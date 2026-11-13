#!/usr/bin/env python3
"""The circuit on screen must match the tools' reference picture pixel for pixel.
This is what proves the banded tile switching lands on the right scanlines."""
from common import *
from PIL import Image

e = Emu(ROM); e.frame(0, 30)
def bg_frame():
    e.ram[SYM["ppumask_s"]] = 0x0E          # background only: cars are sprites
    e.frame(0); e.frame(0)
for n, t in enumerate(TRACKS):
    ref = np.array(Image.open(os.path.join(ROOT, "build", f"ref_{n}.png")).convert("RGB"))
    bg_frame(); shot = e.frame_img.copy()
    bad = [y + 32 for y in same_picture(shot[32:, :], ref[32:, :])]
    check(f"circuit {n} {t['name']} matches its reference", not bad, f"bad rows {bad[:12]}" if bad else f"bands at {t['bands']}")
    stable = all((bg_frame() or True) and not same_picture(e.frame_img[32:], shot[32:]) for _ in range(5))
    check(f"circuit {n} picture is stable frame to frame", stable)
if __name__ == "__main__": finish()
