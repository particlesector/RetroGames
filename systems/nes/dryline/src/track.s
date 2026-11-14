; Loading a circuit: tiles, palettes, the tile bands and the surface map.

.segment "CODE"

.macro SETCNT n
    lda #<(n)
    sta cnt
    lda #>(n)
    sta cnt+1
.endmacro

; A = circuit number. Turns the screen off and leaves it off.
load_track:
    sta cur_track
    jsr ppu_off
    ldx cur_track
    lda track_bank,x
    jsr map_a000
    ldx cur_track
    lda track_lo,x
    sta ptr0
    lda track_hi,x
    sta ptr0+1
    ldy #0
    lda (ptr0),y
    sta band_count
    iny
@sp:
    lda (ptr0),y
    sta band_split-1,y
    iny
    cpy #4
    bne @sp
    lda (ptr0),y
    sta track_laps
    iny
    ldx #0
@gr:
    lda (ptr0),y
    sta grid_xy,x
    iny
    inx
    cpx #16                 ; grid, pit box and weather script are contiguous in RAM
    bne @gr
    ldx #0
@pf:
    lda (ptr0),y
    sta pal_fair,x
    iny
    inx
    cpx #48                 ; fair palette, rain palette and the name are contiguous in RAM
    bne @pf
    lda #$FF
    sta track_name+16
    tya
    clc
    adc ptr0
    sta ptr0
    bcc :+
    inc ptr0+1
:   lda #$20
    sta PPUADDR
    lda #$00
    sta PPUADDR
    SETCNT 960
    jsr copy_ppu
    lda #<wetmap
    sta ptr1
    lda #>wetmap
    sta ptr1+1
    SETCNT 960
    jsr copy_ram
    SETCNT 64               ; the attribute table follows the nametable in the PPU too
    jsr copy_ppu
    lda #<surface
    sta ptr1
    lda #>surface
    sta ptr1+1
    SETCNT 960
    jsr copy_ram
    lda #<wp_x
    sta ptr1
    lda #>wp_x
    sta ptr1+1
    SETCNT MAXWP*4
    jsr copy_ram
    lda #BANK_RACE1
    jsr map_a000
    ; tile banks
    ldx cur_track
    lda chr_base,x
    pha
    ldx #0
    stx $8000
    sta $8001
    inx
    stx $8000               ; leave register 1 selected
    pla
    clc
    adc #2
    ldx #0
@bp:
    sta band_page,x
    adc #2
    inx
    cpx #4
    bne @bp
    lda band_page
    sta $8001
    ; counter values for each split
    lda #0
    sta band_latch
    sta band_latch+1
    sta band_latch+2
    sta band_latch+3
    lda band_count
    cmp #2
    bcc @pal
    lda band_split
    clc
    adc #IRQ_FIRST
    sta band_latch
    ldx #1
@bl:
    inx
    cpx band_count
    bcs @pal
    dex
    lda band_split,x
    sec
    sbc band_split-1,x
    clc
    adc #IRQ_NEXT
    sta band_latch,x
    inx
    bne @bl
@pal:
    ldx #15
@p: lda pal_fair,x
    sta pal_buf,x
    lda sprite_pals,x
    sta pal_buf+16,x
    dex
    bpl @p
    lda pal_buf
    sta pal_buf+16
    lda #1
    sta pal_dirty
    rts

.segment "RODATA"
chr_base:
    .repeat 8, i
    .byte CHR_TRACKS + i * TRACK_PAGES
    .endrepeat
sprite_pals:
    .byte $0F,$0F,$16,$30, $0F,$0F,$2C,$30, $0F,$0F,$28,$30, $0F,$0F,$24,$30
