#!/usr/bin/env python3
"""Game-flow checks: menus, passwords, pause, death, retry, storm cycle, ending, raster split, audio."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bot import *
import numpy as np

S_TITLE, S_PASS, S_CARD, S_PLAY, S_END = range(5)
results = []
def check(name, ok, detail=""):
    results.append(ok); print(("ok    " if ok else "FAIL  ") + name + (f"  ({detail})" if detail else ""))

def tap(e, pad, n=1):
    for _ in range(n): e.frame(pad, 2); e.frame(0, 3)

def v(e, name, i=0): return int(e.ram[SYM[name] + i])

# --- title menu and password entry -------------------------------------------------
e = Emu(ROM); e.frame(0, 40)
check("boots to title", v(e, "state") == S_TITLE)
tap(e, DOWN); check("menu cursor moves", v(e, "menu_sel") == 1)
tap(e, START); e.frame(0, 20); check("password screen opens", v(e, "state") == S_PASS)
tap(e, START); e.frame(0, 10); check("wrong code is refused", v(e, "state") == S_PASS)
codes = [l.split() for l in open(os.path.join(ROOT, "build", "passwords.txt"))]
room_id, code = codes[18]
for i, ch in enumerate(code):
    tap(e, UP, ord(ch) - 65); tap(e, RIGHT)
tap(e, START); e.frame(0, 20)
check(f"code {code} opens island card", v(e, "state") == S_CARD and v(e, "room") == 18)
tap(e, A); e.frame(0, 20); check(f"card leads to room {room_id}", v(e, "state") == S_PLAY and v(e, "room") == 18)
e.frame(0, 320); check("card times out on its own", True)

# --- pause, retry, death -----------------------------------------------------------
b = Bot(8)                                   # 2-1: crab awake on the sea bed
tap(b.e, START); f = b.v("frame_count"); x = b.v("o_x"); b.e.frame(0, 30)
check("pause freezes the room", b.v("paused") == 1 and b.v("o_x") == x)
tap(b.e, START); b.e.frame(0, 30); check("unpause resumes", b.v("paused") == 0 and b.v("o_x") != x)
died = False
for _ in range(400):
    b.e.frame(RIGHT)
    if b.v("pstate") == 1: died = True; break
check("an awake crab kills Pim", died)
b.e.frame(0, 80); check("room restarts after death", b.v("pstate") == 0 and b.v("px") == 32 and b.v("state") == S_PLAY)
b.e.frame(RIGHT, 20); tap(b.e, SELECT); b.e.frame(0, 20); check("SELECT restarts the room", b.v("px") == 32)

# --- ember goes out in water -------------------------------------------------------
b = Bot(1); b.tide(-1); b.walk(178); b.jump(RIGHT); b.walk(218)
c1 = b.v("carried"); b.tide(+1); b.walk(150); b.e.frame(0, 30)
check("carried ember is lost when Pim gets wet", c1 == 1 and b.v("carried") == 0 and b.v("e_state") == 0)

# --- storm cycles by itself and ignores the bell -----------------------------------
b = Bot(24); seen = []
for _ in range(900):
    b.e.frame(B if b.e.frames % 20 == 0 else 0)
    if not seen or seen[-1] != b.v("tide_level"): seen.append(b.v("tide_level"))
check("storm tide cycles 0-1-2-1-0", seen[:5] == [0, 1, 2, 1, 0], str(seen))

# --- raster split: no scanline may be half sky, half water ---------------------------
b = Bot(2); torn = 0; offs = set()
for step in range(140):
    b.e.frame(B if step in (5, 70) else 0)
    img = b.e.frame_img; wl = b.v("water_y"); sky = img[60, 100]
    first = None
    for y in range(120, 207):
        is_sky = (img[y, 84:140] == sky).all(axis=1)
        n = int(is_sky.sum())
        if 20 <= n <= len(is_sky) - 20: torn += 1      # (water has a few sky-coloured specks)
        if first is None and n < 8: first = y
    if first is not None: offs.add(first - wl)
check("waterline has no torn scanlines while the tide moves", torn == 0, f"{torn} torn rows")
check("waterline follows water_y", min(offs) >= 0 and max(offs) <= 2, f"offsets {sorted(offs)}")

# --- last room leads to the ending -------------------------------------------------
from run_tests import load, run
rooms = load(); b = Bot(len(rooms) - 1); run(b, rooms[-1][1]); b.e.frame(0, 160)
check("clearing the last room shows the ending", b.v("state") == S_END)
tap(b.e, START); b.e.frame(0, 30); check("ending returns to title", b.v("state") == S_TITLE)
b = Bot(7); run(b, rooms[7][1]); b.e.frame(0, 160)
check("island 1 clear leads to the island 2 card", b.v("state") == S_CARD and b.v("room") == 8)

# --- audio: the first bar of the title theme, note by note ----------------------------
e = Emu(ROM); e.record_audio = True; e.frame(0, 300)
a = np.concatenate(e.audio).astype(np.float64)[::2]
rate = len(a) / (300 / 60.0988); tick = 9 / 60.0988
def loudest(t0, t1, lo, hi):
    seg = a[int(rate * t0):int(rate * t1)]; seg = seg - seg.mean()
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))); fr = np.fft.rfftfreq(len(seg), 1 / rate)
    m = (fr >= lo) & (fr <= hi); return fr[m][np.argmax(sp[m])]
check("title music produces sound", np.abs(a - a.mean()).max() > 500)
melody = [(0, 4, 587.3), (4, 2, 493.9), (6, 2, 587.3), (8, 4, 784.0), (12, 2, 587.3), (14, 2, 493.9), (16, 4, 659.3)]
got = [loudest(s0 * tick + 0.02, (s0 + n) * tick, 400, 1000) for s0, n, _ in melody]
check("title melody is in tune (D5 B4 D5 G5 D5 B4 E5)", all(abs(g - f) < f * 0.02 for g, (_, _, f) in zip(got, melody)),
      " ".join(f"{g:.0f}" for g in got))
bass = loudest(0.02, 8 * tick, 60, 150)
check("triangle bass plays G2", abs(bass - 98.0) < 3, f"{bass:.0f} Hz")

print(f"{len(results)} checks, {results.count(False)} failed")
sys.exit(1 if False in results else 0)
