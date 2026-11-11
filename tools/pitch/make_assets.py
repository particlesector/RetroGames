#!/usr/bin/env python3
"""Renders the TIDEBELL pitch mockups under NES constraints.

Everything is built from 16x16 metatiles with one 4-colour palette each
(= NES attribute cells) and 3-colour sprites, using 2C02 palette indices.
These are mockups, not emulator captures.
"""
import os, sys
from PIL import Image

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/pitch"
W, H = 256, 240

NES = {}
_rows = [
 "626262 001FB2 2404C8 5200B2 730076 800024 730B00 522800 244400 005700 005C00 005324 003C76 000000 000000 000000",
 "ABABAB 0D57FF 4B30FF 8A13FF BC08D6 D21269 C72E00 9D5400 607B00 209800 00A300 009942 007DB4 000000 000000 000000",
 "FFFFFF 53AEFF 9085FF D365FF FF57FF FF5DCF FF7757 FA9E00 BDC700 7AE700 43F611 26EF7E 2CD5F6 4E4E4E 000000 000000",
 "FFFFFF B6E1FF CED1FF E9C3FF FFBCFF FFBDF4 FFC6C3 FFD59A E9E681 CEF481 B6FB9A A9FAC3 A9F0F4 B8B8B8 000000 000000"]
for r, row in enumerate(_rows):
    for c, hx in enumerate(row.split()):
        NES[r * 16 + c] = tuple(int(hx[i:i + 2], 16) for i in (0, 2, 4))

SKY = 0x0C
BG_PAL = [
    [SKY, 0x1C, 0x2C, 0x30],   # 0 sky / water / text
    [SKY, 0x00, 0x10, 0x1A],   # 1 sea-stone + moss
    [SKY, 0x1C, 0x17, 0x37],   # 2 wood + sand (shares water blue)
    [SKY, 0x16, 0x30, 0x38],   # 3 lighthouse
]
SPR_PAL = [
    [0x0F, 0x28, 0x17],        # 0 Pim: outline, raincoat, fur
    [0x16, 0x27, 0x30],        # 1 ember / crab
    [0x14, 0x25, 0x30],        # 2 jellyfish / foam
    [0x0F, 0x17, 0x27],        # 3 driftwood
]
BG_NAMES = ["SKY-WATER", "STONE-MOSS", "WOOD-SAND", "LIGHTHOUSE"]
SPR_NAMES = ["PIM", "EMBER-CRAB", "JELLY-FOAM", "DRIFTWOOD"]

def tint(c):  # PPUMASK blue-emphasis approximation
    return (int(c[0] * .72), int(c[1] * .78), c[2])

# ---------------------------------------------------------------- font
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
 "-": "00000/00000/00000/11111/00000/00000/00000", " ": "00000/00000/00000/00000/00000/00000/00000",
}.items()}

def text_pixels(s, x, y, scale=1):
    """yield (px, py, row) for lit pixels; row = glyph row 0..6"""
    for i, ch in enumerate(s):
        g = FONT[ch]
        for r in range(7):
            for c in range(5):
                if g[r][c] == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            yield x + (i * 6 + c) * scale + dx, y + r * scale + dy, r

# ------------------------------------------------------------- sprites
def spr(rows, key):
    w = len(rows[0])
    assert all(len(r) == w for r in rows), [len(r) for r in rows]
    return [[key.get(ch, 0) for ch in r] for r in rows]

PK = {"k": 1, "y": 2, "b": 3}
PIM_TOP = [
 "................",
 ".....kkkkkk.....",
 "....kyyyyyyk....",
 "...kyyyyyyyyk...",
 "..kkkkkkkkkkkk..",
 "...kbbbbbbbbk...",
 "...kbkbbbbkbk...",
 "...kbbbkkbbbk...",
 "....kbbbbbbk....",
 "...kyyyyyyyyk...",
 "..kyykyyyykyyk..",
 "..kbkyyyyyykbk..",
 "...kyyyyyyyyk..."]
