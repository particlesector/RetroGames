; Reset, interrupts and the small services everything else uses. Lives in the fixed bank.

.segment "CODE"

; The background's upper 128 tiles are swapped between horizontal bands of the
; screen. The MMC3 counter fires a scanline early; the handler waits for the
; next horizontal blank and then makes the single write that swaps the bank.
; Cycle counts matter: keep this routine inside one page and do not reorder it.
irq:
    pha                     ; 3
    sta $E000               ; 4  acknowledge
    lda #18                 ; 2
    sec                     ; 2
@d: sbc #1                  ; 5n-1
    bne @d
    lda irq_bank            ; 3
    sta $8001               ; 4  register 1 was selected by the NMI and stays selected
    txa
    pha
    inc irq_idx
    ldx irq_idx
    lda band_page+1,x
    sta irq_bank
    lda band_latch,x
    beq @last
    sta $C000
    sta $C001
    sta $E001
@last:
    pla
    tax
    pla
    rti

nmi:
    pha
    txa
    pha
    tya
    pha
    lda ppumask_s
    sta PPUMASK
    lda nmi_ready
    beq @noppu
    lda #0
    sta OAMADDR
    lda #>oam
    sta $4014
    ldx #0
@vb:
    lda vbuf,x
    beq @vbdone
    sta PPUADDR
    lda vbuf+1,x
    sta PPUADDR
    ldy vbuf+2,x
    inx
    inx
    inx
@vbl:
    lda vbuf,x
    sta PPUDATA
    inx
    dey
    bne @vbl
    beq @vb
@vbdone:
    lda #0
    sta vbuf
    sta vb_pos
    lda pal_dirty
    beq @nopal
    lda #$3F
    sta PPUADDR
    ldx #0
    stx PPUADDR
@pl:
    lda pal_buf,x
    sta PPUDATA
    inx
    cpx #32
    bne @pl
    lda #$3F
    sta PPUADDR
    lda #0
    sta PPUADDR
    sta PPUADDR
    sta PPUADDR
    sta pal_dirty
@nopal:
    lda ppuctrl_s
    sta PPUCTRL
    lda #0
    sta PPUSCROLL
    sta PPUSCROLL
    sta nmi_ready
@noppu:
    lda split_on            ; MMC3 registers are only touched here while a race screen is up
    beq @snd
    lda band_page
    sta $8001
    lda band_page+1
    sta irq_bank
    lda #0
    sta irq_idx
    lda band_latch
    beq @snd
    sta $C000
    sta $C001
    sta $E000
    sta $E001
@snd:
    inc frame_count
    pla
    tay
    pla
    tax
    pla
    rti

reset:
    sei
    cld
    ldx #$FF
    txs
    inx
    stx PPUCTRL
    stx PPUMASK
    stx $4010
    lda #$40
    sta $4017
    bit PPUSTATUS
@v1:
    bit PPUSTATUS
    bpl @v1
    txa
@clr:
    sta $00,x
    sta $0100,x
    sta $0300,x
    sta $0400,x
    sta $0500,x
    sta $0600,x
    sta $0700,x
    inx
    bne @clr
    lda #$FF
@oamclr:
    sta oam,x
    inx
    bne @oamclr
@v2:
    bit PPUSTATUS
    bpl @v2
    ldx #7
@bank:
    stx $8000
    lda bank_init,x
    sta $8001
    dex
    bpl @bank
    lda #1
    sta $8000               ; register 1 stays selected: see irq
    lda #0
    sta $A000
    sta $E000
    lda #$80
    sta $A001               ; enable battery RAM
    lda #$88                ; NMI on, sprites at $1000, background at $0000
    sta ppuctrl_s
    sta PPUCTRL
    cli
    lda #0
    jsr race_begin
main_loop:
    jsr read_pads
    jsr race_frame
    jsr wait_frame
    jmp main_loop

