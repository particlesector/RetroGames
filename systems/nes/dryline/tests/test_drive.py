#!/usr/bin/env python3
"""Car physics: acceleration, top speed, steering, surfaces and walls."""
from common import *
import math

def v(e, name, i=0): return int(e.ram[SYM[name] + i])
def pos(e, i=0): return v(e, "c_xh", i) + v(e, "c_xl", i) / 256, v(e, "c_yh", i) + v(e, "c_yl", i) / 256

t = TRACKS[0]
e = boot(solo=True)
e = boot(lights=True)
check("cars start on their grid slots", [[v(e, "c_xh", i), v(e, "c_yh", i)] for i in range(4)] == t["grid"])
e = boot(solo=True); x0, y0 = pos(e); e.frame(A, 60); x1, y1 = pos(e)
hd = v(e, "c_ang") * 2 * math.pi / 256
along = (x1 - x0) * math.cos(hd) + (y1 - y0) * math.sin(hd); side = -(x1 - x0) * math.sin(hd) + (y1 - y0) * math.cos(hd)
check("throttle drives the car straight ahead", along > 40 and abs(side) < 1.5, f"{along:.1f} px forward, {side:.1f} sideways in 1 s")
e = boot(solo=True); e.ram[SYM["c_spd"]] = 160; e.frame(A, 18)
xa, ya = pos(e); e.frame(A); xb, yb = pos(e); top = math.hypot(xb - xa, yb - ya)
check("top speed on tarmac is 2.5 px per frame", abs(top - 2.5) < 0.06 and v(e, "c_spd") == 160, f"{top:.2f}")
e = boot(solo=True); n = 0
while v(e, "c_spd") < 96 and n < 400: e.frame(A); n += 1
check("0 to 1.5 px per frame takes about half a second", n <= 34, f"{n} frames")
e = boot(solo=True); e.frame(A, 40); a0 = v(e, "c_ang"); e.frame(A | RIGHT, 10)
check("steering right turns the heading clockwise", (v(e, "c_ang") - a0) & 255 == 30)
e = boot(solo=True); e.frame(A, 40); e.frame(B, 40)
xa, ya = pos(e); e.frame(0, 10); xb, yb = pos(e)
check("brakes bring the car to rest", math.hypot(xb - xa, yb - ya) < 0.05 and v(e, "c_spd") == 0)
# put the car on the infield grass: the surface is recognised and caps the speed
e = boot(solo=True); e.ram[SYM["c_xh"]] = 216; e.ram[SYM["c_yh"]] = 150; e.ram[SYM["c_spd"]] = 150
e.frame(A, 3); on_grass = v(e, "c_surf") == 1; e.frame(A, 30)
check("grass is recognised under the car", on_grass)
check("grass limits speed to 80", v(e, "c_spd") <= 80, f"speed {v(e, 'c_spd')}")
# nothing escapes the screen or enters the HUD, whatever the controls
import random
rnd = random.Random(1); e = boot(solo=True); ok = True
for f in range(3000):
    if f % 20 == 0: p = A | rnd.choice([0, LEFT, RIGHT, LEFT, RIGHT, B])
    e.frame(p)
    x, y = v(e, "c_xh"), v(e, "c_yh")
    if not (8 <= x <= 247 and 40 <= y <= 238): ok = False
check("a randomly driven car stays inside the playfield", ok)
if __name__ == "__main__": finish()
