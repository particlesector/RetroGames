#!/usr/bin/env python3
"""KITESONG's tests, on Stella's libretro core (shared/tools/a2600_emu.py).

- Every song is played to its end by a bot that flies to each chime's lane: it must catch every
  chime (PERFECT), with each caught note ringing on its lane's pitch. This is each song's
  machine-checked solution: a song the bot can't perfect doesn't ship.
- Left alone, the kite runs out of wind and falls: TRY AGAIN.
- Free Flight: the button plays the note at the kite's height and leaves a chime behind.
- The logic never outruns its VBLANK or overscan time (`overruns` stays 0).

With --media DIR it also saves screenshots and a recording of a perfect DUSK.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(GAME.parents[2] / "shared" / "tools"))
from a2600_emu import Emu, labels, FIRE, UP, DOWN, LEFT, RIGHT, RESET, SELECT  # noqa: E402

ROM = str(GAME / "build" / "kitesong.F8")
L = labels(str(GAME / "build" / "labels.txt"))
M_TITLE, M_PLAY, M_FALL, M_RESULT = 0, 1, 2, 3
LANE_Y = [1, 13, 25, 37, 49, 61, 73, 85, 97, 109]


def song_names():
    names = []
    for line in (GAME / "assets" / "songs.txt").read_text().splitlines():
        if line.startswith("song "):
            names.append(line.split(None, 1)[1].strip())
    return names


class Game:
    def __init__(self):
        self.e = Emu(ROM)
        self.e.frame(0, 10)

    ALIAS = {"result": "free"}      # equates the label file doesn't list

    def __getitem__(self, name):
        return self.e.ram[L[self.ALIAS.get(name, name)] - 0x80]

    def arr(self, name, n):
        a = L[name] - 0x80
        return list(self.e.ram[a:a + n])

    def press(self, button):
        self.e.frame(button, 2)
        self.e.frame(0, 2)

    def start(self, index):
        while self["sel"] != index:
            self.press(RIGHT)
        self.press(FIRE)
        assert self["mode"] == M_PLAY, "the song didn't start"


def bot_input(g):
    """Fly toward the next chime's lane."""
    lane = g["cur_lane"]
    if lane >= 10:
        return 0
    target = LANE_Y[9 - lane]
    y = g["kite_y"]
    if y > target + 1:
        return UP
    if y < target - 1:
        return DOWN
    return 0


COPIES = {0: [0], 1: [0, 16], 2: [0, 32], 3: [0, 16, 32], 4: [0, 64], 6: [0, 32, 64]}


def chime_times(index):
    """The song's chimes: (lane, time in pixels), from the compiled data."""
    lines = (GAME / "build" / "songs.inc").read_text().splitlines()
    start = lines.index(f"SONG{index}_MEL:") + 1
    t, out = 0, []
    for line in lines[start:]:
        if ".byte" not in line:
            break
        vals = [int(v.strip().lstrip("$"), 16) if "$" in v else int(v) for v in line.split(".byte")[1].split(",")]
        for k in range(0, len(vals), 2):
            t += vals[k]
            if vals[k + 1] < 0xFE:
                out.append((vals[k + 1], t))
    return out


def unseen(g, chimes, misses):
    """Chimes on screen (x 8 up to the kite's window) that this frame's list doesn't draw; a chime
    missing two frames running counts as hidden (one is the flicker of a band's second group)."""
    a = L["now"] - 0x80
    now = g.e.ram[a] | g.e.ram[a + 1] << 8
    lx, nus, chl = g.arr("lane_x", 10), g.arr("lane_nus", 10), g.arr("lane_chl", 10)
    hidden = []
    for i, (lane, t) in enumerate(chimes):
        ahead = t - now
        x = 116 - ahead
        if not (4 < ahead and x >= 8):
            continue
        b = 9 - lane
        shown = chl[b] == (L["CHIME"] & 0xFF) and any(abs(lx[b] + o - x) <= 1 for o in COPIES.get(nus[b], [0]))
        misses[i] = 0 if shown else misses.get(i, 0) + 1
        if misses[i] >= 2:
            hidden.append(i)
    return hidden


def play_song(index, media=None):
    g = Game()
    g.start(index)
    total = g["total"]
    notes, caught = [], 0
    frames = 0
    chimes, misses, g.hidden = chime_times(index), {}, set()
    if media:
        g.e.record_audio = True
    while g["mode"] in (M_PLAY, M_FALL) and frames < 60 * 300:
        g.e.frame(bot_input(g))
        frames += 1
        g.hidden.update(unseen(g, chimes, misses))
        if g["caught"] != caught:
            caught = g["caught"]
            notes.append(g["m_note"])
        if media and frames == 30 * 60 // 2:
            g.e.screenshot().save(os.path.join(media, "play.png"))
    return g, total, notes, frames


def expected_lanes(index):
    """The song's chime lanes in order, from the compiled data."""
    text = (GAME / "build" / "songs.inc").read_text()
    lines = text.splitlines()
    start = lines.index(f"SONG{index}_MEL:") + 1
    lanes = []
    for line in lines[start:]:
        if not line.strip().startswith(".byte"):
            break
        vals = [v.strip() for v in line.strip()[5:].split(",")]
        for k in range(1, len(vals), 2):
            v = int(vals[k].lstrip("$"), 16)
            if v < 0xFE:
                lanes.append(v)
    return lanes


