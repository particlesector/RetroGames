#!/usr/bin/env python3
"""Race logic, proven by letting the rivals' AI drive every car."""
from common import *
def v(e, n, i=0): return int(e.ram[SYM[n] + i])

for n, t in enumerate(TRACKS):
    e = Emu(ROM); e.frame(0, 10); e.ram[SYM["cur_track"]] = n; e.ram[SYM["demo"]] = 1
    laps = [[] for _ in range(4)]; last = [0] * 4; off = 0; badpos = 0; lights = 0
    for f in range(60 * 90):
        e.frame(0)
        if v(e, "race_state") == 0: lights = f
        for i in range(4):
            l = v(e, "c_lap", i)
            if l != last[i]: laps[i].append(f); last[i] = l
            off += v(e, "c_surf", i) != 0
        if sorted(v(e, "c_pos", i) for i in range(4)) != [1, 2, 3, 4]: badpos += 1
        if all(v(e, "c_fin", i) for i in range(4)): break
    name = f"circuit {n} {t['name']}"
    times = [(b - a) / 60 for l in laps for a, b in zip(l, l[1:])]
    check(f"{name}: the lights hold the grid for about 3 seconds", 170 < lights < 215, f"{lights} frames")
    check(f"{name}: all four cars finish the race", all(v(e, "c_fin", i) for i in range(4)), f"{f / 60:.0f} s")
    check(f"{name}: finishing order is 1 to 4", sorted(v(e, "c_fin", i) for i in range(4)) == [1, 2, 3, 4])
    check(f"{name}: rivals stay on the tarmac in the dry", off < 30, f"{off} off-road frames")
    check(f"{name}: positions are always a clean 1-2-3-4", badpos == 0)
    check(f"{name}: lap times are sane and consistent", times and 5 < min(times) and max(times) < 14, f"{min(times):.2f} to {max(times):.2f} s")
    check(f"{name}: the player's finish ends the race", v(e, "race_state") == 2)

# a parked player does not stop the race, and is last
e = Emu(ROM); e.frame(0, 10)
for f in range(60 * 30): e.frame(0)
check("a player who never moves is classified last", v(e, "c_pos") == 4)
check("rivals lap a parked player without getting stuck", all(v(e, "c_lap", i) >= 3 for i in (1, 2, 3)), str([v(e, "c_lap", i) for i in range(4)]))
# shuttling back and forth over the line earns nothing
e = boot()
for i in (1, 2, 3): e.ram[SYM["c_yh"] + i] = 60          # move the rivals out of the way
e.frame(A, 45); first = val(e, "c_lap")
for _ in range(3):
    e.ram[SYM["c_ang"]] = (val(e, "c_ang") + 128) & 255; e.ram[SYM["c_spd"]] = 0; e.frame(A, 45)
check("crossing the line again and again counts one lap, not four", first == 1 and val(e, "c_lap") == 1, f"lap {val(e, 'c_lap')}")
if __name__ == "__main__": finish()