PIM_IDLE = spr(PIM_TOP + [
 "...kyyykkyyyk...",
 "...kbbk..kbbk...",
 "...kkkk..kkkk..."], PK)
PIM_WALK = spr(PIM_TOP + [
 "..kyyykkkyyyk...",
 "..kbbk...kbbk...",
 "..kkk.....kkkk.."], PK)
PIM_BELL = spr([
 "................",
 ".....kkkkkk.....",
 "....kyyyyyyk....",
 "...kyyyyyyyyk.k.",
 "..kkkkkkkkkkkkyk",
 "...kbbbbbbbbkyyy",
 "...kbkbbbbkbkyyy",
 "...kbbbkkbbbk.k.",
 "....kbbbbbbkkbk.",
 "...kyyyyyyyyykk.",
 "..kyykyyyyyykk..",
 "..kbkyyyyyyk....",
 "...kyyyyyyyyk...",
 "...kyyykkyyyk...",
 "...kbbk..kbbk...",
 "...kkkk..kkkk..."], PK)
PIM_SWIM = spr([
 "................",
 "................",
 "................",
 "................",
 "..........kkkk..",
 ".k.......kyyyyk.",
 "kbk....kkkkkkkkk",
 "kbbk.kkyyykbbbbk",
 ".kbbkyyyyykbkbbk",
 "..kbyyyyyykbbbkk",
 "...kkyyyyykbbbk.",
 "....kbkkykkkkk..",
 "....kk.kbk......",
 "........k.......",
 "................",
 "................"], PK)
CK = {"r": 1, "o": 2, "w": 3}
CRAB = spr([
 "................",
 "................",
 "................",
 ".rr.........rr..",
 "rwor.......rowr.",
 "rr.r.......r.rr.",
 ".rr..w...w..rr..",
 "..r..r...r..r...",
 "..rrrrrrrrrrr...",
 ".rrorrrrrrrorr..",
 ".rrrrorrrorrrr..",
 "..rrrrrrrrrrr...",
 ".r.rr.....rr.r..",
 "r..r.r...r.r..r.",
 "................",
 "................"], CK)
EMBER = spr([
 "....r...",
 "...ro.r.",
 "..roor..",
 ".roowor.",
 ".rowwor.",
 ".rowwor.",
 "..roor..",
 "...rr..."], CK)
JK = {"m": 1, "p": 2, "w": 3}
JELLY = spr([
 "................",
 ".....mmmmmm.....",
 "...mmppppppmm...",
 "..mppwwppppppm..",
 "..mpwwpppppppm..",
 ".mppwppppppppmm.",
 ".mppppppppppppm.",
 ".mmpmmpmmpmmpmm.",
 "..p..m..p..m..p.",
 "..p..m..p..m..p.",
 ".p..m..p..m..p..",
 ".p..m..p..m..p..",
 "..p..m..p..m..p.",
 "..p.....p.....p.",
 "................",
 "................"], JK)
GLINT = spr(["wwwwww..", ".ww....."], JK)
RAFT = [[0] * 32 for _ in range(8)]
for y in range(1, 7):
    for x in range(32):
        e = y in (1, 6) or x in (0, 31) or x % 8 == 7
        if (y in (1, 6)) and x in (0, 31): continue
        RAFT[y][x] = 1 if e else (3 if y == 2 else 2)

# ------------------------------------------------------------- tiles
A = 4  # "air" pixel: sky above the tide line, water below it
def h(x, y, s=0): return ((x * 73856093) ^ (y * 19349663) ^ (s * 83492791)) >> 3 & 0xFF

def t_air(): return [[A] * 16 for _ in range(16)]
def t_rock(grass=False):
    t = [[1] * 16 for _ in range(16)]
    for y in range(16):
        for x in range(16):
            c, ry = y // 8, y % 8
            jx = (x + (4 if c else 0)) % 8
            if ry == 7 or jx == 7: t[y][x] = 0
            elif ry == 0 or jx == 0: t[y][x] = 2
    if grass:
        for x in range(16):
            for y in range(3): t[y][x] = 3
            t[3][x] = 3 if h(x, 3) % 3 else t[3][x]
            if h(x, 9) % 4 == 0: t[4][x] = 3
    return t
