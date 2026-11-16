# Atari 2600

Atari 2600 (VCS) projects.

- Toolchain: [cc65](https://cc65.github.io/) (`ca65` assembler, `ld65` linker)
- Output: cartridge images in each game's `build/` (`.bin` for 4 KB, the
  bank-switching scheme as the extension otherwise, such as `.F8`, as Stella
  takes it)
- Targets: Stella and [retro-silicon](https://github.com/particlesector/retro-silicon)'s
  2600 core, NTSC

| Game | Status |
|---|---|
| [KITESONG](kitesong/) | Complete |
