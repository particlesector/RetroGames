#!/usr/bin/env python3
"""Renders the DRYLINE pitch mockups under NES limits.

A track is a closed spline. It is rasterised, cut into 16x16 attribute cells that
each get one 4-colour palette, and into 8x8 tiles that are counted for uniqueness
(one track has to fit one 256-tile CHR bank). Wetness is stored per tile, exactly
as the game would: rain wets tiles, cars dry the ones they drive over.
These are mockups, not emulator captures.
"""
import os, sys, math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "..", "shared", "tools"))
from font5x7 import FONT

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "docs", "pitch")
W, H, HUD = 256, 240, 24
rng = np.random.default_rng(7)

_rows = [
 "626262 001FB2 2404C8 5200B2 730076 800024 730B00 522800 244400 005700 005C00 005324 003C76 000000 000000 000000",
 "ABABAB 0D57FF 4B30FF 8A13FF BC08D6 D21269 C72E00 9D5400 607B00 209800 00A300 009942 007DB4 000000 000000 000000",
 "FFFFFF 53AEFF 9085FF D365FF FF57FF FF5DCF FF7757 FA9E00 BDC700 7AE700 43F611 26EF7E 2CD5F6 4E4E4E 000000 000000",
 "FFFFFF B6E1FF CED1FF E9C3FF FFBCFF FFBDF4 FFC6C3 FFD59A E9E681 CEF481 B6FB9A A9FAC3 A9F0F4 B8B8B8 000000 000000"]
NES = np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)] for r in _rows for h in r.split()], dtype=np.int32)

# colour roles -> NES index, for fair weather and for rain
ROLE = ["GRASS", "GDARK", "GLIGHT", "SAND", "ROAD", "WETROAD", "WHITE", "RED", "WATER", "WLIGHT", "GREY", "BLACK"]
DRY = dict(GRASS=0x1A, GDARK=0x0A, GLIGHT=0x2A, SAND=0x38, ROAD=0x00, WETROAD=0x2D, WHITE=0x30, RED=0x16,
           WATER=0x11, WLIGHT=0x21, GREY=0x10, BLACK=0x0F)
# in rain the whole road takes the dark wet colour; entry WETROAD becomes what cars uncover
RAIN = dict(DRY, GRASS=0x0A, GDARK=0x09, GLIGHT=0x1A, SAND=0x28, ROAD=0x0C, WETROAD=0x00, WATER=0x01, WLIGHT=0x11)
G, GD, GL, SA, RO, WR, WH, RE, WA, WL, GY, BK = range(12)
# background palettes as roles; entry 0 is the shared backdrop (grass)
PALS = [[G, RO, WH, RE],      # 0 road with kerbs
        [G, GD, GL, SA],      # 1 nature
        [G, WA, WL, WH],      # 2 water
        [G, RO, WH, WR]]      # 3 road; entry 3 is the dried surface in rain, laid rubber in the dry
SPR = [[0x0F, 0x16, 0x30], [0x0F, 0x2C, 0x30], [0x0F, 0x28, 0x30], [0x0F, 0x24, 0x30]]

# ----------------------------------------------------------------- track
CTRL = [(52, 206), (128, 210), (204, 206), (234, 178), (230, 144), (200, 124), (160, 134), (122, 150),
        (92, 132), (104, 102), (150, 90), (200, 84), (232, 62), (210, 42), (150, 46), (96, 58),
        (54, 44), (24, 70), (24, 120), (32, 150), (28, 182)]
HALF = 16

def spline(pts, n=2400):
    p = np.array(pts, float); k = len(p); out = []
    for i in range(k):
        p0, p1, p2, p3 = p[i - 1], p[i], p[(i + 1) % k], p[(i + 2) % k]
        for t in np.linspace(0, 1, n // k, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.array(out)

PATH = spline(CTRL)
TAN = np.roll(PATH, -1, 0) - np.roll(PATH, 1, 0); TAN /= np.linalg.norm(TAN, axis=1)[:, None]
ARC = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(PATH, axis=0), axis=1))])
ang = np.arctan2(TAN[:, 1], TAN[:, 0])
CURV = np.convolve(np.unwrap(np.concatenate([ang, ang[:1]]))[1:] - np.unwrap(np.concatenate([ang, ang[:1]]))[:-1],
                   np.ones(60) / 60, "same") / (ARC[-1] / len(PATH))

def nearest():
    ys, xs = np.mgrid[0:H, 0:W]
    P = np.stack([xs.ravel(), ys.ravel()], 1).astype(float)
    best = np.full(len(P), 1e9); idx = np.zeros(len(P), int)
    for s in range(0, len(PATH), 200):
        d = np.linalg.norm(P[:, None, :] - PATH[None, s:s + 200, :], axis=2)
        m = d.min(1); a = d.argmin(1) + s
        upd = m < best; best[upd] = m[upd]; idx[upd] = a[upd]
    side = (TAN[idx, 0] * (P[:, 1] - PATH[idx, 1]) - TAN[idx, 1] * (P[:, 0] - PATH[idx, 0]))
    return best.reshape(H, W), idx.reshape(H, W), np.sign(side).reshape(H, W)

