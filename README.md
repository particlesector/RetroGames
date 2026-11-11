# RetroGames

Original homebrew games for retro systems. One repo, many systems, many ROMs.

## Layout

```
systems/
  <system>/              one folder per target platform (nes, snes, gb, genesis, ...)
    README.md            toolchain, hardware notes and conventions for that system
    <game>/              one self-contained project per ROM
      README.md          what it is, status, how to build
      docs/              design docs, pitches, reference
      assets/            source art, music and level data
      src/               code
      tools/             scripts used only by this game
      tests/             automated tests
      release/           the current playable ROM
      build/             build output (git-ignored)
shared/                  anything used by more than one game or system
```

Rules of thumb:

- A game folder builds on its own; it never reaches into another game's folder.
- Code or tools needed by two games move to `shared/` (or `systems/<system>/common/` if system-specific).
- Folder names are lowercase, no spaces: `systems/gb/my-game`.
- Build output stays out of git; each game keeps one current ROM in `release/`.

## Games

| System | Game | Status |
|---|---|---|
| NES | [TIDEBELL](systems/nes/tidebell/) | Complete |

## Adding a game

1. Create `systems/<system>/<game>/` (add `systems/<system>/README.md` if the system is new).
2. Give it a `README.md` and add a row to the table above.

## License

[MIT](LICENSE). Everything in this repo — code, art, music, levels and ROMs — is free to use, modify, share and sell, as long as the copyright notice stays with it.