def t_sand(top=False):
    t = [[3] * 16 for _ in range(16)]
    for y in range(16):
        for x in range(16):
            if h(x, y, 5) % 11 == 0: t[y][x] = 2
    if top:
        for x in range(16):
            t[0][x] = 2 if (x // 2) % 4 else 3
            t[1][x] = 3
    return t
def t_dock():
    t = t_air()
    for x in range(16):
        t[0][x] = 3; t[1][x] = 3; t[2][x] = 2; t[3][x] = 2; t[4][x] = 0
        if x % 8 == 7: t[0][x] = t[1][x] = t[2][x] = t[3][x] = 0
    return t
def t_post(under_dock=False):
    t = t_air()
    for y in range(16):
        for x in range(6, 10):
            t[y][x] = 3 if x == 6 else 2
        if y % 8 == 5:
            for x in range(6, 10): t[y][x] = 0
    return t
def t_dockpost():
    t, p = t_dock(), t_post()
    for y in range(5, 16): t[y] = p[y]
    return t
def t_band(col, left, feature=None, lit=False):
    t = [[col] * 16 for _ in range(16)]
    for y in range(16):
        for x in range(16):
            if y % 4 == 3 and (x + (y // 4) * 4) % 8 == 0: t[y][x] = 0 if col == 2 else 2
    for y in range(16):
        if left: t[y][0] = 0
        else: t[y][15] = 0; t[y][14] = 0 if col == 2 else t[y][14]
    if feature == "window":
        for y in range(4, 12):
            for x in range(5, 11):
                edge = y in (4, 11) or x in (5, 10)
                t[y][x] = 0 if edge else (3 if lit else 0)
        for y in range(5, 11): t[y][7] = 3 if lit else 2
    if feature == "door":
        for y in range(3, 16):
            for x in range(3, 13):
                if y == 3 and x in (3, 4, 11, 12): continue
                if y == 4 and x in (3, 12): continue
                t[y][x] = 0
        for y in range(6, 9):
            for x in range(6, 10): t[y][x] = 3
        t[11][10] = 3
    return t
def t_lamp(left, lit):
    t = [[3 if lit else 0] * 16 for _ in range(16)]
    for y in range(16):
        for x in range(16):
            if y in (0, 15) or x % 8 == (0 if left else 7): t[y][x] = 2
            if not lit and (x + y) % 8 == 3 and y not in (0, 15): t[y][x] = 2 if h(x, y) % 2 else t[y][x]
    for y in range(16): t[y][0 if left else 15] = 2
    return t
def t_roof(left):
    t = t_air()
    for y in range(6, 16):
        for x in range(16):
            xx = x if left else 15 - x
            if xx >= 15 - (y - 6) * 2:
                t[y][x] = 2 if y == 15 else 1
    if left:
        for y in range(1, 6): t[y][15] = 2
    else:
        t[1][0] = t[2][0] = 1
    return t

def tileset(lit):
    return {
        " ": (0, t_air()),
        "R": (1, t_rock()), "G": (1, t_rock(True)),
        "S": (2, t_sand(True)), "s": (2, t_sand()),
        "D": (2, t_dock()), "d": (2, t_dockpost()), "P": (2, t_post()),
        "L": (3, t_band(1, True)), "l": (3, t_band(1, False)),
        "W": (3, t_band(2, True)), "w": (3, t_band(2, False)),
        "I": (3, t_band(1, False, "window", lit)), "i": (3, t_band(2, True, "window", lit)),
        "O": (3, t_band(2, False, "door")),
        "T": (3, t_lamp(True, lit)), "t": (3, t_lamp(False, lit)),
        "A": (3, t_roof(True)), "a": (3, t_roof(False)),
        "*": (3, t_air()),   # sky cell coloured by the lighthouse palette (beam)
    }

WATER = [[1] * 16 for _ in range(16)]
for (x, y) in [(2, 3), (3, 3), (4, 3), (10, 9), (11, 9), (12, 9), (13, 9), (6, 13), (7, 13)]:
    WATER[y][x] = 2
for (x, y) in [(9, 2), (10, 2), (1, 10), (2, 10), (3, 10), (13, 14)]:
    WATER[y][x] = 0

# ------------------------------------------------------------ renderer
def render(level, tiles, overlay, wl, sprites, tick=0):
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        row = level[y // 16]
        for x in range(W):
            pal, t = tiles[row[x // 16]]
            v = t[y & 15][x & 15]
            if v == A:
                if y >= wl:
                    v = WATER[y & 15][(x + tick // 6) & 15] if pal == 0 else 1
                else:
                    o = overlay.get((x, y))
                    v = o if o is not None else 0
            px[x, y] = NES[BG_PAL[pal][v]]
    for (sx, sy, art, pal, flip) in sprites:
        w = len(art[0])
        for j, r in enumerate(art):
            for i in range(w):
                v = r[w - 1 - i] if flip else r[i]
                X, Y = sx + i, sy + j
                if v and 0 <= X < W and 0 <= Y < H:
                    px[X, Y] = NES[SPR_PAL[pal][v - 1]]
    for y in range(max(0, wl + 2), H):     # raster split: emphasis on below the surface
        for x in range(W):
            px[x, y] = tint(px[x, y])
    return img

def sky_overlay(level, moon, seed, star_rows):
    o = {}
    for cy in range(star_rows):
        for cx in range(16):
            if level[cy][cx] != " ": continue
            for k in range(2):
                hv = h(cx, cy, seed + k)
                if hv % 3 == 0:
                    x, y = cx * 16 + hv % 16, cy * 16 + (hv // 16) % 16
                    o[(x, y)] = 3 if hv % 2 else 2
    mx, my, r = moon
    for y in range(my - r, my + r + 1):
        for x in range(mx - r, mx + r + 1):
            d = (x - mx) ** 2 + (y - my) ** 2
            if d <= r * r:
                d2 = (x - mx - 6) ** 2 + (y - my + 4) ** 2
                if d2 > (r - 1) ** 2: o[(x, y)] = 3 if d < (r - 2) ** 2 else 2
                else: o.pop((x, y), None)
    return o

def put_text(o, s, x, y, col=3, scale=1, split=None, shadow=None):
    if shadow is not None:
        for (X, Y, r) in text_pixels(s, x + scale, y + scale, scale): o[(X, Y)] = shadow
    for (X, Y, r) in text_pixels(s, x, y, scale):
        o[(X, Y)] = col if split is None or r < 3 else split

# ----------------------------------------------------------- game room
ROOM = [
 "                ",
 "                ",
 "                ",
 "            Aa  ",
 "            Tt  ",
 "            Ll  ",
 "            Ww  ",
 "     GG     LI  ",
 "            WO  ",
 "GG         GGGGG",
 "RRDdDDd    RRRRR",
 "RR P  P     RRRR",
 "RR P  P      RRR",
 "RRSSSSSSSSSSSRRR",
 "RRssssssssssssRR"]
LOW, MID, HIGH = 203, 176, 148

def room_frame(wl, tick, ring=False, lit=False, embers=(1, 1, 1)):
    tiles = tileset(lit)
    o = sky_overlay(ROOM, (40, 56, 13), 7, 9)
    put_text(o, "ROOM 1-3", 16, 12)
    put_text(o, "TIDE", 176, 12)
    lvl = 0 if wl > 190 else (1 if wl > 162 else 2)
    for i in range(3):
        for y in range(11, 20):
            for x in range(206 + i * 10, 214 + i * 10):
                edge = y in (11, 19) or x in (206 + i * 10, 213 + i * 10)
                if edge: o[(x, y)] = 3
                elif i <= lvl: o[(x, y)] = 2
    bob = (tick // 8) % 2
    s = []
    for i, e in enumerate(embers):
        if e: s.append((88 + i * 12, 11, EMBER, 1, False))
    s.append((84, 96 - bob, EMBER, 1, False))                 # high ledge ember
    if wl > 200: s.append((152, 193 + bob, EMBER, 1, False))               # tide-pool ember
    s.append((216, 128 - bob, EMBER, 1, False))               # by the door
    cx = 62 + abs((tick // 3) % 40 - 20)
    s.append((cx, 194, CRAB, 1, (tick // 3) % 40 >= 20))
    if wl < 180:
        s.append((152, max(wl + 6, 172 + 4 * bob), JELLY, 2, False))
    s.append((112, wl - 5 + bob, RAFT, 3, False))             # driftwood floats
    for i in range(4):                                        # 4 foam glints, <8 per line
        gx = (i * 67 + tick // 2 + 30) % 250
        if ROOM[min(14, wl // 16)][gx // 16] == " ":
            s.append((gx, wl, GLINT, 2, False))
    py = 144
    if wl - 9 < py: s.append((40, wl - 9 + bob, PIM_SWIM, 0, False))
    else: s.append((40, py, PIM_BELL if ring else PIM_IDLE, 0, False))
    return render(ROOM, tiles, o, wl, s, tick)

# -------------------------------------------------------- title screen
TITLE = [
 "                ",
 "                ",
 "                ",
 "                ",
 "                ",
 "            Aa  ",
 "************Tt  ",
 "            Ll  ",
 "            Ww  ",
 "            LI  ",
 "            iO  ",
 "  G       GGGGGG",
 " GRG      RRRRRR",
 "RRRRR    RRRRRRR",
 "RRRRRR  RRRRRRRR"]
def title_frame(tick=0):
    tiles = tileset(True)
    o = sky_overlay(TITLE, (222, 44, 15), 3, 11)
    for x in range(0, 192):                                   # dithered beam, lighthouse palette
        half = 1 + (192 - x) // 26
        for y in range(104 - half, 104 + half + 1):
            if (x + y) % 2 == 0 and 96 <= y < 112: o[(x, y)] = 3
    for k in [k for k in o if 80 <= k[1] < 96 or 112 <= k[1] < 128]:
        pass
    put_text(o, "TIDEBELL", 56, 36, col=3, scale=3, split=2, shadow=1)
    put_text(o, "A TALE OF THE LAST LIGHTHOUSE", 41, 66, col=2)
    if (tick // 16) % 2 == 0: put_text(o, "PRESS START", 95, 140)
    s = [(34, 160, PIM_BELL, 0, False), (150, 196, JELLY, 2, False), (72, 178, RAFT, 3, False)]
    for i in range(4): s.append(((i * 61 + tick // 2 + 90) % 80 + 76, 183, GLINT, 2, False))
    return render(TITLE, tiles, o, 183, s, tick)

# --------------------------------------------------------------- sheets
def up(img, k): return img.resize((img.width * k, img.height * k), Image.NEAREST)

def label(img, s, x, y, col=(255, 255, 255)):
    px = img.load()
    for (X, Y, r) in text_pixels(s, x, y):
        if 0 <= X < img.width and 0 <= Y < img.height: px[X, Y] = col

def sprite_sheet():
    items = [("PIM IDLE", PIM_IDLE, 0), ("WALK", PIM_WALK, 0), ("RING", PIM_BELL, 0), ("SWIM", PIM_SWIM, 0),
             ("CRAB", CRAB, 1), ("JELLY", JELLY, 2), ("EMBER", EMBER, 1), ("DRIFTWOOD", RAFT, 3)]
    img = Image.new("RGB", (4 * 64, 2 * 44), NES[SKY]); px = img.load()
    for n, (name, art, pal) in enumerate(items):
        ox, oy = (n % 4) * 64, (n // 4) * 44
        w = len(art[0]); x0 = ox + (64 - w) // 2; y0 = oy + 6 + (16 - len(art)) // 2
        for j, r in enumerate(art):
            for i, v in enumerate(r):
                if v: px[x0 + i, y0 + j] = NES[SPR_PAL[pal][v - 1]]
        label(img, name, ox + (64 - len(name) * 6) // 2, oy + 30)
    return img

def tile_sheet():
    ts = tileset(False); lit = tileset(True)
    keys = [("R", ts), ("G", ts), ("S", ts), ("s", ts), ("D", ts), ("d", ts), ("P", ts), ("A", ts), ("a", ts),
            ("T", ts), ("T", lit), ("L", ts), ("W", ts), ("I", lit), ("O", ts)]
    img = Image.new("RGB", (len(keys) * 18 + 2, 2 * 18 + 2), (0, 0, 0)); px = img.load()
    for n, (k, src) in enumerate(keys):
        pal, t = src[k]
        for row in range(2):      # top: dry bank, bottom: submerged bank + emphasis
            for y in range(16):
                for x in range(16):
                    v = t[y][x]
                    if v == A: v = 0 if row == 0 else (WATER[y][x] if pal == 0 else 1)
                    c = NES[BG_PAL[pal][v]]
                    px[2 + n * 18 + x, 2 + row * 18 + y] = c if row == 0 else tint(c)
    return img

def palette_sheet():
    img = Image.new("RGB", (256, 108), (16, 16, 24)); px = img.load()
    def sw(x, y, idx):
        for j in range(14):
            for i in range(22): px[x + i, y + j] = NES[idx]
        s = "%02X" % idx
        lum = sum(NES[idx])
        label(img, s, x + 5, y + 4, (0, 0, 0) if lum > 380 else (255, 255, 255))
    label(img, "BACKGROUND", 4, 3); label(img, "SPRITES", 148, 3)
    for p in range(4):
        y = 14 + p * 23
        for i, idx in enumerate(BG_PAL[p]): sw(4 + i * 24, y, idx)
        label(img, BG_NAMES[p], 4, y + 15, (150, 160, 190))
        for i, idx in enumerate(SPR_PAL[p]): sw(148 + i * 24, y, idx)
        label(img, SPR_NAMES[p], 148, y + 15, (150, 160, 190))
    return img

def main():
    os.makedirs(OUT, exist_ok=True)
    lo = room_frame(LOW, 0); mid = room_frame(MID, 8); hi = room_frame(HIGH, 0)
    up(lo, 3).save(f"{OUT}/room_low_tide.png"); up(hi, 3).save(f"{OUT}/room_high_tide.png")
    trip = Image.new("RGB", (W * 3 + 16, H), (0, 0, 0))
    for i, im in enumerate((lo, mid, hi)): trip.paste(im, (i * (W + 8), 0))
    up(trip, 2).save(f"{OUT}/tide_levels.png")
    up(title_frame(), 3).save(f"{OUT}/title.png")
    up(sprite_sheet(), 4).save(f"{OUT}/sprites.png")
    up(tile_sheet(), 4).save(f"{OUT}/tiles.png")
    up(palette_sheet(), 3).save(f"{OUT}/palettes.png")
    frames, t = [], 0
    def seg(a, b, n, ring=False):
        nonlocal t
        for i in range(n):
            wl = round(a + (b - a) * (i / max(1, n - 1)))
            frames.append(up(room_frame(wl, t, ring and (t // 6) % 2 == 0), 2)); t += 2
    seg(LOW, LOW, 10); seg(LOW, LOW, 8, True); seg(LOW, MID, 14); seg(MID, MID, 8)
    seg(MID, MID, 8, True); seg(MID, HIGH, 20); seg(HIGH, HIGH, 16); seg(HIGH, LOW, 30)
    frames[0].save(f"{OUT}/tide_demo.gif", save_all=True, append_images=frames[1:], duration=66, loop=0)
    print("wrote", sorted(os.listdir(OUT)))

main()