bank_init: .byte 0, 2, CHR_SPRITES, CHR_SPRITES+1, CHR_SPRITES+2, CHR_SPRITES+3, BANK_RACE0, BANK_RACE1

; A = 8 KB bank to map at $A000. Only call with split_on = 0.
map_a000:
    pha
    lda #7
    sta $8000
    pla
    sta $8001
    lda #1
    sta $8000
    rts

wait_frame:
    lda #1
    sta nmi_ready
    lda frame_count
@w: cmp frame_count
    beq @w
    rts

ppu_off:
    lda #0
    sta ppumask_s
    sta split_on
    jsr oam_begin
    jsr wait_frame
    lda #0
    sta vbuf
    sta vb_pos
    rts

ppu_on:
    lda #MASK_ON
    sta ppumask_s
    jmp wait_frame

; Both controllers. Each is read until two reads agree, so a stray bit cannot register.
read_pads:
    ldx #1
@p: lda pad,x
    sta pad_prev,x
    dex
    bpl @p
    jsr @read
@again:
    lda pad
    sta tmp0
    lda pad+1
    sta tmp1
    jsr @read
    lda pad
    cmp tmp0
    bne @again
    lda pad+1
    cmp tmp1
    bne @again
    ldx #1
@n: lda pad_prev,x
    eor #$FF
    and pad,x
    sta pad_new,x
    dex
    bpl @n
    rts
@read:
    lda #1
    sta $4016
    sta pad+1
    lsr a
    sta $4016
@l: lda $4016
    lsr a
    rol pad
    lda $4017
    lsr a
    rol pad+1
    bcc @l
    rts

; ------------------------------------------------------------------ sprites
oam_begin:
    lda #$FF
    ldx #0
@l: sta oam,x
    inx
    inx
    inx
    inx
    bne @l
    rts

; A = tile at d_x/d_y with attributes d_attr. Slots are handed out with a stride
; so priority rotates and crowded scanlines flicker evenly.
spr8:
    ldx oam_i
    sta oam+1,x
    lda d_y
    sec
    sbc #1
    sta oam,x
    lda d_attr
    sta oam+2,x
    lda d_x
    sta oam+3,x
    txa
    clc
    adc #68
    sta oam_i
    rts

; --------------------------------------------------------------------- text
; X = column, Y = row -> addr_hi/addr_lo
calc_addr:
    tya
    lsr a
    lsr a
    lsr a
    ora #$20
    sta addr_hi
    tya
    asl a
    asl a
    asl a
    asl a
    asl a
    sta addr_lo
    txa
    ora addr_lo
    sta addr_lo
    rts

; print $FF-terminated string at ptr0 straight to the PPU (rendering off)
puts_xy:
    jsr calc_addr
    lda addr_hi
    sta PPUADDR
    lda addr_lo
    sta PPUADDR
    ldy #0
@l: lda (ptr0),y
    cmp #$FF
    beq @r
    sta PPUDATA
    iny
    bne @l
@r: rts

; ------------------------------------------------------------------ copying
; Copy cnt bytes from (ptr0) to the PPU; advances ptr0.
copy_ppu:
    ldy #0
@l: lda cnt
    ora cnt+1
    beq @r
    lda (ptr0),y
    sta PPUDATA
    inc ptr0
    bne :+
    inc ptr0+1
:   lda cnt
    bne :+
    dec cnt+1
:   dec cnt
    jmp @l
@r: rts

; Copy cnt bytes from (ptr0) to (ptr1); advances both.
copy_ram:
    ldy #0
@l: lda cnt
    ora cnt+1
    beq @r
    lda (ptr0),y
    sta (ptr1),y
    inc ptr0
    bne :+
    inc ptr0+1
:   inc ptr1
    bne :+
    inc ptr1+1
:   lda cnt
    bne :+
    dec cnt+1
:   dec cnt
    jmp @l
@r: rts

.segment "VECTORS"
    .word nmi, reset, irq
