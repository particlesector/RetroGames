#!/usr/bin/env python3
"""Quick look: boot the ROM, press through to a room, save screenshots."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "shared", "tools"))
from nes_emu import *
out = sys.argv[1]
e = Emu("build/tidebell.nes")
e.frame(0, 60); e.screenshot(2).save(f"{out}/t_title.png")
e.frame(START, 2); e.frame(0, 30); e.screenshot(2).save(f"{out}/t_card.png")
e.frame(START, 2); e.frame(0, 30); e.screenshot(2).save(f"{out}/t_room.png")
