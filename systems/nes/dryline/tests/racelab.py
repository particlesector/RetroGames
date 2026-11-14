#!/usr/bin/env python3
"""Development tool: run an all-AI race and print lap times. Usage: racelab.py [seconds] [shot.png]"""
from common import *
def v(e, n, i=0): return int(e.ram[SYM[n] + i])
secs = int(sys.argv[1]) if len(sys.argv) > 1 else 70
e = Emu(ROM); e.frame(0, 10); e.ram[SYM["demo"]] = 1
laps = [[] for _ in range(4)]; last = [0] * 4; off = [0] * 4; hits = 0; top = [0] * 4; pits = [[] for _ in range(4)]; wx = []
for f in range(60 * secs):
    e.frame(0)
    for i in range(4):
        l = v(e, "c_lap", i)
        if l != last[i]: laps[i].append(f); last[i] = l
        if v(e, "c_surf", i): off[i] += 1
        top[i] = max(top[i], v(e, "c_spd", i))
        if v(e, "c_serv", i) == 149: pits[i].append((round(f / 60), v(e, "c_want", i)))
    if not wx or wx[-1][1] != v(e, "weather"): wx.append((round(f / 60), v(e, "weather")))
    if len(sys.argv) > 3 and f == int(sys.argv[3]) * 60: e.screenshot(3).save(sys.argv[2])
for i in range(4):
    print(f"car {i}: laps {[round((b - a) / 60, 2) for a, b in zip(laps[i], laps[i][1:])]} finished {v(e, 'c_fin', i)} "
          f"off-road frames {off[i]} top {top[i]} pits {pits[i]} wear {v(e, 'c_wear', i)}")
print("weather changes (s, state):", wx)
if len(sys.argv) == 3: e.screenshot(3).save(sys.argv[2])
