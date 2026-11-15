#!/usr/bin/env python3
"""KITESONG's data: the songs (assets/songs.txt) for the music bank, and the
picture tables, font and text for the main bank.

usage: build_data.py SONGS OUTDIR
  writes OUTDIR/songs.inc (bank 0) and OUTDIR/tables.inc (bank 1)

Picture tables are indexed by the kernel's line counter Y, which counts down,
so entry Y is the line 119 - Y of the sky (120 counted lines: 10 bands of 12),
or 39 - Y of the hills.
"""

import math
import sys
from pathlib import Path

LANES = ["C4", "D4", "E4", "A4", "C5", "D5", "E5", "G5", "A5", "C6"]   # lane 0 lowest
CHORDS = {"C": 0, "F": 1, "Am": 2, "Bb": 3, "G": 4}
SKIES = ["dusk", "night", "gale", "dawn"]
PX_EIGHTH = 16          # the wind moves a chime 16 pixels an eighth note
SKY_LINES = 120


# ---- Songs ----
def parse_songs(text):
    songs, cur, phrase = [], None, None
    for raw in text.splitlines():
        line = raw.split("#")[0].strip()
        if not line:
            continue
        word, *rest = line.split()
        if word == "song":
            cur = {"name": " ".join(rest), "phrases": {}, "order": []}
            songs.append(cur)
        elif word == "tempo":
            cur["tempo"] = int(rest[0])
        elif word == "sky":
            cur["sky"] = SKIES.index(rest[0])
        elif word == "beat":
            cur["beat"] = int(rest[0])
        elif word == "phrase":
            phrase = cur["phrases"].setdefault(rest[0], [])
        elif word == "order":
            cur["order"] = rest
        else:
            chord, bar = line.split("|")
            toks = bar.split()
            if len(toks) != 8:
                sys.exit(f"{cur['name']}: a bar needs 8 eighths: {raw}")
            if chord.strip() not in CHORDS:
                sys.exit(f"{cur['name']}: unknown chord {chord.strip()}")
            for t in toks:
                if t not in "-." and t not in LANES:
                    sys.exit(f"{cur['name']}: {t} isn't a note the TIA plays in tune ({' '.join(LANES)})")
            phrase.append((CHORDS[chord.strip()], toks))
    return songs


def compile_song(i, s):
    bars = [b for p in s["order"] for b in s["phrases"][p]]
    chimes = sum(1 for _, toks in bars for t in toks if t in LANES)
    out = [f"SONG{i}:", f"        .byte {s['tempo']}, {s['sky']}, {s['beat']}, {chimes}",
           f"        .word SONG{i}_BARS, SONG{i}_MEL, PXT{s['tempo']}"]
    out.append(f"SONG{i}_BARS:")
    out.append("        .byte " + ", ".join(str(c) for c, _ in bars) + ", $FF")
    # Melody events: (pixels since the last event, lane); lane $FE a rest that only moves time
    # (gaps over 255 pixels), $FF the end.
    ev, last, t = [], 0, 0
    for _, toks in bars:
        for tok in toks:
            if tok in LANES:
                d = t - last
                while d > 255:
                    ev.append((240, 0xFE))
                    d -= 240
                ev.append((d, LANES.index(tok)))
                last = t
            t += PX_EIGHTH
    ev.append((max(0, min(255, t - last)), 0xFF))
    out.append(f"SONG{i}_MEL:")
    for k in range(0, len(ev), 8):
        out.append("        .byte " + ", ".join(f"{d}, ${l:02X}" for d, l in ev[k:k + 8]))
    notes = sum(1 for _, l in ev if l < 0xFE)
    return out, notes, len(bars)


# ---- Picture ----
def sky_table(stops):
    """Colours down the sky from (hue, luma) stops, evenly spread; entry Y is line 119 - Y."""
    rows = []
    for line in range(SKY_LINES):
        k = line * (len(stops) - 1) / (SKY_LINES - 1)
        hue, luma = stops[min(len(stops) - 1, round(k))]
        rows.append(hue << 4 | luma << 1)
    return rows[::-1]


