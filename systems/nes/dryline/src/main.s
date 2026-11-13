; DRYLINE Grand Prix
; NES, MMC3 (mapper 4), 128 KB PRG, 128 KB CHR, battery RAM. Assemble with ca65.

.setcpu "6502"
.include "defs.inc"

.segment "HEADER"
    .byte $4E, $45, $53, $1A, 8, 16, $42, 0, 0, 0, 0, 0, 0, 0, 0, 0

.segment "CHARS"
    .incbin "dryline.chr"

.include "charmap.inc"
.include "kernel.s"
.include "track.s"
.include "race.s"
.include "tracks.inc"

.segment "RODATA"
.include "sprites.inc"
