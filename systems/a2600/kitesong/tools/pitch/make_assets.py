#!/usr/bin/env python3
"""KITESONG pitch assets: mockups drawn under the Atari 2600's TIA rules, and
the theme rendered from the TIA's own sound dividers.

usage: make_assets.py [OUTDIR]   (default: docs/pitch next to this game)

Pictures are 160 x 192 TIA pixels, one colour value ({hue, luma}) per pixel,
built line by line from what the TIA has on a line: a background colour, a
40-bit playfield in one colour, two 8-pixel players and their missiles, and
the ball. They're scaled 4 x 2 so pixels have a TV's shape. The colours come
from a simple NTSC model below (16 hues, 8 lumas), not from an emulator.

The theme is rendered sample by sample from the TIA's audio clock (the colour
clock / 114) and the dividers of the waveforms used: AUDC 4 (pure tone, /2)
for the melody, AUDC 1 (4-bit poly, /15) for the bass and AUDC 8 (9-bit poly)
for the drums, on two channels as the TIA has. Notes change once a frame, as
a 2600 driver changes them in its vertical blank.
"""

import math
import struct
import sys
import wave
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[1] / "docs" / "pitch"
W, H = 160, 192


# ---- Colours: an NTSC TIA, roughly as a TV shows it ----
def tia_rgb(c):
    hue, luma = c >> 4, (c >> 1) & 7
    y = 0.04 + 0.88 * luma / 7
    u = v = 0.0
    if hue:  # hue 1 in phase with the colour burst (-U), each next one 1/14 turn on
        ang = math.radians(180 - (hue - 1) * 360 / 14)
        u, v = 0.2 * math.cos(ang), 0.2 * math.sin(ang)
    r = y + 1.140 * v
    g = y - 0.395 * u - 0.581 * v
    b = y + 2.032 * u
    return tuple(int(255 * max(0.0, min(1.0, v)) ** 0.62) for v in (r, g, b))


# ---- A frame, line by line ----
class Line:
    def __init__(self, bk):
        self.bk = bk
        self.pf = [0] * 40      # playfield bits, 4 pixels each
        self.pf_col = 0
        self.objs = []          # (x, bits or width, colour); drawn over the playfield

    def player(self, x, bits, col):
        assert bits < 256
        self.objs.append((x, [(bits >> (7 - k)) & 1 for k in range(8)], col))

    def dot(self, x, w, col):   # a missile or the ball: 1, 2, 4 or 8 pixels
        assert w in (1, 2, 4, 8)
        self.objs.append((x, [1] * w, col))

    def pixels(self):
        row = [self.bk] * W
        for k in range(40):
            if self.pf[k]:
                for p in range(4):
                    row[4 * k + p] = self.pf_col
        for x, bits, col in self.objs:
            for k, b in enumerate(bits):
                if b:
                    row[(x + k) % W] = col
        return row


def render(lines, name):
    data = bytearray()
    for ln in lines:
        row = b"".join(bytes(tia_rgb(c)) * 4 for c in ln.pixels())
        data += row * 2
    Image.frombytes("RGB", (W * 4, H * 2), bytes(data)).save(OUT / name)


# Sky: hue and luma by line, deep violet at the top to gold at the horizon.
SKY = [(0x70, 0), (0x70, 1), (0x60, 1), (0x60, 2), (0x50, 2), (0x50, 3), (0x40, 3), (0x40, 4),
       (0x30, 4), (0x30, 5), (0x20, 5), (0x20, 6), (0x10, 6), (0x10, 7), (0x00, 7)]
HORIZON = 150


def sky_line(y):
    band = min(len(SKY) - 1, y * len(SKY) // HORIZON)
    hue, luma = SKY[band]
    return Line(hue | (luma << 1))


def hills(ln, y, scroll=0):
    """Two ranges of hills below the horizon, in the playfield (4-pixel blocks)."""
    for k in range(40):
        x = (k + scroll) % 40
        far = HORIZON - 6 + int(5 * math.sin(x * 0.45) + 3 * math.sin(x * 0.9))
        near = HORIZON + 10 + int(6 * math.sin(x * 0.3 + 2) + 2 * math.sin(x * 1.3))
        if y >= far:
            ln.pf[k] = 1
        ln.pf_col = 0x62 if y < near else 0x00
        if y >= near:
            ln.pf[k] = 1


def sun(ln, y, cx=26, cy=112, r=20):
    """A playfield disc: a block is 4 pixels, a pixel twice a line's height on a TV."""
    if not any(ln.pf) and abs(y - cy) <= r:
        half = int(round(math.sqrt(r * r - (y - cy) ** 2) / 8))
        for k in range(cx - half, cx + half + 1):
            ln.pf[k] = 1
        ln.pf_col = 0x2E if y < cy else 0x1C


KITE = [0x18, 0x3C, 0x7E, 0xFF, 0xFF, 0x7E, 0x3C, 0x18, 0x10, 0x08, 0x10, 0x08]
CHIME = [0x18, 0x3C, 0x3C, 0x3C, 0x7E, 0x18]

# 5x7 capitals, for the title's 48-pixel line of six player copies (8 letters of 6 pixels).
FONT = {
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
}
DIGITS = {
    "0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"], "3": ["111", "001", "111", "001", "111"],
    "4": ["101", "101", "111", "001", "001"], "8": ["111", "101", "111", "101", "111"],
    "/": ["001", "001", "010", "100", "100"],
}


