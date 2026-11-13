"""Shared test helpers for DRYLINE."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "..", "..", "..", "shared", "tools"))
from nes_emu import Emu, labels, A, B, SELECT, START, UP, DOWN, LEFT, RIGHT
import numpy as np

ROM = os.path.join(ROOT, "build", "dryline.nes")
SYM = labels(os.path.join(ROOT, "build", "labels.txt"))
TRACKS = json.load(open(os.path.join(ROOT, "build", "tracks.json")))

results = []
def check(name, ok, detail=""):
    results.append(bool(ok)); print(("ok    " if ok else "FAIL  ") + name + (f"  ({detail})" if detail else ""))
def finish():
    print(f"{len(results)} checks, {results.count(False)} failed"); sys.exit(1 if False in results else 0)

def same_picture(a, b):
    """Rows where two images differ once colours are matched one-to-one (the emulator's palette is not ours)."""
    fwd, back, bad = {}, {}, []
    for y in range(a.shape[0]):
        ok = True
        for pa, pb in set(zip(map(tuple, a[y]), map(tuple, b[y]))):
            if fwd.setdefault(pa, pb) != pb or back.setdefault(pb, pa) != pa: ok = False
        if not ok: bad.append(y)
    return bad
