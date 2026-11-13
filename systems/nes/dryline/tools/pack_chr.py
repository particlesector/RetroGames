#!/usr/bin/env python3
"""Assembles build/dryline.chr (128 KB): pages 0-3 menu art, 4-7 sprites, 8+ circuits."""
import sys, os
b = sys.argv[1]
def load(name, size):
    p = os.path.join(b, name)
    d = open(p, "rb").read() if os.path.exists(p) else b""
    assert len(d) <= size, f"{name} is {len(d)} bytes, limit {size}"
    return d + bytes(size - len(d))
out = load("menu.chr", 4096) + load("sprites.chr", 4096) + load("tracks.chr", 120 * 1024)
open(os.path.join(b, "dryline.chr"), "wb").write(out)