def run_case(case, media):
    """One case in this process (Stella's core holds one game a process)."""
    names = song_names()
    fails = 0

    def check(ok, what):
        nonlocal fails
        print(("ok   " if ok else "FAIL ") + what, flush=True)
        fails += not ok

    if case < len(names) - 1:                      # a song (the last is Free Flight)
        i, name = case, names[case]
        g, total, notes, frames = play_song(i, media if (media and i == 0) else None)
        check(g["mode"] == M_RESULT and g["result"] == 2,
              f"{name}: the bot plays it perfectly ({g['caught']}/{total} chimes, {frames / 60:.0f} s)")
        check(notes == expected_lanes(i), f"{name}: each caught chime rings its own lane's note")
        check(not g.hidden, f"{name}: every chime is drawn from the left edge on"
              + (f" (hidden: {sorted(g.hidden)})" if g.hidden else ""))
        check(g["overruns"] == 0, f"{name}: no frame's logic outran its time")
        check(bool(g["stars"] & (1 << i)), f"{name}: a perfect song lights its star")
        if media and i == 0:
            g.e.save_audio(os.path.join(media, "dusk.wav"))
            g.e.frame(0, 10)
            g.e.screenshot().save(os.path.join(media, "result.png"))
    elif case == len(names) + 1:                   # the clouds move evenly
        from collections import Counter
        g = Game()
        g.start(0)
        offs = Counter()
        for _ in range(1500):
            lx, nus, chl = g.arr("lane_x", 10), g.arr("lane_nus", 10), g.arr("lane_chl", 10)
            g.e.frame(bot_input(g))
            im = g.e.screenshot()
            sky0 = next(y for y in range(14, 60) if im.getpixel((150, y)) != (0, 0, 0)
                        and im.getpixel((150, y - 1)) == (0, 0, 0))   # the sky's first line
            for b in range(5):                     # the top bands, clear of the sun
                if chl[b] != (L["CHIME"] & 0xFF) or nus[b] != 0 or lx[b] >= 95:
                    continue
                row = sky0 + 14 * b + 7            # the cloud's widest row
                px = [im.getpixel((x, row)) for x in range(160)]
                s = [x for x in range(8, 112) if px[x] != px[150]]
                if s:
                    offs[s[0] - lx[b]] += 1
        top = offs.most_common(1)[0]
        check(top[1] >= 0.98 * sum(offs.values()),
              f"a cloud is drawn where the list says, 1 pixel a step (offsets seen: {dict(offs)})")
    elif case == len(names) - 1:                   # left alone, the kite runs out of wind
        g = Game()
        g.start(0)
        fell = False
        for _ in range(60 * 60):
            g.e.frame(0)
            fell |= g["mode"] == M_FALL
            if g["mode"] == M_RESULT:
                break
        check(fell and g["mode"] == M_RESULT and g["result"] == 0, "left alone, the kite falls: TRY AGAIN")
    elif case == len(names):                       # attract mode
        g = Game()
        g.e.frame(0, 700)
        check(g["mode"] == M_PLAY and g["demo"] == 1, "ten quiet seconds on the title start a demo")
        while g["mode"] == M_PLAY:
            g.e.frame(0)
        check(g["result"] == 2, f"the demo flies its song perfectly ({g['caught']}/{g['total']})")
        g.e.frame(0, 400)
        check(g["mode"] == M_TITLE, "after the demo's results, back to the title")
        g.e.frame(0, 700)
        g.e.frame(0, 60)
        g.press(UP)
        check(g["mode"] == M_TITLE, "touching the joystick ends a demo")
    else:                                          # Free Flight
        g = Game()
        if media:
            g.e.frame(0, 30)
            g.e.screenshot().save(os.path.join(media, "title.png"))
        g.start(len(names) - 1)
        ok = True
        for band in (0, 4, 9, 2):
            target = LANE_Y[band]
            for _ in range(80):
                y = g["kite_y"]
                g.e.frame(UP if y > target + 1 else DOWN if y < target - 1 else 0)
            g.press(FIRE)
            ok &= g["m_note"] == 9 - band and g.arr("rec_band", 1)[0] == band and g["m_vol"] > 0
            g.e.frame(0, 20)
        if media:
            g.e.screenshot().save(os.path.join(media, "free.png"))
        check(ok, "Free Flight: the button plays the kite's note and leaves its chime")
        g.press(SELECT)
        check(g["mode"] == M_TITLE, "Select leaves Free Flight for the title")
        check(g["overruns"] == 0, "Free Flight: no frame's logic outran its time")
    return fails


def main():
    import subprocess
    media = None
    if "--media" in sys.argv:
        media = sys.argv[sys.argv.index("--media") + 1]
        os.makedirs(media, exist_ok=True)
    if "--case" in sys.argv:
        sys.exit(1 if run_case(int(sys.argv[sys.argv.index("--case") + 1]), media) else 0)
    fails = 0
    for case in range(len(song_names()) + 3):
        cmd = [sys.executable, __file__, "--case", str(case)] + (["--media", media] if media else [])
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        print(r.stdout, end="")
        fails += r.returncode != 0
    print("all passed" if not fails else f"{fails} case(s) failed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
