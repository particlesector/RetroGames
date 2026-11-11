#!/usr/bin/env python3
"""Builds build/tidebell.chr and build/gfx.inc.

CHR layout (1 KB pages):  0-1 BG tiles $00-$7F, dry   |  2-3 BG tiles $80-$FF
                          4-7 sprites                 |  8-9 BG tiles $00-$7F, submerged
Tiles with "air" pixels get a dry and a submerged version at the same index;
the MMC3 scanline IRQ swaps page 0-1 for 8-9 at the waterline.
"""
import sys, os

OUT = sys.argv[1] if len(sys.argv) > 1 else "build"
A = 4  # air pixel

def h(x, y, s=0): return ((x * 73856093) ^ (y * 19349663) ^ (s * 83492791)) >> 3 & 0xFF

# ------------------------------------------------------------------ font
FONT = {k: v.split("/") for k, v in {
 "A": "01110/10001/10001/11111/10001/10001/10001", "B": "11110/10001/10001/11110/10001/10001/11110",
 "C": "01110/10001/10000/10000/10000/10001/01110", "D": "11110/10001/10001/10001/10001/10001/11110",
 "E": "11111/10000/10000/11110/10000/10000/11111", "F": "11111/10000/10000/11110/10000/10000/10000",
 "G": "01110/10001/10000/10111/10001/10001/01111", "H": "10001/10001/10001/11111/10001/10001/10001",
 "I": "01110/00100/00100/00100/00100/00100/01110", "J": "00111/00010/00010/00010/00010/10010/01100",
 "K": "10001/10010/10100/11000/10100/10010/10001", "L": "10000/10000/10000/10000/10000/10000/11111",
 "M": "10001/11011/10101/10101/10001/10001/10001", "N": "10001/11001/10101/10011/10001/10001/10001",
 "O": "01110/10001/10001/10001/10001/10001/01110", "P": "11110/10001/10001/11110/10000/10000/10000",
 "Q": "01110/10001/10001/10001/10101/10010/01101", "R": "11110/10001/10001/11110/10100/10010/10001",
 "S": "01111/10000/10000/01110/00001/00001/11110", "T": "11111/00100/00100/00100/00100/00100/00100",
 "U": "10001/10001/10001/10001/10001/10001/01110", "V": "10001/10001/10001/10001/10001/01010/00100",
 "W": "10001/10001/10001/10101/10101/11011/10001", "X": "10001/10001/01010/00100/01010/10001/10001",
 "Y": "10001/10001/01010/00100/00100/00100/00100", "Z": "11111/00001/00010/00100/01000/10000/11111",
 "0": "01110/10001/10011/10101/11001/10001/01110", "1": "00100/01100/00100/00100/00100/00100/01110",
 "2": "01110/10001/00001/00010/00100/01000/11111", "3": "11110/00001/00001/01110/00001/00001/11110",
 "4": "00010/00110/01010/10010/11111/00010/00010", "5": "11111/10000/11110/00001/00001/10001/01110",
 "6": "00110/01000/10000/11110/10001/10001/01110", "7": "11111/00001/00010/00100/01000/01000/01000",
 "8": "01110/10001/10001/01110/10001/10001/01110", "9": "01110/10001/10001/01111/00001/00010/01100",
 "-": "00000/00000/00000/11111/00000/00000/00000", ".": "00000/00000/00000/00000/00000/01100/01100",
 "!": "00100/00100/00100/00100/00100/00000/00100", "'": "00100/00100/01000/00000/00000/00000/00000",
 ",": "00000/00000/00000/00000/01100/00100/01000", "+": "00000/00100/00100/11111/00100/00100/00000",
 ":": "00000/01100/01100/00000/01100/01100/00000", "?": "01110/10001/00001/00010/00100/00000/00100",
}.items()}

def glyph_tile(ch):
    t = [[0] * 8 for _ in range(8)]
    for r in range(7):
        for c in range(5):
            if FONT[ch][r][c] == "1": t[r][c + 1] = 3
    return t

