"""Trackside objects. Each is pixel art on the 16-pixel grid in the roles of one palette,
so every attribute cell it touches stays inside the NES's four-colours-per-cell limit."""
import numpy as np
from nespal import *

def art(rows, key):
    w = len(rows[0]); assert all(len(r) == w for r in rows), [len(r) for r in rows]
    return np.array([[key[c] for c in r] for r in rows])

N = {".": -1, "d": GD, "l": GL, "g": G, "s": SA}
TREE = art([
 "....dddddd......",
 "..ddllllllldd...",
 ".dllllllllllld..",
 ".dllldlllllllld.",
 "dlllllllldllllld",
 "dllllllllllldlgd",
 "dlldllllllllgggd",
 "dllllllldllggggd",
 "dllllllllllggggd",
 "dllllldlllgggggd",
 ".dlllllllggggdd.",
 ".dllllgggggggdd.",
 "..ddggggggggddd.",
 "...dddgggggdddd.",
 ".....ddddddddd..",
 ".......ddddd...."], N)
PINE = art([
 ".......dd.......",
 "......dlld......",
 ".....dllgd......",
 "....dllllgd.....",
 "...dlldllggd....",
 "....dlllggd.....",
 "...dllllgggd....",
 "..dllldllgggd...",
 ".dllllllgggggd..",
 "..ddllllggggdd..",
 ".dllllldlggggdd.",
 "dlllllllgggggggd",
 ".ddllllggggggdd.",
 "...ddddddddddd..",
 ".....ddddddd....",
 "................"], N)
BUSH = art([
 "................",
 "....ddd...dd....",
 "..ddllld.dlld...",
 ".dllllllddllgd..",
 ".dlldlllllllggd.",
 "..dllllgdllgggd.",
 "...ddgggggggdd..",
 ".....ddddddd...."], N)
FLOWERS = art([
 "................",
 "..s......s......",
 ".sls....sls..s..",
 "..s......s..sls.",
 ".....s.......s..",
 "....sls.........",
 ".....s....s.....",
 ".s.......sls....",
 "sls.......s.....",
 ".s...s..........",
 "....sls......s..",
 ".....s......sls.",
 "..s..........s..",
 ".sls.....s......",
 "..s.....sls.....",
 ".........s......"], N)

S = {".": -1, "k": K, "y": GY, "a": AC, "g": G}
def stand(cells):
    """Grandstand, 2 cells deep, seen from above: roof edge at the back, tiers of spectators, a front rail."""
    w = cells * 16; t = np.full((32, w), GY)
    t[0:2] = K; t[2:5] = GY; t[3] = AC; t[5] = K
    for row, y in enumerate(range(6, 27, 3)):               # seven tiers
        t[y:y + 2] = GY; t[y + 2] = K
        for x in range(1 + (row % 2) * 2, w - 2, 4):
            h = (x * 7 + row * 13) % 5
            t[y:y + 2, x:x + 2] = AC if h < 2 else (K if h < 4 else GY)
    t[27:29] = GY; t[28, ::2] = K; t[29:32] = K
    t[:, 0] = K; t[:, w - 1] = K
    for x in range(16, w, 16): t[6:27, x - 1:x + 1] = GY      # aisles
    return t

def pits(cells):
    """Pit building: flat roof with a stripe, garage doors facing the track below."""
    w = cells * 16; t = np.full((16, w), GY)
    t[0] = K; t[1:3] = AC; t[3] = K; t[4:7] = GY
    t[5, 2:w - 2:3] = K                                       # roof vents
    t[7] = K
    for x in range(0, w, 16):
        t[8:16, x + 2:x + 14] = K; t[8:16, x + 7:x + 9] = GY; t[8, x + 2:x + 14] = AC
    t[:, 0] = K; t[:, w - 1] = K
    return t

def board():
    """Advertising hoarding, 16x8."""
    t = np.full((8, 16), AC); t[0] = K; t[7] = K; t[:, 0] = K; t[:, 15] = K
    for x in (3, 6, 9, 12): t[2:6, x:x + 2] = K
    t[3, 3:14] = GY
    return t

def truck():
    t = np.full((16, 16), -1)
    t[2:14, 4:12] = GY; t[2, 4:12] = K; t[13, 4:12] = K; t[2:14, 4] = K; t[2:14, 11] = K
    t[3:6, 5:11] = AC; t[6, 5:11] = K; t[9:12, 6:10] = AC
    return t

W = {".": -1, "b": WA, "l": WL, "w": WW}
TENT = art([
 "................",
 ".......ww.......",
 ".....wwwwww.....",
 "...wwwwllwwww...",
 "..wwwwwllwwwww..",
 ".wwwwwwllwwwwww.",
 ".wllllllllllllw.",
 ".wwwwwwllwwwwww.",
 ".wwwwwwllwwwwww.",
 "..wwwwwllwwwww..",
 "...wwwwllwwww...",
 ".....wwwwww.....",
 "....bbbbbbbb....",
 "...bbbbbbbbbb...",
 ".....bbbbbb.....",
 "................"], W)

def lake(xs, ys, cx, cy, rx, ry):
    """-> (mask, pixels): water with a pale shoreline and repeating ripples."""
    r = ((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2
    m = r < 1; px = np.full(xs.shape, WA)
    px[(r > 0.80) & m] = WL
    rip = ((ys % 8 == 2) & ((xs + (ys // 8) * 5) % 16 < 5)) | ((ys % 8 == 6) & ((xs + (ys // 8) * 3 + 9) % 16 < 3))
    px[rip & (r < 0.72)] = WL
    px[((xs % 16 == 3) & (ys % 16 == 2)) & (r < 0.6)] = WW
    return m, px

def gravel(xs, ys, cx, cy, rx, ry):
    r = ((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2
    m = r < 1; px = np.full(xs.shape, SA)
    px[((xs + ys) % 4 == 0) & (ys % 2 == 0)] = GL
    px[(r > 0.82) & m] = GD
    return m, px