SKY_STOPS = {
    "dusk": [(7, 0), (7, 1), (6, 1), (6, 2), (5, 2), (5, 3), (4, 3), (4, 4), (3, 4), (3, 5), (2, 5), (2, 6), (1, 6), (1, 7)],
    "night": [(0, 0), (8, 0), (8, 0), (8, 1), (9, 1), (8, 1), (7, 1), (7, 2), (6, 2), (6, 3)],
    "gale": [(0, 1), (0, 2), (7, 2), (7, 3), (0, 3), (6, 3), (0, 4), (5, 4), (0, 5), (4, 5)],
    "dawn": [(8, 3), (8, 4), (9, 4), (9, 5), (6, 5), (5, 5), (4, 5), (4, 6), (3, 6), (2, 6), (2, 7), (1, 7)],
}


def disc(cy, r):
    """A centred disc in PF2 with the playfield reflected: D7 is beside the centre."""
    rows = []
    for line in range(SKY_LINES):
        dy = line - cy
        b = 0
        if abs(dy) <= r:
            half = round(math.sqrt(r * r - dy * dy) / 5)   # a block is 4 pixels, a pixel ~1.3 lines
            for k in range(min(8, half)):
                b |= 0x80 >> k
        rows.append(b)
    return rows[::-1]


def pf_bits(blocks):
    """40 blocks (True lit) to PF0, PF1, PF2 for the left half and the right (not reflected)."""
    def half(bl):
        pf0 = sum(1 << (4 + k) for k in range(4) if bl[k])
        pf1 = sum(1 << (7 - k) for k in range(8) if bl[4 + k])
        pf2 = sum(1 << k for k in range(8) if bl[12 + k])
        return [pf0, pf1, pf2]
    return half(blocks[:20]) + half(blocks[20:])


def hills():
    """Two ridges, reflected (20 blocks a half); entry Y is line 39 - Y of the hills."""
    rows = {0: [], 1: [], 2: []}
    for line in range(40):
        bl = []
        for k in range(20):
            far = 4 + int(4 * math.sin(k * 0.55) + 2 * math.sin(k * 1.3))
            bl.append(line >= far)
        b = pf_bits(bl + bl[::-1])[:3]
        for j in range(3):
            rows[j].append(b[j])
    return [rows[j][::-1] for j in range(3)]


FONT = {
    "A": "010101111101101", "B": "110101110101110", "C": "011100100100011", "D": "110101101101110",
    "E": "111100110100111", "F": "111100110100100", "G": "011100101101011", "H": "101101111101101",
    "I": "111010010010111", "K": "101101110101101", "L": "100100100100111", "M": "101111111101101",
    "N": "110101101101101", "O": "010101101101010", "P": "110101110100100", "R": "110101110101101",
    "S": "011100010001110", "T": "111010010010010", "U": "101101101101111", "W": "101101111111101",
    "Y": "101101010010010", "!": "010010010000010", " ": "000000000000000",
    "0": "111101101101111", "1": "010110010010111", "2": "111001111100111", "3": "111001111001111",
    "4": "101101111001001", "5": "111100111001111", "6": "111100111101111", "7": "111001001001001",
    "8": "111101111101111", "9": "111101111001111",
}


def text_rows(s):
    """5 rows of 6 bytes: the string centred in 40 playfield blocks, 3 blocks a letter."""
    width = 4 * len(s) - 1
    if width > 40:
        sys.exit(f"text too long: {s}")
    x0 = (40 - width) // 2
    out = []
    for r in range(5):
        bl = [False] * 40
        for i, ch in enumerate(s):
            for c in range(3):
                if FONT[ch][3 * r + c] == "1":
                    bl[x0 + 4 * i + c] = True
        out += pf_bits(bl)
    return out


