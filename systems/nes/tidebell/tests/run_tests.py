#!/usr/bin/env python3
"""Replays the `solve:` line of every room in assets/levels.txt through the emulator.

Solve commands:  W<x> walk to px   J/JL/JR[@x] jump (stop steering at x)   T+ T- ring the bell
                 S<x>,<y> swim to (use _ to leave an axis alone)   Z<n> wait   G wait to land
                 K<n> wait for tide level n (storm rooms)   ?c=n ?b=n check carried/banked   C room clears
Usage: run_tests.py [room ...] [--shots DIR] [--gif DIR] [-v]
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bot import *

def load():
    rooms = []
    for line in open(os.path.join(ROOT, "assets", "levels.txt")):
        if line.startswith("room"): rooms.append([re.search(r'"([^"]*)"', line).group(1), None])
        elif line.startswith("solve:") and rooms: rooms[-1][1] = (rooms[-1][1] or "") + " " + line[6:].strip()
        elif line.startswith("scene"): break
    return rooms

def run(b, script, verbose=False):
    for tok in script.split():
        if verbose: print(f"    {tok:10s} from {b.pos()}")
        c, a = tok[0], tok[1:]
        if c == "W": b.walk(int(a))
        elif c == "J":
            d = {"L": LEFT, "R": RIGHT}.get(a[:1], 0); a = a.lstrip("LR")
            b.jump(d, x=int(a[1:]) if a.startswith("@") else None)
        elif c == "T": b.tide(+1 if a == "+" else -1)
        elif c == "S":
            x, y = a.split(","); b.swim(None if x == "_" else int(x), None if y == "_" else int(y))
        elif c == "Z": b.wait(int(a))
        elif c == "G": b.settle()
        elif c == "K":
            for _ in range(1200):
                if b.v("tide_level") == int(a) and b.v("water_y") == b.v("tide_y", int(a)): break
                b.step()
            else: raise Fail("tide level never came")
        elif c == "?":
            k, n = a.split("="); got = b.v({"c": "carried", "b": "banked"}[k])
            if got != int(n): raise Fail(f"expected {k}={n}, got {got} at {b.pos()}")
        elif c == "C": b.cleared()
        else: raise Fail(f"bad command {tok}")

def main():
    args = sys.argv[1:]; verbose = "-v" in args
    shots = args[args.index("--shots") + 1] if "--shots" in args else None
    gif = args[args.index("--gif") + 1] if "--gif" in args else None
    want = [int(a) for a in args if a.isdigit()]
    rooms, bad = load(), 0
    for i, (name, script) in enumerate(rooms):
        if want and i not in want: continue
        tag = f"{i // 8 + 1}-{i % 8 + 1} {name}"
        try:
            rec = [] if gif else None
            b = Bot(i, record=rec)
            if shots: b.e.frame(0, 10); b.e.screenshot(2).save(f"{shots}/room{i:02d}.png")
            if not script: raise Fail("no solve: line")
            if not script.split()[-1] == "C": raise Fail("solve: must end with C")
            f0 = b.e.frames; run(b, script, verbose)
            print(f"ok    {tag}  ({(b.e.frames - f0) / 60:.0f}s)")
            if gif: rec[0].save(f"{gif}/room{i:02d}.gif", save_all=True, append_images=rec[1::2], duration=66, loop=0)
        except Fail as ex:
            bad += 1; print(f"FAIL  {tag}: {ex}")
            if shots: b.e.screenshot(2).save(f"{shots}/fail{i:02d}.png")
    print(f"{len(rooms)} rooms, {bad} failed" if not want else f"{bad} failed")
    sys.exit(1 if bad else 0)

if __name__ == "__main__": main()