def text48(lines, y0, text, col):
    """Eight 6-pixel letters as six 8-pixel player copies (the 48-pixel trick)."""
    bits = "".join("".join(FONT[ch][r] + "0" for ch in text) for r in range(7))
    for r in range(7):
        row = "".join(FONT[ch][r] + "0" for ch in text)
        for c in range(6):
            b = int(row[8 * c:8 * c + 8], 2)
            for dy in range(2):
                lines[y0 + 2 * r + dy].player(56 + 8 * c, b, col)
    return bits


def score(lines, y0, text, col):
    """Score digits in the playfield's left half, 3 blocks a digit."""
    for r in range(5):
        for dy in range(2):
            ln = lines[y0 + 2 * r + dy]
            ln.pf_col = col
            for i, ch in enumerate(text):
                for k, b in enumerate(DIGITS[ch][r]):
                    ln.pf[1 + 4 * i + k] = b == "1"


def title():
    lines = [sky_line(y) for y in range(H)]
    for y, ln in enumerate(lines):
        hills(ln, y)
        if y < HORIZON - 6:
            sun(ln, y)
    text48(lines, 40, "KITESONG", 0x0E)
    for k, b in enumerate(KITE):
        lines[78 + k].player(110, b, 0xA6)
    for k in range(40):  # its string, a missile moved one pixel a line (HMOVE)
        lines[90 + k].dot(113 - k // 2, 1, 0x0A)
    render(lines, "title.png")


# The song's chimes: (eighth, note) of the theme's melody, as heights in the sky.
NOTE_Y = {"C5": 112, "D5": 98, "E5": 84, "G5": 70, "A5": 56, "C6": 42}


def gameplay():
    lines = [sky_line(y) for y in range(H)]
    for y, ln in enumerate(lines):
        hills(ln, y, scroll=7)
        if y < HORIZON - 6:
            sun(ln, y, cx=30)
    score(lines, 6, "18/48", 0x1E)
    kite_x, kite_y = 40, NOTE_Y["G5"] - 4
    for k, b in enumerate(KITE):
        lines[kite_y + k].player(kite_x, b, 0xA6)
    for k in range(HORIZON - (kite_y + 12)):
        lines[kite_y + 12 + k].dot(max(0, kite_x + 3 - k // 3), 1, 0x0A)
    # The chimes coming on the wind, 12 pixels an eighth; one a line band, as the
    # kernel reuses player 1 down the screen.
    melody = [("A5", 0), ("G5", 3), ("E5", 4), ("D5", 8), ("E5", 10), ("C5", 12), ("A5", 16), ("C6", 18)]
    for note, eighth in melody:
        x = kite_x + 12 + 12 * eighth
        if x > 150:
            continue
        y = NOTE_Y[note] - 3
        for k, b in enumerate(CHIME):
            if not lines[y + k].objs or all(o[2] != 0x2E for o in lines[y + k].objs):
                lines[y + k].player(x, b, 0x2E)
    # The chime just caught: a sparkle (the ball) where it was.
    for dy, dx in ((-6, 9), (-2, 12), (2, 8), (6, 11)):
        lines[kite_y + 4 + dy].dot(kite_x + dx, 1, 0x0E)
    render(lines, "gameplay.png")


def palette():
    used = sorted({c for c, _ in [(h | (l << 1), 0) for h, l in SKY]} | {0x62, 0x00, 0x2E, 0x1C, 0x0E, 0xA6, 0x0A})
    img = Image.new("RGB", (16 * 40, 8 * 20))
    for c in range(0, 256, 2):
        hue, luma = c >> 4, (c >> 1) & 7
        for x in range(40):
            for y in range(20):
                img.putpixel((hue * 40 + x, luma * 20 + y), tia_rgb(c))
        if c in used:
            for x in range(40):
                for y in (0, 19):
                    img.putpixel((hue * 40 + x, luma * 20 + y), (255, 255, 255))
    img.save(OUT / "palette.png")


# ---- The theme, on the TIA's two channels ----
AUDIO_HZ = 3579545 / 114
FRAME = 262 * 228 / 114          # audio clocks a frame
MEL = {"C5": 29, "D5": 26, "E5": 23, "G5": 19, "A5": 17, "C6": 14}   # AUDC 4, AUDF
BASS = {"C2": 31, "F2": 23, "A2": 18, "C3": 15}                      # AUDC 1, AUDF
FRAMES_PER_EIGHTH = 15           # 120 beats a minute

THEME = [  # eighth notes; "-" holds, "." rests
    "E5 - G5 - A5 - G5 E5", "D5 - E5 - C5 - - -", "A5 - C6 - A5 - G5 -", "G5 - - - E5 - - -",
    "E5 - G5 - A5 - G5 A5", "C6 - - - A5 - G5 -", "A5 - G5 - E5 - D5 -", "C5 - - - - - . .",
]
ROOTS = ["C2", "A2", "F2", "C2", "C2", "A2", "F2", "C2"]


class Channel:
    def __init__(self):
        self.audc = self.audf = self.audv = 0
        self.div = 0
        self.out = 0
        self.poly4 = 0xF
        self.poly9 = 0x1FF

    def clock(self):
        self.div += 1
        if self.div <= self.audf:
            return self.out * self.audv
        self.div = 0
        if self.audc == 4:              # pure tone: toggles each divided clock
            self.out ^= 1
        elif self.audc == 1:            # 4-bit poly
            fb = ((self.poly4 >> 3) ^ (self.poly4 >> 2)) & 1
            self.poly4 = ((self.poly4 << 1) | fb) & 0xF
            self.out = self.poly4 & 1
        elif self.audc == 8:            # 9-bit poly: noise
            fb = ((self.poly9 >> 8) ^ (self.poly9 >> 4)) & 1
            self.poly9 = ((self.poly9 << 1) | fb) & 0x1FF
            self.out = self.poly9 & 1
        return self.out * self.audv


def theme_events(missed=()):
    """Each frame's (channel 0, channel 1) settings: (AUDC, AUDF, AUDV)."""
    frames = []
    for bar, (mel, root) in enumerate(zip(THEME, ROOTS)):
        notes = mel.split()
        held = None
        for e, n in enumerate(notes):
            if n not in "-.":
                held = (n, 0)
            elif n == ".":
                held = None
            for f in range(FRAMES_PER_EIGHTH):
                # melody: attack then a slow decay, silent if the chime was missed
                if held and (bar, e) not in missed:
                    note, _ = held
                    age = (e - next(i for i in range(e, -1, -1) if notes[i] not in "-.")) * FRAMES_PER_EIGHTH + f
                    ch1 = (4, MEL[note], max(3, 10 - age // 6))
                else:
                    ch1 = (0, 0, 0)
                # channel 0: bass on eighths 0, 2, 4, 6; a snare (noise) on 3 and 7
                if e in (3, 7) and f < 5:
                    ch0 = (8, 4, 8 - f)
                elif e in (3, 7):
                    ch0 = (0, 0, 0)
                else:
                    ch0 = (1, BASS[root], max(2, 7 - f // 3) if e % 2 == 0 else max(1, 4 - f // 3))
                frames.append((ch0, ch1))
    return frames


def theme(name, loops=2, missed=()):
    frames = theme_events(missed) * loops
    ch = [Channel(), Channel()]
    samples, acc = [], 0.0
    for settings in frames:
        for c, (audc, audf, audv) in zip(ch, settings):
            c.audc, c.audf, c.audv = audc, audf, audv
        acc += FRAME
        while acc >= 1:
            acc -= 1
            samples.append(ch[0].clock() + ch[1].clock())
    # The TIA's ~31.4 kHz samples to 44.1 kHz, linearly.
    # Then a DC-blocking filter, as a TV's AC-coupled sound path has, and the peak at -3 dB.
    vals, rate = [], 44100
    n = int(len(samples) * rate / AUDIO_HZ)
    prev_x = prev_y = 0.0
    for i in range(n):
        t = i * AUDIO_HZ / rate
        j = int(t)
        a = samples[j] if j < len(samples) else 0
        b = samples[j + 1] if j + 1 < len(samples) else a
        x = a + (b - a) * (t - j)
        prev_y = x - prev_x + 0.998 * prev_y
        prev_x = x
        vals.append(prev_y)
    peak = max(abs(v) for v in vals) or 1
    out = [int(v / peak * 23000) for v in vals]
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack(f"<{len(out)}h", *out))


def mp3(name):
    """theme.wav to theme.mp3 when ffmpeg is installed (the repo keeps the small MP3s)."""
    import shutil
    import subprocess
    if shutil.which("ffmpeg"):
        wav = OUT / f"{name}.wav"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav), "-b:a", "128k",
                        str(OUT / f"{name}.mp3")], check=True)
        wav.unlink()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    title()
    gameplay()
    palette()
    theme("theme.wav")
    # The same, with four chimes missed: the melody drops out, the band plays on.
    theme("theme_missed.wav", loops=1, missed={(1, 4), (3, 0), (5, 0), (6, 6)})
    mp3("theme")
    mp3("theme_missed")


if __name__ == "__main__":
    main()