def digit8(ch):
    """A digit for a player: the 3x5 glyph two pixels a column, 5 rows."""
    rows = []
    for r in range(5):
        b = 0
        for c in range(3):
            if FONT[ch][3 * r + c] == "1":
                b |= 0b11 << (6 - 2 * c)
        rows.append(b)
    return rows


KITE = [0x18, 0x3C, 0x7E, 0xFF, 0x7E, 0x3C, 0x18, 0x08, 0x10, 0x08]   # top row first
CHIME = [0x18, 0x3C, 0x3C, 0x3C, 0x3C, 0x7E, 0x18, 0x00]               # band lines 2-9


def byte_lines(label, data, per=16):
    out = [f"{label}:"]
    for k in range(0, len(data), per):
        out.append("        .byte " + ", ".join(f"${b:02X}" for b in data[k:k + per]))
    return out


def main():
    songs = parse_songs(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)

    # Bank 0: the songs.
    s0 = ["; Generated by tools/build_data.py from assets/songs.txt; don't edit.",
          f"NSONGS = {len(songs)}"]
    tempos = sorted({s["tempo"] for s in songs})
    for t in tempos:   # pixels the wind has moved this many frames into an eighth
        s0 += byte_lines(f"PXT{t}", [k * PX_EIGHTH // t for k in range(t)])
    s0.append("SONGS:")
    s0.append("        .word " + ", ".join(f"SONG{i}" for i in range(len(songs))))
    for i, s in enumerate(songs):
        lines, notes, nbars = compile_song(i, s)
        s0 += lines
        print(f"{s['name']}: {notes} chimes, {nbars} bars, {nbars * 8 * s['tempo'] / 60:.0f} s")
    (out / "songs.inc").write_text("\n".join(s0) + "\n")

    # Bank 1: the picture, the font and the text.
    s1 = ["; Generated by tools/build_data.py; don't edit."]
    s1.append("        .align 256")
    chime = [0] * SKY_LINES
    for line in range(SKY_LINES):
        row = line % 12
        if 2 <= row < 10:
            chime[line] = CHIME[row - 2]
    s1 += byte_lines("CHIME", chime[::-1])
    s1 += byte_lines("ZERO", [0] * SKY_LINES)
    for name in SKIES:

        s1 += byte_lines(f"SKY_{name.upper()}", sky_table(SKY_STOPS[name]))
    s1 += byte_lines("SUN_BIG", disc(92, 18))
    s1 += byte_lines("SUN_MOON", disc(30, 12))
    s1 += byte_lines("SUN_NONE", [0] * SKY_LINES)
    h0, h1, h2 = hills()
    s1 += byte_lines("HILL0", h0) + byte_lines("HILL1", h1) + byte_lines("HILL2", h2)
    s1 += byte_lines("KITE_GFX", KITE[::-1])
    s1 += byte_lines("DIGITS", [b for d in "0123456789" for b in digit8(d)])
    # Text: six tables, one a playfield register (left PF0 PF1 PF2, right PF0 PF1 PF2), five
    # rows a string; string k's rows at 5k. TX_<NAME> is that offset.
    texts = [("TITLE", "KITESONG"), ("CLEAR", "CLEAR!"), ("AGAIN", "TRY AGAIN"),
             ("PERFECT", "PERFECT!"), ("BLANK", " ")]
    texts += [(f"NAME{i}", s["name"]) for i, s in enumerate(songs)]
    rows = [text_rows(v) for _, v in texts]
    for k, (name, _) in enumerate(texts):
        s1.append(f"TX_{name} = {5 * k}")
    for reg in range(6):
        s1 += byte_lines(f"TXT{reg}", [r[6 * row + reg] for r in rows for row in range(5)])
    (out / "tables.inc").write_text("\n".join(s1) + "\n")


if __name__ == "__main__":
    main()
