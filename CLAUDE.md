# RetroGames

Original homebrew games for retro systems, by ParticleSector. MIT licensed.
The owner writes C++ professionally and tests on FPGA hardware (and MesenCE for NES).

## Layout

- `systems/<system>/<game>/` — one self-contained project per ROM, with its own
  `Makefile` (`all`, `test`, `clean`), `README.md`, `src/`, `assets/`, `tools/`,
  `tests/`, `docs/`, a git-ignored `build/`, and the current playable ROM in `release/`.
- `systems/<system>/README.md` — toolchain and hardware notes for that system.
- `shared/` — anything used by more than one game. A game never reaches into another game's folder.
- Root `README.md` has the games table; add a row for every new game.

## Commands

- `make`, `make test`, `make clean` at the root run every game; `make GAME=nes/tidebell test` runs one.
- Inside a game folder the same targets work directly.
- Tests need Python 3 with Pillow and numpy, and for NES the `libretro-nestopia` package.
  The cloud environment's setup script installs all of it.

## Conventions

- Pitch first: concept, genre, art direction and mock assets go to the owner for a yes before any game code.
- Ask the owner's open questions (language, mapper, scope, target hardware) before writing code.
- Art, levels and music are text or code in the repo, compiled by Python tools in the game's
  `tools/`. No binary source assets.
- Every level carries a machine-checked solution. In TIDEBELL that is the `solve:` line
  under each room in `assets/levels.txt`, replayed by `tests/run_tests.py`. A level that
  the bot cannot clear does not ship.
- After changing a game, run its tests, rebuild, and copy the ROM to `release/` in the same commit.
- State plainly what was not verified (real hardware, other emulators, how audio sounds).
- No model names in commits, code or docs.

## Testing harness

`shared/tools/nes_emu.py` drives a libretro core from Python: set controller input per
frame, read and write CPU RAM, grab frames as images, record audio. Symbols come from the
linker's label file (`labels()`), so tests refer to variables by name.
`systems/nes/tidebell/tests/bot.py` shows the closed-loop pattern: act, read RAM, decide.

## NES notes (from TIDEBELL)

- Toolchain: ca65/ld65, one translation unit, linker config per game.
- Assume NTSC and a standard pad; the owner's targets are an FPGA core and MesenCE.
- With MMC3 scanline IRQs, keep background tiles at $0000 and sprites at $1000, write
  the IRQ registers at the end of NMI after all PPU address writes, and never touch
  $8000 outside NMI if the IRQ handler relies on the selected bank register.
- Cycle-timed handlers must sit inside one page and note their cycle counts in comments.
- NMI must not write $2005/$2006 on frames the main thread has not finished, or it
  corrupts direct PPU writes during screen loads.
- A tile with transparent pixels needs a palette that contains the colour it should show
  through to; check this when adding palette-swap or mid-frame effects.
- ca65 `.charmap` applies to every later string, including the iNES header: write the
  header as numeric bytes.
