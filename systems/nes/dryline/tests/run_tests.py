#!/usr/bin/env python3
"""Runs every test_*.py in this folder."""
import glob, os, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__)); bad = 0
for t in sorted(glob.glob(os.path.join(here, "test_*.py"))):
    print(f"== {os.path.basename(t)}"); bad += subprocess.call([sys.executable, t]) != 0
sys.exit(1 if bad else 0)