# --------------------------------------------------------------- metatiles
def blank(v=A): return [[v] * 16 for _ in range(16)]
def t_star(n):
    t = blank()
    for (x, y, c) in [[(5, 3, 3), (12, 10, 2)], [(10, 5, 3), (3, 12, 2), (13, 13, 3)]][n]: t[y][x] = c
    return t
def t_rock(grass=False):
    t = blank(1)
    for y in range(16):
        for x in range(16):
            c, ry = y // 8, y % 8
            jx = (x + (4 if c else 0)) % 8
            if ry == 7 or jx == 7: t[y][x] = 0
            elif ry == 0 or jx == 0: t[y][x] = 2
    if grass:
        for x in range(16):
            for y in range(3): t[y][x] = 3
            if h(x, 3) % 3: t[3][x] = 3
            if h(x, 9) % 4 == 0: t[4][x] = 3
    return t
def t_sand(top=False):
    t = blank(3)
    for y in range(16):
        for x in range(16):
            if h(x, y, 5) % 11 == 0: t[y][x] = 2
    if top:
        for x in range(16):
            t[0][x] = 2 if (x // 2) % 4 else 3
            t[1][x] = 3
    return t
def t_dock(post=False):
    t = blank()
    for x in range(16):
        t[0][x] = 3; t[1][x] = 3; t[2][x] = 2; t[3][x] = 2; t[4][x] = 0
        if x % 8 == 7: t[0][x] = t[1][x] = t[2][x] = t[3][x] = 0
    if post:
        p = t_post()
        for y in range(5, 16): t[y] = p[y]
    return t
def t_post():
    t = blank()
    for y in range(16):
        for x in range(6, 10): t[y][x] = 3 if x == 6 else 2
        if y % 8 == 5:
            for x in range(6, 10): t[y][x] = 0
    return t
def art(rows, key):
    assert all(len(r) == len(rows[0]) for r in rows), [len(r) for r in rows]
    return [[key[c] for c in r] for r in rows]
URCHIN = art([
 "................",
 "................",
 ".......b........",
 "...b...b...b....",
 "....b..b..b.....",
 ".b...bbbbb...b..",
 "..b.bbsbbbb.b...",
 "...bbsbbbbbb....",
 "bbbbbbbbbbbbbbb.",
 "...bbbbbbbbb....",
 "..b.bbbbbbb.b...",
 ".b...bbbbb...b..",
 "....b..b..b.....",
 "...b...b...b....",
 ".......b........",
 "................"], {".": A, "b": 2, "s": 3})
def t_coral(wet):
    if not wet:
        t = blank(0)
        for i in range(16):
            if i % 4 in (0, 1):
                t[0][i] = t[15][i] = t[i][0] = t[i][15] = 1
        return t
    t = blank(1)
    for y in range(16):
        for x in range(16):
            v = h(x // 2, y // 2, 11)
            if v % 7 == 0: t[y][x] = 2
            elif v % 9 == 0: t[y][x] = 0
    for i in range(16):
        t[0][i] = t[i][0] = 2; t[15][i] = t[i][15] = 0
    return t
def t_crate():
    t = blank(2)
    for i in range(16):
        t[0][i] = t[i][0] = 3; t[15][i] = t[i][15] = 0
    for i in range(2, 14):
        t[i][i] = 0; t[i][15 - i] = 0; t[2][i] = 3; t[13][i] = 0
        t[i][2] = 3; t[i][13] = 0
    return t
def t_door():
    t = blank(2)
    for y in range(16):
        for x in range(16):
            if y % 4 == 3 and (x + (y // 4) * 4) % 8 == 0: t[y][x] = 0
        t[y][0] = 0; t[y][15] = 0
    for y in range(3, 16):
        for x in range(4, 12):
            if y == 3 and x in (4, 11): continue
            t[y][x] = 1 if x in (4, 11) or y == 3 else 0
    t[10][9] = 3; t[4][4] = t[4][11] = 2
    for y in range(5, 8):
        for x in range(6, 10): t[y][x] = 3
    return t
def t_lamp(lit):
    t = blank(3 if lit else 0)
    for x in range(16):
        t[0][x] = t[1][x] = t[2][x] = 1; t[3][x] = 0
        t[14][x] = 2; t[15][x] = 0
    for y in range(4, 14):
        for x in (0, 1, 7, 8, 14, 15): t[y][x] = 2
        if not lit: t[y][3 + (13 - y) // 3] = 2
    for y in range(16): t[y][0] = 0; t[y][15] = 0
    return t
def t_band(col, left, feature=None, lit=False):
    t = blank(col)
    for y in range(16):
        for x in range(16):
            if y % 4 == 3 and (x + (y // 4) * 4) % 8 == 0: t[y][x] = 0 if col == 2 else 2
    for y in range(16):
        if left: t[y][0] = 0
        else: t[y][15] = 0
    if feature == "window":
        for y in range(4, 12):
            for x in range(5, 11):
                t[y][x] = 0 if (y in (4, 11) or x in (5, 10)) else (3 if lit else 0)
    if feature == "door":
        for y in range(3, 16):
            for x in range(3, 13):
                if (y == 3 and x in (3, 4, 11, 12)) or (y == 4 and x in (3, 12)): continue
                t[y][x] = 0
        for y in range(6, 9):
            for x in range(6, 10): t[y][x] = 3
        t[11][10] = 3
    return t
def t_biglamp(left, lit):
    t = blank(3 if lit else 0)
    for y in range(16):
        for x in range(16):
            if y in (0, 15) or x % 8 == (0 if left else 7): t[y][x] = 2
        t[y][0 if left else 15] = 2
    return t
def t_roof(left):
    t = blank()
    for y in range(6, 16):
        for x in range(16):
            xx = x if left else 15 - x
            if xx >= 15 - (y - 6) * 2: t[y][x] = 2 if y == 15 else 1
    if left:
        for y in range(1, 6): t[y][15] = 2
    else: t[1][0] = t[2][0] = 1
    return t
def t_beam(n):
    t = blank()
    half = 2 + n
    for y in range(8 - half, 8 + half):
        for x in range(16):
            if (x + y) % 2 == 0: t[y][x] = 3
    return t
def moon_tiles():
    img = [[A] * 32 for _ in range(32)]
    r, mx, my = 13, 15, 16
    for y in range(32):
        for x in range(32):
            d = (x - mx) ** 2 + (y - my) ** 2
            if d <= r * r and (x - mx - 6) ** 2 + (y - my + 4) ** 2 > (r - 1) ** 2:
                img[y][x] = 3 if d < (r - 2) ** 2 else 2
    return [[row[cx * 16:cx * 16 + 16] for row in img[cy * 16:cy * 16 + 16]] for cy in (0, 1) for cx in (0, 1)]

def t_castle(wet):
    if wet:
        t = blank()
        for (x, y) in [(3, 2), (11, 4), (6, 8), (13, 10), (2, 12), (9, 14)]: t[y][x] = 3
        return t
    t = blank(3)
    for y in range(16):
        for x in range(16):
            if h(x, y, 21) % 9 == 0: t[y][x] = 2
            if y % 8 == 7 or (x + (y // 8) * 4) % 8 == 7: t[y][x] = 2
    for x in range(16):
        if x % 8 in (3, 4): t[0][x] = t[1][x] = 0
        t[15][x] = 0
    return t
AIR, SOLID, PLAT, HAZ, CORAL, DOOR, CASTLE = range(7)
MT = [  # name, palette, type, dry pixels, (optional) wet pixels
 ("AIR", 0, AIR, blank()), ("STAR1", 0, AIR, t_star(0)), ("STAR2", 0, AIR, t_star(1)),
 ("ROCK", 1, SOLID, t_rock()), ("ROCKTOP", 1, SOLID, t_rock(True)),
 ("SAND", 2, SOLID, t_sand()), ("SANDTOP", 2, SOLID, t_sand(True)),
 ("DOCK", 2, PLAT, t_dock()), ("DOCKPOST", 2, PLAT, t_dock(True)), ("POST", 2, AIR, t_post()),
 ("URCHIN", 2, HAZ, URCHIN), ("CORAL", 3, CORAL, t_coral(False), t_coral(True)),
 ("DOOR", 3, DOOR, t_door()), ("LAMP", 3, AIR, t_lamp(False)), ("LAMPLIT", 3, AIR, t_lamp(True)),
 ("CRATE", 2, SOLID, t_crate()), ("CASTLE", 2, CASTLE, t_castle(False), t_castle(True)),
] + [("MOON%d" % i, 0, AIR, t) for i, t in enumerate(moon_tiles())] + [
 ("ROOF_L", 3, AIR, t_roof(True)), ("ROOF_R", 3, AIR, t_roof(False)),
 ("BLAMP_L", 3, AIR, t_biglamp(True, False)), ("BLAMP_R", 3, AIR, t_biglamp(False, False)),
 ("BLIT_L", 3, AIR, t_biglamp(True, True)), ("BLIT_R", 3, AIR, t_biglamp(False, True)),
 ("RED_L", 3, SOLID, t_band(1, True)), ("RED_R", 3, SOLID, t_band(1, False)),
 ("WHITE_L", 3, SOLID, t_band(2, True)), ("WHITE_R", 3, SOLID, t_band(2, False)),
 ("WIN_R", 3, SOLID, t_band(1, False, "window", True)), ("BIGDOOR", 3, SOLID, t_band(2, False, "door")),
 ("BEAM1", 3, AIR, t_beam(0)), ("BEAM2", 3, AIR, t_beam(1)), ("BEAM3", 3, AIR, t_beam(2)),
]

WATER = blank(1)
for (x, y) in [(2, 3), (3, 3), (4, 3), (10, 9), (11, 9), (12, 9), (13, 9), (6, 13), (7, 13)]: WATER[y][x] = 2
for (x, y) in [(9, 2), (10, 2), (1, 10), (2, 10), (3, 10), (13, 14)]: WATER[y][x] = 0

# --------------------------------------------------------------- allocation
def enc(t):
    p0 = bytes(sum(((t[y][x] & 1) << (7 - x)) for x in range(8)) for y in range(8))
    p1 = bytes(sum(((t[y][x] >> 1) << (7 - x)) for x in range(8)) for y in range(8))
    return p0 + p1

bg_dry = [None] * 256; bg_wet = [None] * 256; index = {}
def alloc(dry, wet, dynamic):
    key = (enc(dry), enc(wet))
    if key in index: return index[key]
    order = list(range(0, 128)) if dynamic else list(range(128, 256)) + list(range(127, -1, -1))
    for i in order:
        if bg_dry[i] is None and i != 0xFF:
            bg_dry[i], bg_wet[i] = key; index[key] = i; return i
    raise SystemExit("out of BG tiles")

font_ids = {" ": alloc([[0] * 8] * 8, [[0] * 8] * 8, False)}
for ch in FONT: t = glyph_tile(ch); font_ids[ch] = alloc(t, t, False)
assert all(font_ids[chr(65 + i)] == font_ids["A"] + i for i in range(26))
assert all(font_ids[str(i)] == font_ids["0"] + i for i in range(10))

def quad(t, qx, qy): return [row[qx * 8:qx * 8 + 8] for row in t[qy * 8:qy * 8 + 8]]

mt_rows = []
for m in MT:
    name, pal, typ, dry = m[:4]
    wet_src = m[4] if len(m) > 4 else None
    ids = []
    for (qx, qy) in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        d = quad(dry, qx, qy)
        has_air = any(v == A for r in d for v in r)
        w = quad(wet_src, qx, qy) if wet_src is not None else d
        dyn = has_air or wet_src is not None
        w = [[(WATER[qy * 8 + y][qx * 8 + x] if pal == 0 else (1 if pal == 2 else 0)) if v == A else v
              for x, v in enumerate(r)] for y, r in enumerate(w)]
        d = [[0 if v == A else v for v in r] for r in d]
        ids.append(alloc(d, w, dyn))
    mt_rows.append((name, pal, typ, ids))
assert mt_rows[0][3][0] == 0, mt_rows[0]


def small(rows, key):
    t = art(rows, key); return alloc(t, t, False)
K3 = {".": 0, "r": 1, "w": 2, "y": 3}
ICON_EMPTY = small(["........", "...r....", "..r.r...", ".r...r..", ".r...r..", ".r...r..", "..rrr...", "........"], K3)
ICON_CARRY = small(["...r....", "..ryr...", "..ryr.r.", ".ryyyr..", ".ryyyr..", ".ryyyr..", "..rrr...", "........"], K3)
ICON_BANK = small(["...w....", "..www...", "..www.w.", ".wwwww..", ".wwwww..", ".wwwww..", "..www...", "........"], K3)
K0 = {".": 0, "c": 2, "w": 3}
PIP_OFF = small(["........", ".wwwww..", ".w...w..", ".w...w..", ".w...w..", ".w...w..", ".wwwww..", "........"], K0)
PIP_ON = small(["........", ".wwwww..", ".wcccw..", ".wcccw..", ".wcccw..", ".wcccw..", ".wwwww..", "........"], K0)

# logo: each letter is 16x24 (2x3 tiles), 3x font with a drop shadow
def logo_letter(ch):
    img = [[0] * 16 for _ in range(24)]
    for r in range(7):
        for c in range(5):
            if FONT[ch][r][c] == "1":
                for dy in range(3):
                    for dx in range(3):
                        y, x = r * 3 + dy, c * 3 + dx
                        if img[y + 1][x + 1] == 0: img[y + 1][x + 1] = 1
                        img[y][x] = 3 if r < 3 else 2
    out = []
    for ty in range(3):
        for tx in range(2):
            t = [row[tx * 8:tx * 8 + 8] for row in img[ty * 8:ty * 8 + 8]]
            out.append(alloc(t, t, False))
    return out
LOGO = [logo_letter(c) for c in "TIDEBELL"]

# ------------------------------------------------------------------ sprites
spr_tiles = []; spr_index = {}
def salloc(t):
    if not spr_tiles: spr_tiles.append(bytes(16)); spr_index[bytes(16)] = 0
    k = enc(t)
    if k not in spr_index: spr_index[k] = len(spr_tiles); spr_tiles.append(k)
    return spr_index[k]
def frame16(rows, key):
    t = art(rows, key)
    return [salloc(quad(t, qx, qy)) for (qx, qy) in [(0, 0), (1, 0), (0, 1), (1, 1)]]
PK = {".": 0, "k": 1, "y": 2, "b": 3}
PIM_TOP = [
 "................", ".....kkkkkk.....", "....kyyyyyyk....", "...kyyyyyyyyk...", "..kkkkkkkkkkkk..",
 "...kbbbbbbbbk...", "...kbkbbbbkbk...", "...kbbbkkbbbk...", "....kbbbbbbk....", "...kyyyyyyyyk...",
 "..kyykyyyykyyk..", "..kbkyyyyyykbk..", "...kyyyyyyyyk..."]
FRAMES = [
 ("PIM_IDLE", frame16(PIM_TOP + ["...kyyykkyyyk...", "...kbbk..kbbk...", "...kkkk..kkkk..."], PK)),
 ("PIM_WALK1", frame16(PIM_TOP + ["..kyyykkkyyyk...", "..kbbk...kbbk...", "..kkk.....kkkk.."], PK)),
 ("PIM_WALK2", frame16(PIM_TOP + ["...kyyykyyyk....", "....kbbkbbk.....", "....kkkkkkk....."], PK)),
 ("PIM_JUMP", frame16([
 "................", ".....kkkkkk.....", "....kyyyyyyk....", "...kyyyyyyyyk...", "..kkkkkkkkkkkk..",
 ".k.kbbbbbbbbk.k.", "kbkkbkbbbbkbkkbk", "kykkbbbkkbbbkkyk", ".kykkbbbbbbkkyk.", "..kyyyyyyyyyyk..",
 "...kyyyyyyyyk...", "...kyyyyyyyyk...", "...kyyyyyyyyk...", "..kbbykkkkybbk..", "..kkkk....kkkk..",
 "................"], PK)),
 ("PIM_BELL", frame16([
 "................", ".....kkkkkk.....", "....kyyyyyyk....", "...kyyyyyyyyk.k.", "..kkkkkkkkkkkkyk",
 "...kbbbbbbbbkyyy", "...kbkbbbbkbkyyy", "...kbbbkkbbbk.k.", "....kbbbbbbkkbk.", "...kyyyyyyyyykk.",
 "..kyykyyyyyykk..", "..kbkyyyyyyk....", "...kyyyyyyyyk...", "...kyyykkyyyk...", "...kbbk..kbbk...",
 "...kkkk..kkkk..."], PK)),
 ("PIM_SWIM1", frame16([
 "................", "................", "................", "................", "..........kkkk..",
 ".k.......kyyyyk.", "kbk....kkkkkkkkk", "kbbk.kkyyykbbbbk", ".kbbkyyyyykbkbbk", "..kbyyyyyykbbbkk",
 "...kkyyyyykbbbk.", "....kbkkykkkkk..", "....kk.kbk......", "........k.......", "................",
 "................"], PK)),
 ("PIM_SWIM2", frame16([
 "................", "................", "................", "................", "..........kkkk..",
 ".........kyyyyk.", ".......kkkkkkkkk", ".....kkyyykbbbbk", ".kkkkyyyyykbkbbk", "kbbbyyyyyykbbbkk",
 "kbkkkyyyyykbbbk.", ".k..kkbkykkkkk..", ".....kbk.k......", "......k.........", "................",
 "................"], PK)),
]
CK = {".": 0, "r": 1, "o": 2, "w": 3}
CRAB_A = [
 "................", "................", "................", ".rr.........rr..", "rwor.......rowr.",
 "rr.r.......r.rr.", ".rr..w...w..rr..", "..r..r...r..r...", "..rrrrrrrrrrr...", ".rrorrrrrrrorr..",
 ".rrrrorrrorrrr..", "..rrrrrrrrrrr..."]
FRAMES += [
 ("CRAB1", frame16(CRAB_A + [".r.rr.....rr.r..", "r..r.r...r.r..r.", "................", "................"], CK)),
 ("CRAB2", frame16(CRAB_A + ["..r.rr...rr.r...", ".r.r..r.r..r.r..", "................", "................"], CK)),
 ("CRAB_SLEEP", frame16([
 "................", "................", "................", "................", "................",
 "................", "................", "..rr.......rr...", ".rworrrrrrrowr..", ".rrorrrrrrrorr..",
 ".rrrrorrrorrrr..", "..rrrrrrrrrrr...", "................", "................", "................",
 "................"], CK)),
]
JK = {".": 0, "m": 1, "p": 2, "w": 3}
JELLY_A = [
 "................", ".....mmmmmm.....", "...mmppppppmm...", "..mppwwppppppm..", "..mpwwpppppppm..",
 ".mppwppppppppmm.", ".mppppppppppppm.", ".mmpmmpmmpmmpmm."]
FRAMES += [
 ("JELLY1", frame16(JELLY_A + ["..p..m..p..m..p.", "..p..m..p..m..p.", ".p..m..p..m..p..", ".p..m..p..m..p..",
                               "..p..m..p..m..p.", "..p.....p.....p.", "................", "................"], JK)),
 ("JELLY2", frame16(JELLY_A + [".p..m..p..m..p..", ".p..m..p..m..p..", "..p..m..p..m..p.", "..p..m..p..m..p.",
                               ".p..m..p..m..p..", ".p.....p.....p..", "................", "................"], JK)),
]
def s8(rows, key): return salloc(art(rows, key))
EMB = ["....r...", "...ro.r.", "..roor..", ".roowor.", ".rowwor.", ".rowwor.", "..roor..", "...rr..."]
SPR = {
 "SPR_EMBER": s8(EMB, CK),
 "SPR_EMBER_DIM": s8(EMB, {".": 0, "r": 1, "o": 1, "w": 2}),
 "SPR_GLINT": s8(["wwwwww..", ".ww.....", "........", "........", "........", "........", "........", "........"], JK),
 "SPR_POOF1": s8(["..w..w..", ".w.ww.w.", "w.w..w.w", ".w....w.", ".w....w.", "w.w..w.w", ".w.ww.w.", "..w..w.."], CK),
 "SPR_POOF2": s8(["w..w...w", "........", "...w....", "w......w", "........", "....w...", "........", "w..w...w"], CK),
 "SPR_NOTE": s8(["...yy...", "...y.y..", "...y..y.", "...y....", ".yyy....", "yyyy....", ".yy.....", "........"], PK),
}
raft = [[0] * 16 for _ in range(8)]
for y in range(1, 7):
    for x in range(16):
        if y in (1, 6) and x == 0: continue
        raft[y][x] = 1 if (y in (1, 6) or x == 0 or x % 8 == 7) else (3 if y == 2 else 2)
SPR["SPR_RAFT_L"] = salloc([r[:8] for r in raft]); SPR["SPR_RAFT_M"] = salloc([r[8:] for r in raft])
assert len(spr_tiles) <= 256

# ------------------------------------------------------------------- output
os.makedirs(OUT, exist_ok=True)
Z = bytes(16)
chr_ = bytearray(16384)
for i in range(256):
    d, w = bg_dry[i] or Z, bg_wet[i] or Z
    chr_[i * 16:i * 16 + 16] = d
    if i < 128: chr_[0x2000 + i * 16:0x2000 + i * 16 + 16] = w
for i, t in enumerate(spr_tiles): chr_[0x1000 + i * 16:0x1000 + i * 16 + 16] = t
open(f"{OUT}/tidebell.chr", "wb").write(chr_)

def bl(xs): return ", ".join("$%02X" % x for x in xs)
with open(f"{OUT}/gfx.inc", "w") as f:
    f.write("; generated by tools/build_chr.py\n")
    for i, (name, pal, typ, ids) in enumerate(mt_rows): f.write(f"MT_{name} = {i}\n")
    for k, nm in enumerate(["mt_tl", "mt_tr", "mt_bl", "mt_br"]):
        f.write(f"{nm}: .byte {bl([m[3][k] for m in mt_rows])}\n")
    f.write(f"mt_pal: .byte {bl([m[1] for m in mt_rows])}\n")
    f.write(f"mt_type: .byte {bl([m[2] for m in mt_rows])}\n")
    f.write(f"T_A = ${font_ids['A']:02X}\nT_0 = ${font_ids['0']:02X}\nT_SPACE = ${font_ids[' ']:02X}\n")
    for ch, i in font_ids.items(): f.write(f".charmap ${ord(ch):02X}, ${i:02X}\n")
    for nm in ("ICON_EMPTY", "ICON_CARRY", "ICON_BANK", "PIP_OFF", "PIP_ON"): f.write(f"T_{nm} = ${globals()[nm]:02X}\n")
    for r in range(3):
        f.write(f"logo_row{r}: .byte {bl([L[r * 2 + k] for L in LOGO for k in (0, 1)])}, $FF\n")
    for i, (name, ids) in enumerate(FRAMES): f.write(f"F_{name} = {i * 4}\n")
    f.write(f"frame_tiles: .byte {bl([t for _, ids in FRAMES for t in ids])}\n")
    for k, v in SPR.items(): f.write(f"{k} = ${v:02X}\n")
# python-side copy for the level builder
with open(f"{OUT}/gfx.py", "w") as f:
    f.write("MT = %r\nFONT = %r\n" % ({m[0]: i for i, m in enumerate(mt_rows)}, sorted(font_ids)))
used = sum(1 for t in bg_dry if t is not None)
print(f"chr: {used} bg tiles, {len(spr_tiles)} sprite tiles, {len(mt_rows)} metatiles")
