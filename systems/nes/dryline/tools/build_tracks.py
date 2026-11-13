#!/usr/bin/env python3
"""Compiles assets/tracks/*.toml into CHR pages and data for the ROM.

A circuit is a closed spline plus scenery. It is rasterised, fitted to NES
attribute cells, and cut into 8x8 tiles. Tiles $00-$7F are the "common" bank
(fixed tiles, the font, and the circuit's most repeated tiles); tiles $80-$FF
are unique edge tiles, held in up to four 2 KB banks that the game swaps
between horizontal bands of the screen with the MMC3 scanline interrupt.

Outputs in build/: tracks.chr, tracks.inc, charmap.inc, ref_<n>.png (what the
screen must look like, for the tests), tracks.json (facts for the tests).
"""
import sys, os, json, glob, math, tomllib
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "shared", "tools"))
from nespal import *
from font5x7 import FONT

W, H, TOP = 256, 240, 32            # the top 32 pixels are the HUD
ROAD, ROADK = 0x01, 0x04            # pure road tile in a road cell / in a kerb cell; +1, +2 = drying, dry
FONT_BASE, COMMON_BASE, UNIQUE_BASE = 0x10, 0x50, 0x80
MAX_BANDS, PAGES_PER_TRACK = 4, 10  # 2 common pages + 4 bands x 2 pages
CHARS = sorted(FONT)

