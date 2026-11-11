"""Closed-loop test bot: drives TIDEBELL through the emulator and reads game RAM."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "..", "..", "..", "shared", "tools"))
from nes_emu import Emu, labels, A, B, SELECT, START, UP, DOWN, LEFT, RIGHT

ROM = os.path.join(ROOT, "build", "tidebell.nes")
SYM = labels(os.path.join(ROOT, "build", "labels.txt"))
S_PLAY = 3

class Fail(Exception): pass

class Bot:
    def __init__(self, room=0, record=None):
        self.e = Emu(ROM); self.record = record; self.done = False
        self.e.frame(0, 40)
        self.e.frame(START, 2); self.e.frame(0, 20)       # title -> island card
        self.e.ram[SYM["room"]] = room
        self.e.frame(START, 2); self.e.frame(0, 20)       # card -> room
        if self.v("state") != S_PLAY or self.v("room") != room: raise Fail("room did not start")
        self.room = room

    def v(self, name, i=0): return int(self.e.ram[SYM[name] + i])
    @property
    def x(self): return self.v("px")
    @property
    def y(self): return self.v("py")
    def ground(self): return self.v("pground") == 1
    def wet(self): return self.v("pwet") == 1
    def pos(self): return (self.x, self.y, "wet" if self.wet() else ("gnd" if self.ground() else "air"), self.v("water_y"))

    def step(self, pad=0, n=1):
        for _ in range(n):
            self.e.frame(pad)
            if self.record is not None and self.e.frames % 2 == 0: self.record.append(self.e.screenshot())
            if self.v("pstate") == 1: raise Fail(f"Pim died at {self.pos()}")
            if self.v("pstate") == 2: self.done = True

    def wait(self, n): self.step(0, n)
    def settle(self, limit=120):
        for _ in range(limit):
            if self.done or self.ground() or self.wet(): return
            self.step()
        raise Fail(f"never landed {self.pos()}")

    def tide(self, d):
        """Ring the bell: d=+1 raises the tide a step, d=-1 lowers it; waits for the water."""
        lvl = self.v("tide_level")
        self.step(B | (DOWN if d < 0 else 0)); self.step(DOWN if d < 0 else 0)
        if self.v("tide_level") != lvl + d: raise Fail(f"bell refused (level {lvl}, d={d}) {self.pos()}")
        for _ in range(300):
            if self.v("water_y") == self.v("tide_y", self.v("tide_level")): self.step(0, 2); return
            self.step()
        raise Fail("tide never settled")

    def walk(self, x, limit=400):
        """Walk/swim sideways until px reaches x."""
        d = RIGHT if x > self.x else LEFT
        for _ in range(limit):
            if self.done or (d == RIGHT and self.x >= x) or (d == LEFT and self.x <= x): return
            self.step(d)
        raise Fail(f"walk to {x} stuck at {self.pos()}")

    def jump(self, d=0, hold=30, x=None):
        """Jump (or hop out of water) holding direction d; optionally stop steering at px x."""
        if not (self.ground() or self.wet()): raise Fail(f"jump with nothing underfoot {self.pos()}")
        was_wet = self.wet()
        self.step(0)                      # release A so the press registers
        self.step(A | d)
        for i in range(200):
            steer = d
            if x is not None and ((d == RIGHT and self.x >= x) or (d == LEFT and self.x <= x)): steer = 0
            self.step(steer | (A if i < hold else 0))
            if self.done or self.ground() or (self.wet() and not was_wet) or (self.wet() and i > 30): return
        raise Fail(f"jump never ended {self.pos()}")

    def swim(self, x=None, y=None, limit=500):
        for _ in range(limit):
            pad = 0
            if x is not None and abs(self.x - x) > 1: pad |= RIGHT if x > self.x else LEFT
            if y is not None and abs(self.y - y) > 1: pad |= DOWN if y > self.y else UP
            if pad == 0: return
            self.step(pad)
        raise Fail(f"swim to {x},{y} stuck at {self.pos()}")

    def cleared(self, limit=200):
        for _ in range(limit):
            if self.done or self.v("pstate") == 2: return True
            self.e.frame(0)
        raise Fail(f"room not cleared: carried={self.v('carried')} banked={self.v('banked')}/{self.v('e_count')} {self.pos()}")
