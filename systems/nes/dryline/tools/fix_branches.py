#!/usr/bin/env python3
"""Development helper: rewrites out-of-range conditional branches as a short
inverse branch over a jmp. Usage: fix_branches.py <ca65 command...>"""
import re, subprocess, sys
INV = {"beq": "bne", "bne": "beq", "bcc": "bcs", "bcs": "bcc", "bmi": "bpl", "bpl": "bmi", "bvc": "bvs", "bvs": "bvc"}
n = 0
for _ in range(60):
    r = subprocess.run(sys.argv[1:], capture_output=True, text=True)
    errs = re.findall(r"^(\S+)\((\d+)\): Error: Range error", r.stderr, re.M)
    if not errs: break
    for path, line in sorted(set(errs), key=lambda e: -int(e[1])):
        L = open(path).read().split("\n"); i = int(line) - 1
        m = re.match(r"^(\S*\s+)(b\w\w)\s+(\S+)(.*)$", L[i])
        assert m and m.group(2) in INV, L[i]
        n += 1; lab = f"@far{n}_{i}"
        L[i:i + 1] = [f"{m.group(1)}{INV[m.group(2)]} {lab}{m.group(4)}", f"    jmp {m.group(3)}", f"{lab}:"]
        open(path, "w").write("\n".join(L))
print(r.stderr.strip() or f"branches fixed: {n}")