# ---------------------------------------------------------------- geometry
def spline(pts, n=3000):
    p = np.array(pts, float); k = len(p); out = []
    for i in range(k):
        p0, p1, p2, p3 = p[i - 1], p[i], p[(i + 1) % k], p[(i + 2) % k]
        for t in np.linspace(0, 1, n // k, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.array(out)

class Geo:
    def __init__(self, t):
        self.path = P = spline(t["points"])
        tan = np.roll(P, -1, 0) - np.roll(P, 1, 0); self.tan = tan / np.linalg.norm(tan, axis=1)[:, None]
        seg = np.linalg.norm(np.roll(P, -1, 0) - P, axis=1)
        self.arc = np.concatenate([[0], np.cumsum(seg)[:-1]]); self.length = float(seg.sum())
        ang = np.unwrap(np.arctan2(self.tan[:, 1], self.tan[:, 0]))
        d = np.roll(ang, -1) - ang; d[-1] = d[-2]
        k = np.convolve(np.concatenate([d[-40:], d, d[:40]]), np.ones(81) / 81, "same")[40:-40]
        self.curv = k / seg.mean()
        ys, xs = np.mgrid[0:H, 0:W]; Q = np.stack([xs.ravel(), ys.ravel()], 1).astype(float)
        best = np.full(len(Q), 1e9); idx = np.zeros(len(Q), int)
        for s in range(0, len(P), 150):
            dd = np.linalg.norm(Q[:, None, :] - P[None, s:s + 150, :], axis=2)
            m = dd.min(1); a = dd.argmin(1) + s; u = m < best; best[u] = m[u]; idx[u] = a[u]
        side = self.tan[idx, 0] * (Q[:, 1] - P[idx, 1]) - self.tan[idx, 1] * (Q[:, 0] - P[idx, 0])
        self.dist, self.idx, self.side = best.reshape(H, W), idx.reshape(H, W), np.sign(side).reshape(H, W)
        sx, sy = t["start"]; self.i0 = int(np.argmin((P[:, 0] - sx) ** 2 + (P[:, 1] - sy) ** 2))

# ------------------------------------------------------------------ drawing
def draw(t, g):
    """-> (role image, solid mask). Everything is built from repeating patterns to keep tiles few."""
    half = t["half_width"]; ys, xs = np.mgrid[0:H, 0:W]
    tex = np.full((16, 16), G)
    for (x, y, c) in [(2, 3, GD), (3, 3, GD), (10, 1, GL), (13, 7, GD), (6, 9, GL), (7, 9, GL), (1, 13, GD), (11, 12, GD), (12, 12, GD)]:
        tex[y, x] = c
    img = np.tile(tex, (H // 16, W // 16)); solid = np.zeros((H, W), bool)
    tree = np.full((16, 16), -1)
    for y in range(16):
        for x in range(16):
            if (x - 7.5) ** 2 + (y - 8) ** 2 < 42: tree[y, x] = GD
            if (x - 6) ** 2 + (y - 6) ** 2 < 7: tree[y, x] = GL
    for s in t.get("scenery", []):
        if s["kind"] in ("lake", "gravel"):
            (cx, cy), (rx, ry) = s["at"], s["size"]
            m = ((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2 < 1
            a, b = (WA, WL) if s["kind"] == "lake" else (SA, GL)
            img[m] = a; img[m & ((xs * 3 + ys * 5) % 11 == 0)] = b
            if s["kind"] == "lake": solid |= m
        elif s["kind"] == "trees":
            for (tx, ty) in s["at"]:
                assert tx % 16 == 0 and ty % 16 == 0, "trees sit on the 16-pixel grid"
                m = tree >= 0; img[ty:ty + 16, tx:tx + 16][m] = tree[m]
                solid[ty + 3:ty + 13, tx + 3:tx + 13] = True
    road = g.dist < half
    img[road] = RO; solid[road] = False
    img[(g.dist >= half - 2) & (g.dist < half - 1)] = WH
    kerb = (g.dist >= half) & (g.dist < half + 3) & (np.abs(g.curv[g.idx]) > 0.018) & (g.side == np.sign(g.curv[g.idx]))
    stripe = (g.arc[g.idx] // 4).astype(int) % 2 == 0
    img[kerb & stripe] = RE; img[kerb & ~stripe] = WH; solid[kerb] = False
    along = g.arc[g.idx] - g.arc[g.i0]
    along = (along + g.length / 2) % g.length - g.length / 2
    line = road & (np.abs(along) < 2.5)
    img[line & (((xs // 2) + (ys // 2)) % 2 == 0)] = WH
    for k in range(4):                                   # grid boxes behind the line
        box = road & (np.abs(along + 4 + k * 14) < 0.7) & ((g.side > 0) == (k % 2 == 0)) & (g.dist < half - 4) & (g.dist > 3)
        img[box] = WH
    img[:TOP] = RO; solid[:TOP] = True
    return img, solid

def fit(img):
    """Give each 16x16 cell the palette that fits best; scenery that cannot fit becomes grass."""
    idx = np.zeros_like(img); cellpal = np.zeros((H // 16, W // 16), int)
    for cy in range(H // 16):
        for cx in range(W // 16):
            cell = img[cy * 16:cy * 16 + 16, cx * 16:cx * 16 + 16]; roles = np.unique(cell)
            best = None
            for pi in (3, 0, 1, 2):
                miss = sum(int((cell == r).sum()) for r in roles if r not in PALS[pi])
                if best is None or miss < best[0]: best = (miss, pi)
            p = PALS[best[1]]; cellpal[cy, cx] = best[1]; m = np.zeros_like(cell)
            for r in roles:
                m[cell == r] = p.index(r) if r in p else (p.index(RO) if r in (RE, WH, DR) and RO in p else 0)
            idx[cy * 16:cy * 16 + 16, cx * 16:cx * 16 + 16] = m
    return idx, cellpal

# -------------------------------------------------------------------- tiles
def enc(t):
    t = np.asarray(t)
    p0 = bytes(int(sum(((t[y, x] & 1) << (7 - x)) for x in range(8))) for y in range(8))
    p1 = bytes(int(sum(((t[y, x] >> 1) << (7 - x)) for x in range(8))) for y in range(8))
    return p0 + p1

def fixed_tiles():
    t = {0x00: np.zeros((8, 8), int)}
    chk = (np.add.outer(np.arange(8), np.arange(8)) % 2) == 0
    for base, dry in ((ROAD, 3), (ROADK, 2)):
        t[base] = np.full((8, 8), 1)
        half = np.full((8, 8), 1); full = np.full((8, 8), 1)
        if dry == 3: half[chk] = 3; full[:] = 3
        else:                                            # kerb cells have no dried colour: dither with white
            half[chk & (np.arange(8)[:, None] % 4 == 0)] = 2; full[chk & (np.arange(8)[:, None] % 2 == 0)] = 2
        t[base + 1], t[base + 2] = half, full
    for i, ch in enumerate(CHARS):
        g = np.full((8, 8), 1)
        for r in range(7):
            for c in range(5):
                if FONT[ch][r][c] == "1": g[r, c + 1] = 2
        t[FONT_BASE + i] = g
    return t

def compile_track(n, path):
    t = tomllib.load(open(path, "rb")); g = Geo(t)
    img, solid = draw(t, g); idx, cellpal = fit(img); cellpal[:TOP // 16] = 3
    fixed = fixed_tiles(); key2id = {}
    for i, px in fixed.items():
        if i not in (ROADK, ROADK + 1, ROADK + 2): key2id.setdefault(enc(px), i)
    nt = np.zeros((30, 32), int); wet = np.zeros((30, 32), int); grid = {}
    for ty in range(30):
        for tx in range(32):
            px = idx[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8]
            pure = ty >= TOP // 8 and bool((img[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8] == RO).all())
            if pure:
                kerbcell = cellpal[ty // 2, tx // 2] == 0
                assert cellpal[ty // 2, tx // 2] in (0, 3), "pure road tile outside a road cell"
                nt[ty, tx] = ROADK if kerbcell else ROAD; wet[ty, tx] = 0xC0 if kerbcell else 0x80
            else: grid[(ty, tx)] = enc(px)
    # most repeated tiles go to the common bank
    freq = {}
    for k in grid.values():
        if k not in key2id: freq[k] = freq.get(k, 0) + 1
    common = sorted((k for k in freq if freq[k] > 1), key=lambda k: -freq[k])[:UNIQUE_BASE - COMMON_BASE]
    pages = [bytearray(1024) for _ in range(PAGES_PER_TRACK)]
    def put(page0, tile, data):                          # tile 0..127 within a 2 KB bank
        pages[page0 + tile // 64][(tile % 64) * 16:(tile % 64) * 16 + 16] = data
    for i, px in fixed.items(): put(0, i, enc(px))
    for j, k in enumerate(common): key2id[k] = COMMON_BASE + j; put(0, COMMON_BASE + j, k)
    # unique tiles: fill bands top to bottom, 128 per band
    bands, cur, start_row = [], {}, TOP // 8
    def row_new(ty, have): return {grid[(ty, tx)] for tx in range(32) if (ty, tx) in grid and grid[(ty, tx)] not in key2id} - set(have)
    for ty in range(TOP // 8, 30):
        new = row_new(ty, cur)
        if len(cur) + len(new) > 128:
            bands.append((start_row, cur)); cur, start_row = {}, ty; new = row_new(ty, cur)
        for k in sorted(new): cur[k] = UNIQUE_BASE + len(cur)
        for tx in range(32):
            if (ty, tx) in grid:
                k = grid[(ty, tx)]; nt[ty, tx] = key2id[k] if k in key2id else cur[k]
    bands.append((start_row, cur))
    assert len(bands) <= MAX_BANDS, f"{path}: needs {len(bands)} tile bands, limit {MAX_BANDS}"
    for b, (_, tiles) in enumerate(bands):
        for k, i in tiles.items(): put(2 + b * 2, i - UNIQUE_BASE, k)
    for ty in range(TOP // 8):
        nt[ty, :] = ROAD
    attr = []
    for ay in range(8):
        for ax in range(8):
            v = 0
            for q, (dy, dx) in enumerate([(0, 0), (0, 1), (1, 0), (1, 1)]):
                cy, cx = ay * 2 + dy, ax * 2 + dx
                if cy < 15: v |= int(cellpal[cy, cx]) << (q * 2)
            attr.append(v)
    # surface map at 4-pixel resolution: 0 road, 1 grass, 2 gravel, 3 solid
    surf = np.zeros((60, 64), int)
    for sy in range(60):
        for sx in range(64):
            blk = img[sy * 4:sy * 4 + 4, sx * 4:sx * 4 + 4]
            if solid[sy * 4:sy * 4 + 4, sx * 4:sx * 4 + 4].sum() >= 8: surf[sy, sx] = 3
            elif np.isin(blk, (RO, WH, RE, DR)).sum() >= 8: surf[sy, sx] = 0
            elif (blk == SA).sum() >= 8: surf[sy, sx] = 2
            else: surf[sy, sx] = 1
    packed = [int(surf[sy, sx] | surf[sy, sx + 1] << 2 | surf[sy, sx + 2] << 4 | surf[sy, sx + 3] << 6)
              for sy in range(60) for sx in range(0, 64, 4)]
    # reference picture
    fair = THEMES[t["theme"]][0]
    lut = np.array([[NES[fair[ROLES[r]]] for r in p] for p in PALS])
    ref = lut[np.repeat(np.repeat(cellpal, 16, 0), 16, 1), idx].astype(np.uint8)
    used = sum(len(b[1]) for b in bands)
    info = dict(name=t["name"], bands=[b[0] * 8 for b in bands], unique=used, common=len(common), length=round(g.length),
                half_width=t["half_width"], start=[float(g.path[g.i0][0]), float(g.path[g.i0][1])],
                heading=float(math.atan2(g.tan[g.i0][1], g.tan[g.i0][0])))
    slots = []
    for k in range(4):                                   # grid: staggered pairs behind the line
        i = int(np.argmin(np.abs(((g.arc - g.arc[g.i0] + g.length / 2) % g.length - g.length / 2) + 12 + k * 14)))
        nrm = np.array([-g.tan[i, 1], g.tan[i, 0]]) * (8 if k % 2 == 0 else -8)
        slots.append([int(round(g.path[i, 0] + nrm[0])), int(round(g.path[i, 1] + nrm[1]))])
    grid_angle = int(round(math.atan2(g.tan[g.i0][1], g.tan[g.i0][0]) / (2 * math.pi) * 256)) & 255
    info["grid"] = slots; info["grid_angle"] = grid_angle
    return dict(grid=slots, grid_angle=grid_angle, t=t, g=g, nt=nt, wet=wet, attr=attr, surf=packed, pages=pages, bands=bands, ref=ref, info=info,
                idx=idx, cellpal=cellpal)

def bl(xs): return ", ".join("$%02X" % int(x) for x in xs)

def main():
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    tracks = [compile_track(n, p) for n, p in enumerate(sorted(glob.glob(os.path.join(src, "*.toml"))))]
    chr_ = bytearray(); L = ["; generated by tools/build_tracks.py", f"NUM_TRACKS = {len(tracks)}",
                              f"T_ROAD = ${ROAD:02X}", f"T_ROADK = ${ROADK:02X}", f"TRACK_PAGES = {PAGES_PER_TRACK}"]
    for n, tr in enumerate(tracks):
        for p in tr["pages"]: chr_ += p
        Image.fromarray(tr["ref"]).save(f"{out}/ref_{n}.png")
        L.append(f'.segment "TRK{n // 2}"')
        L.append(f"track_{n}:")
        splits = [b[0] * 8 for b in tr["bands"][1:]] + [0] * (MAX_BANDS - len(tr["bands"]))
        L.append(f"  .byte {len(tr['bands'])}, {bl(splits[:MAX_BANDS - 1])}    ; bands, split scanlines")
        L.append(f"  .byte {tr['t']['laps']}")
        L.append(f"  .byte {bl(v for xy in tr['grid'] for v in xy)}, {tr['grid_angle']}    ; grid slots x,y and heading")
        L.append(f"  .byte {bl(palette_bytes(tr['t']['theme'], False))}")
        L.append(f"  .byte {bl(palette_bytes(tr['t']['theme'], True))}")
        name = tr["t"]["name"].upper(); assert len(name) <= 16
        L.append(f'  .byte "{name:<16}"')
        for label, rows in (("nametable", tr["nt"]), ("wet-capable tiles", tr["wet"])):
            L.append(f"  ; {label}")
            for r in rows: L.append("  .byte " + bl(r))
        L.append("  ; attributes"); L.append("  .byte " + bl(tr["attr"]))
        L.append("  ; surface map, 2 bits per 4x4 pixels")
        for i in range(0, 960, 32): L.append("  .byte " + bl(tr["surf"][i:i + 32]))
    L.append('.segment "RODATA"')
    L.append("track_lo: .byte " + ", ".join(f"<track_{n}" for n in range(len(tracks))))
    L.append("track_hi: .byte " + ", ".join(f">track_{n}" for n in range(len(tracks))))
    L.append("track_bank: .byte " + ", ".join(f"BANK_TRK0 + {n // 2}" for n in range(len(tracks))))
    open(f"{out}/tracks.chr", "wb").write(chr_)
    open(f"{out}/tracks.inc", "w").write("\n".join(L) + "\n")
    with open(f"{out}/charmap.inc", "w") as f:
        f.write("; generated by tools/build_tracks.py\n.charmap $20, $%02X\n" % ROAD)
        for i, ch in enumerate(CHARS): f.write(".charmap $%02X, $%02X\n" % (ord(ch), FONT_BASE + i))
        f.write("T_0 = $%02X\nT_A = $%02X\n" % (FONT_BASE + CHARS.index("0"), FONT_BASE + CHARS.index("A")))
    json.dump([tr["info"] for tr in tracks], open(f"{out}/tracks.json", "w"), indent=1)
    for n, tr in enumerate(tracks):
        i = tr["info"]; print(f"track {n} {i['name']}: {i['length']} px, {i['common']} common + {i['unique']} unique tiles in {len(i['bands'])} bands at {i['bands']}")

if __name__ == "__main__": main()