def build_scene():
    d, idx, side = nearest()
    ys, xs = np.mgrid[0:H, 0:W]
    img = np.full((H, W), G, int)
    tex = np.full((16, 16), G)                       # repeating textures keep the tile count down
    for (x, y, c) in [(2, 3, GD), (3, 3, GD), (10, 1, GL), (13, 7, GD), (6, 9, GL), (7, 9, GL), (1, 13, GD), (11, 12, GD), (12, 12, GD)]:
        tex[y, x] = c
    img[:] = np.tile(tex, (H // 16, W // 16))
    def blob(cx, cy, rx, ry, col, speck):
        m = ((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2 < 1
        img[m] = col
        img[m & ((xs * 3 + ys * 5) % 11 == 0)] = speck
    blob(246, 214, 12, 18, SA, GL); blob(10, 100, 7, 26, SA, GL); blob(66, 96, 10, 14, SA, GL)     # gravel traps
    blob(150, 182, 34, 12, WA, WL)                                                                # infield lake
    tree = np.full((16, 16), -1)
    for y in range(16):
        for x in range(16):
            r = (x - 7.5) ** 2 + (y - 8) ** 2
            if r < 42: tree[y, x] = GD
            if (x - 6) ** 2 + (y - 6) ** 2 < 7: tree[y, x] = GL
    for (tx, ty) in [(152, 152), (176, 152), (72, 168), (88, 176), (72, 184), (240, 104), (240, 120), (136, 64),
                     (168, 64), (56, 80), (56, 104), (0, 32), (240, 24), (0, 216), (104, 176)]:
        m = tree >= 0; img[ty:ty + 16, tx:tx + 16][m] = tree[m]
    road = d < HALF
    img[road] = RO
    img[(d >= HALF - 2) & (d < HALF - 1)] = WH                                                    # edge lines
    kerb = (d >= HALF) & (d < HALF + 3) & (np.abs(CURV[idx]) > 0.020) & (side == np.sign(CURV[idx]))
    stripe = (ARC[idx] // 4).astype(int) % 2 == 0
    img[kerb & stripe] = RE; img[kerb & ~stripe] = WH
    i0 = int(np.argmin(np.abs(PATH[:, 0] - 150) + np.abs(PATH[:, 1] - 210) * 3))                  # start line
    along = ARC[idx] - ARC[i0]
    line = road & (np.abs(along) < 2.5)
    img[line & (((xs // 2) + (ys // 2)) % 2 == 0)] = WH
    for k in range(4):                                                                            # grid boxes
        g = road & (np.abs(along + 14 + k * 12) < 0.7) & ((side > 0) == (k % 2 == 0)) & (d < HALF - 3) & (d > 2)
        img[g] = WH
    img[:HUD] = WR
    return img, d, idx, i0

def fit_palettes(img):
    """Give every 16x16 cell the palette that loses least; snap stray pixels into it."""
    pal = np.zeros((H // 16, W // 16), int); out = np.zeros_like(img)
    rgb = NES[[DRY[r] for r in ROLE]]
    for cy in range(H // 16):
        for cx in range(W // 16):
            cell = img[cy * 16:cy * 16 + 16, cx * 16:cx * 16 + 16]
            best = None
            for pi in (3, 0, 1, 2):                      # prefer the palette that can show a wet road
                p = PALS[pi]
                miss = sum(int((cell == r).sum()) for r in np.unique(cell) if r not in p)
                if best is None or miss < best[0]: best = (miss, pi)
            p = PALS[best[1]]; pal[cy, cx] = best[1]
            m = np.zeros_like(cell)
            for r in np.unique(cell):
                if r in p: j = p.index(r)
                elif r in (GD, GL, SA, WA, WL): j = 0    # scenery that does not fit becomes grass
                else: j = int(np.argmin([np.abs(rgb[r] - rgb[q]).sum() for q in p]))
                m[cell == r] = j
            out[cy * 16:cy * 16 + 16, cx * 16:cx * 16 + 16] = m
    return out, pal

def dry_tile(level, has_dry_colour):
    """8x8 road tile that cars have dried: level 1 half dry, 2 dry. Kerb cells have no dry colour and dither with white."""
    t = np.full((8, 8), 1); chk = (np.add.outer(np.arange(8), np.arange(8)) % 2) == 0
    if has_dry_colour:
        if level == 2: t[:] = 3
        else: t[chk] = 3
    else:
        t[chk & (np.add.outer(np.arange(8), np.zeros(8, int)) % (2 if level == 2 else 4) == 0)] = 2
    return t

# ------------------------------------------------------------------ cars
def car(theta):
    """16x16 open-wheel racer facing angle theta: 0 none, 1 dark, 2 body, 3 white."""
    out = np.zeros((16, 16), int); c, s = math.cos(theta), math.sin(theta)
    for py in range(16):
        for px in range(16):
            votes = [0, 0, 0, 0]
            for sy in (0.17, 0.5, 0.83):
                for sx in (0.17, 0.5, 0.83):
                    dx, dy = px + sx - 8, py + sy - 8
                    x, y = dx * c + dy * s, -dx * s + dy * c; ay = abs(y)
                    k = 0
                    if (2.4 <= x <= 5.4 and 2.5 <= ay <= 4.3) or (-5.6 <= x <= -2.2 and 2.3 <= ay <= 4.6): k = 1
                    if (-5.2 <= x <= 3 and ay <= 1.7) or (3 < x <= 6.6 and ay <= 1.7 - (x - 3) * 0.33) \
                            or (-3.6 <= x <= 1.4 and ay <= 2.7): k = 2
                    if (-6.8 <= x <= -5.4 and ay <= 3.8) or (5.6 <= x <= 6.8 and ay <= 3.3): k = 3
                    if -1.3 <= x <= 1.3 and ay <= 1.0: k = 1
                    if -0.4 <= x <= 0.9 and ay <= 0.62: k = 3
                    votes[k] += 1
            if votes[0] < 5: out[py, px] = 1 + int(np.argmax(votes[1:]))
    return out
CARS = [car(i * 2 * math.pi / 32) for i in range(32)]

def paint(rgb, x, y, art, pal):
    x, y = int(round(x)) - 8, int(round(y)) - 8
    for j in range(16):
        for i in range(16):
            v = art[j, i]
            if v and 0 <= x + i < W and 0 <= y + j < H: rgb[y + j, x + i] = NES[SPR[pal][v - 1]]

def text(rgb, s, x, y, col=(255, 255, 255), scale=1):
    for n, ch in enumerate(s):
        if ch == " ": continue
        for r in range(7):
            for c in range(5):
                if FONT[ch][r][c] == "1":
                    rgb[y + r * scale:y + (r + 1) * scale, x + (n * 8 + c) * scale:x + (n * 8 + c + 1) * scale] = col

# ---------------------------------------------------------------- frames
img, dist, idx, i0 = build_scene()
base, cellpal = fit_palettes(img)
pure = np.array([[bool((img[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8] == RO).all()) for tx in range(W // 8)]
                 for ty in range(H // 8)])

def tile_stats():
    tiles = set()
    for ty in range(HUD // 8, H // 8):
        for tx in range(W // 8): tiles.add(base[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8].tobytes())
    return len(tiles)

def frame(wet, cars, tick, raining, hud):
    roles = RAIN if raining else DRY
    idxmap = base.copy()
    for ty in range(HUD // 8, H // 8):
        for tx in range(W // 8):
            if raining and pure[ty, tx] and wet[ty, tx] < 2:
                p = cellpal[ty // 2, tx // 2]
                if p in (0, 3): idxmap[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8] = dry_tile(2 - int(wet[ty, tx]), p == 3)
    lut = np.array([[NES[roles[ROLE[r]]] for r in p] for p in PALS])
    rgb = lut[np.repeat(np.repeat(cellpal, 16, 0), 16, 1), idxmap].astype(np.uint8)
    for (pos, off, pal) in cars:
        i = int(pos) % len(PATH); n = np.array([-TAN[i, 1], TAN[i, 0]])
        x, y = PATH[i] + n * off
        a = int(round(math.atan2(TAN[i, 1], TAN[i, 0]) / (2 * math.pi / 32))) % 32
        paint(rgb, x, y, CARS[a], pal)
    if raining:
        r2 = np.random.default_rng(tick // 2)
        for _ in range(26):
            x, y = int(r2.integers(4, W - 4)), int(r2.integers(HUD + 2, H - 6))
            for k in range(4): rgb[y + k, x - k] = (206, 209, 255)
    text(rgb, hud, 8, 12)
    return Image.fromarray(rgb)

def up(im, k): return im.resize((im.width * k, im.height * k), Image.NEAREST)

def main():
    os.makedirs(OUT, exist_ok=True)
    L = len(PATH); grid = [(i0 - 60 - k * 46, 6 if k % 2 == 0 else -6, k) for k in range(4)]
    dry = np.zeros((H // 8, W // 8), int)
    up(frame(dry, grid, 0, False, "P1  LAP 1-5  TYRE SLICK  DRY"), 3).save(f"{OUT}/track_dry.png")
    # simulate: rain wets tiles at random, cars dry what they drive over
    wet = np.zeros((H // 8, W // 8), int); frames = []
    cars = [[i0 + 300, 1.0, 0, 9.5], [i0 + 180, -2.0, 1, 9.2], [i0 + 60, 2.0, 2, 9.0], [i0 - 40, -1.0, 3, 8.8]]
    r3 = np.random.default_rng(3)
    for t in range(420):
        raining = t >= 50
        if t == 50: wet[:] = 2
        if raining:
            for _ in range(4):
                ty, tx = int(r3.integers(HUD // 8, H // 8)), int(r3.integers(0, W // 8))
                wet[ty, tx] = min(2, wet[ty, tx] + 1)
        for c in cars:
            c[0] += c[3] * (0.8 if raining else 1.0)
            i = int(c[0]) % L; n = np.array([-TAN[i, 1], TAN[i, 0]]); x, y = PATH[i] + n * c[1]
            ty, tx = int(y) // 8, int(x) // 8
            if raining and 0 <= ty < H // 8 and 0 <= tx < W // 8: wet[ty, tx] = max(0, wet[ty, tx] - 1)
        lap = 1 + int((cars[0][0] - i0) // L)
        hud = f"P1  LAP {lap + 1}-5  TYRE SLICK  " + ("RAIN" if raining else "DRY")
        if t % 2 == 0: frames.append(up(frame(wet, [(c[0], c[1], c[2]) for c in cars], t, raining, hud), 2))
        if t == 400: up(frame(wet, [(c[0], c[1], c[2]) for c in cars], t, True, hud), 3).save(f"{OUT}/track_wet.png")
    frames[0].save(f"{OUT}/weather_demo.gif", save_all=True, append_images=frames[1:], duration=50, loop=0)
    # car rotation sheet
    sheet = np.zeros((4 * 22 + 18, 16 * 22 + 4, 3), np.uint8); sheet[:] = NES[0x00]
    for i in range(32):
        tmp = np.zeros((H, W, 3), np.uint8); tmp[:] = NES[0x00]
        paint(tmp, 8, 8, CARS[i], (i // 16) % 4)
        sheet[2 + (i // 16) * 22:18 + (i // 16) * 22, 4 + (i % 16) * 22:20 + (i % 16) * 22] = tmp[:16, :16]
    for p in range(4):
        tmp = np.zeros((H, W, 3), np.uint8); tmp[:] = NES[0x00]
        paint(tmp, 8, 8, CARS[29], p)
        sheet[48:64, 4 + p * 22:20 + p * 22] = tmp[:16, :16]
    text(sheet, "32 HEADINGS FROM 9 DRAWN FRAMES", 4, 70); text(sheet, "4 LIVERIES", 100, 52)
    up(Image.fromarray(sheet), 3).save(f"{OUT}/cars.png")
    # logo
    lg = np.zeros((64, 256, 3), np.uint8); lg[:] = NES[0x0F]
    for r in range(64):
        lg[r, :] = NES[0x0C] if 40 <= r < 44 else lg[r, :]
    tmp = np.zeros((40, 300, 3), np.uint8)
    text(tmp, "DRYLINE", 0, 0, tuple(NES[0x30]), 4)
    for r in range(28):
        sh = (28 - r) // 4
        row = tmp[r, :240]
        if r >= 12: row = np.where(row.any(1)[:, None], NES[0x28].astype(np.uint8), row)
        dst = lg[8 + r, 8 + sh:8 + sh + 240]
        lg[8 + r, 8 + sh:8 + sh + 240] = np.where(row.any(1)[:, None], row, dst)
    text(lg, "GRAND PRIX", 88, 50, tuple(NES[0x16]))
    for x in range(0, 256, 8): lg[40:44, x:x + 4] = NES[0x30]
    up(Image.fromarray(lg), 3).save(f"{OUT}/logo.png")
    # palettes
    ps = np.zeros((70, 256, 3), np.uint8); ps[:] = (16, 16, 24)
    names = ["KERBS", "NATURE", "WATER", "ROAD"]
    for p in range(4):
        for k, (roles, y) in enumerate(((DRY, 4), (RAIN, 38))):
            for i, r in enumerate(PALS[p]):
                ps[y:y + 12, 4 + p * 63 + i * 14:16 + p * 63 + i * 14] = NES[roles[ROLE[r]]]
        text(ps, names[p][:7], 4 + p * 63, 18, (150, 160, 190))
    text(ps, "RAIN", 4, 54, (150, 160, 190))
    up(Image.fromarray(ps), 3).save(f"{OUT}/palettes.png")
    n = tile_stats()
    print(f"unique 8x8 background tiles for this track: {n} (bank holds 256)")
    print(f"pure road tiles that can change wetness: {int(pure[HUD // 8:].sum())}")
    print(f"track length {ARC[-1]:.0f} px")

main()
