; TIDEBELL - a tale of the last lighthouse
; NES, MMC3 (mapper 4). Assemble with ca65; see the Makefile.

.setcpu "6502"

PPUCTRL   = $2000
PPUMASK   = $2001
PPUSTATUS = $2002
OAMADDR   = $2003
PPUSCROLL = $2005
PPUADDR   = $2006
PPUDATA   = $2007

BTN_A = $80
BTN_B = $40
BTN_SELECT = $20
BTN_START = $10
BTN_UP = $08
BTN_DOWN = $04
BTN_LEFT = $02
BTN_RIGHT = $01

T_AIR = 0           ; metatile collision types (see tools/build_chr.py)
T_SOLID = 1
T_PLAT = 2
T_HAZ = 3
T_CORAL = 4
T_DOOR = 5
T_CASTLE = 6

O_EMBER = 1
O_CRAB = 2
O_JELLY = 3
O_RAFT = 4
MAXOBJ = 8

S_TITLE = 0
S_PASS = 1
S_CARD = 2
S_PLAY = 3
S_END = 4

P_ALIVE = 0
P_DYING = 1
P_CLEAR = 2
P_HIDDEN = 3

STORM_HOLD = 200
MASK_ON = $1E
MASK_WET = $9E      ; blue emphasis below the waterline

oam = $0200

.segment "HEADER"
    .byte $4E, $45, $53, $1A, 2, 2, $40, 0, 0, 0, 0, 0, 0, 0, 0, 0

.segment "CHARS"
    .incbin "tidebell.chr"

.segment "RODATA"
.include "gfx.inc"

.segment "ZEROPAGE"
tmp0:       .res 1
tmp1:       .res 1
tmp2:       .res 1
tmp3:       .res 1
ptr0:       .res 2
nmi_ready:  .res 1
frame_count:.res 1
ppumask_s:  .res 1
ppuctrl_s:  .res 1
dry_bank:   .res 1
wet_bank:   .res 1
split_on:   .res 1
irq_line:   .res 1
pal_dirty:  .res 1
vb_pos:     .res 1
pad:        .res 1
pad_new:    .res 1
pad_prev:   .res 1
state:      .res 1
timer:      .res 1
room:       .res 1
palidx:     .res 1
menu_sel:   .res 1
paused:     .res 1
tide_y:     .res 3
tide_level: .res 1
water_y:    .res 1
storm:      .res 1
storm_t:    .res 1
storm_ph:   .res 1
flash:      .res 1
px:         .res 1
py:         .res 1
pys:        .res 1
vyl:        .res 1
vyh:        .res 1
pface:      .res 1
pground:    .res 1
pwet:       .res 1
pbell:      .res 1
praft:      .res 1
pstate:     .res 1
pmoving:    .res 1
chk_x:      .res 1
chk_y:      .res 1
tmp_t:      .res 1
tmp_n:      .res 1
feet:       .res 1
carried:    .res 1
banked:     .res 1
e_count:    .res 1
hud_dirty:  .res 1
door_x:     .res 1
door_y:     .res 1
door_idx:   .res 1
oam_i:      .res 1
d_x:        .res 1
d_y:        .res 1
d_frame:    .res 1
d_attr:     .res 1
name_ptr:   .res 2
hint_ptr:   .res 2
pw:         .res 4
pw_pos:     .res 1
addr_hi:    .res 1
addr_lo:    .res 1
obj_i:      .res 1
glint_x:    .res 1

.segment "BSS"
mt_map:     .res 256        ; metatile ids, 16 per row, 15 rows (+1 row of padding)
vbuf:       .res 96         ; NMI VRAM queue: hi, lo, len, data..., 0
pal_buf:    .res 32
o_type:     .res MAXOBJ
o_x:        .res MAXOBJ
o_y:        .res MAXOBJ
o_dir:      .res MAXOBJ
o_rest:     .res MAXOBJ
e_x:        .res 4
e_y:        .res 4
e_state:    .res 4          ; 0 home, 1 carried, 2 banked

.macro PRINT col, row, str
    lda #<(str)
    sta ptr0
    lda #>(str)
    sta ptr0+1
    ldx #(col)
    ldy #(row)
    jsr puts_xy
.endmacro

.macro PRINTB col, row, str
    lda #<(str)
    sta ptr0
    lda #>(str)
    sta ptr0+1
    ldx #(col)
    ldy #(row)
    jsr puts_buf
.endmacro

; =============================================================== fixed bank
.segment "FIXED"

; The waterline. The MMC3 scanline counter fires just above water_y; one
; scanline later, in hblank, the background bank is swapped to the submerged
; tile set, and two scanlines after that blue emphasis is switched on. Cycle counts
; matter here: keep this routine inside one page and do not reorder it.
irq:
    pha                     ; 3
    sta $E000               ; 4  acknowledge
    lda #18                 ; 2
    sec                     ; 2
@d1:
    sbc #1                  ; 5n-1
    bne @d1
    lda wet_bank            ; 3
    sta $8001               ; 4  lands near dot 270 of the next line
    lda #43
    sec
@d2:
    sbc #1
    bne @d2
    nop
    lda #MASK_WET
    sta PPUMASK
    pla
    rti

nmi:
    pha
    txa
    pha
    tya
    pha
    lda ppumask_s           ; also clears last frame's emphasis
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
    lda #0
    sta $8000               ; R0 stays selected for the IRQ handler
    lda dry_bank
    sta $8001
    lda split_on
    beq @nosplit
    lda irq_line
    sta $C000
    sta $C001
    sta $E000
    sta $E001
    jmp @snd
@nosplit:
    sta $E000
@snd:
    jsr sound_update
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
    lda #0
    sta $A000
    sta $E000
    sta dry_bank
    lda #8
    sta wet_bank
    lda #$88                ; NMI on, sprites at $1000, background at $0000
    sta ppuctrl_s
    sta PPUCTRL
    jsr sound_init
    cli
    jsr enter_title
main_loop:
    jsr read_pad
    jsr run_state
    jsr wait_frame
    jmp main_loop

bank_init: .byte 0, 2, 4, 5, 6, 7, 0, 1

.segment "VECTORS"
    .word nmi, reset, irq

; ================================================================ main code
.segment "CODE"

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
    jsr set_split
    lda #MASK_ON
    sta ppumask_s
    jmp wait_frame

read_pad:
    lda pad
    sta pad_prev
    lda #1
    sta $4016
    sta pad
    lsr a
    sta $4016
@l: lda $4016
    lsr a
    rol pad
    bcc @l
    lda pad_prev
    eor #$FF
    and pad
    sta pad_new
    rts

run_state:
    lda state
    asl a
    tax
    lda state_tbl+1,x
    pha
    lda state_tbl,x
    pha
    rts

set_split:
    lda water_y
    cmp #236
    bcs @off
    sec
    sbc #1
    sta irq_line
    lda #1
    sta split_on
    rts
@off:
    lda #0
    sta split_on
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

; A = tile, position d_x/d_y, attributes d_attr. Slots are handed out with a
; stride so that priority rotates and overloaded scanlines flicker fairly.
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

; 16x16 frame d_frame at d_x/d_y; d_attr bit 6 mirrors it. Preserves d_x/d_y.
draw16:
    lda d_x
    sta tmp0
    lda d_y
    sta tmp1
    lda #0
    sta tmp2
    sta tmp3
    lda d_attr
    and #$40
    beq @l
    inc tmp3
@l: lda tmp2
    eor tmp3
    clc
    adc d_frame
    tay
    lda frame_tiles,y
    beq @skip
    pha
    lda tmp2
    and #1
    asl a
    asl a
    asl a
    clc
    adc tmp0
    sta d_x
    lda tmp2
    and #2
    asl a
    asl a
    clc
    adc tmp1
    sta d_y
    pla
    jsr spr8
@skip:
    inc tmp2
    lda tmp2
    cmp #4
    bne @l
    lda tmp0
    sta d_x
    lda tmp1
    sta d_y
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

; queue a string for the next vblank
puts_buf:
    jsr calc_addr
    ldx vb_pos
    stx tmp0
    lda addr_hi
    sta vbuf,x
    lda addr_lo
    sta vbuf+1,x
    inx
    inx
    inx
    ldy #0
@l: lda (ptr0),y
    cmp #$FF
    beq @e
    sta vbuf,x
    inx
    iny
    bne @l
@e: tya
    ldy tmp0
    sta vbuf+2,y
    lda #0
    sta vbuf,x
    stx vb_pos
    rts

; ------------------------------------------------------------- room loading
; A = room or scene number. Turns rendering off and unpacks the room into RAM.
room_begin:
    sta tmp3
    jsr ppu_off
    ldx tmp3
    lda room_lo,x
    sta ptr0
    lda room_hi,x
    sta ptr0+1
    ldy #0
@h: lda (ptr0),y
    sta tide_y,y
    iny
    cpy #3
    bne @h
    lda (ptr0),y
    pha
    and #3
    sta tide_level
    pla
    and #$80
    sta storm
    iny
    lda (ptr0),y
    sta px
    iny
    lda (ptr0),y
    sta py
    iny
    lda (ptr0),y
    sta palidx
    iny
    tya
    clc
    adc ptr0
    sta name_ptr
    lda ptr0+1
    adc #0
    sta name_ptr+1
@n: lda (ptr0),y
    iny
    cmp #$FF
    bne @n
    tya
    clc
    adc ptr0
    sta hint_ptr
    lda ptr0+1
    adc #0
    sta hint_ptr+1
@n2:
    lda (ptr0),y
    iny
    cmp #$FF
    bne @n2
    tya
    clc
    adc ptr0
    sta ptr0
    bcc :+
    inc ptr0+1
:   lda #0
    tax
@z: sta mt_map,x
    inx
    bne @z
    ldy #0
@m: lda (ptr0),y
    sta mt_map+32,y
    iny
    cpy #208
    bne @m
    lda ptr0
    clc
    adc #208
    sta ptr0
    bcc :+
    inc ptr0+1
:   lda #0
    sta e_count
    sta tmp0
    ldx #MAXOBJ-1
@co:
    sta o_type,x
    dex
    bpl @co
    ldx #3
@ce:
    sta e_state,x
    dex
    bpl @ce
    ldy #0
@o: lda (ptr0),y
    cmp #$FF
    beq @od
    cmp #O_EMBER
    bne @other
    ldx e_count
    iny
    lda (ptr0),y
    sta e_x,x
    iny
    lda (ptr0),y
    sta e_y,x
    iny
    inc e_count
    bne @o
@other:
    ldx tmp0
    sta o_type,x
    iny
    lda (ptr0),y
    sta o_x,x
    iny
    lda (ptr0),y
    sta o_y,x
    iny
    lda #1
    sta o_dir,x
    inc tmp0
    sty tmp1
    jsr obj_rest
    ldy tmp1
    jmp @o
@od:
    ldx tide_level
    lda tide_y,x
    sta water_y
    lda #0
    sta pys
    sta vyl
    sta vyh
    sta pface
    sta pwet
    sta pbell
    sta carried
    sta banked
    sta pstate
    sta paused
    sta flash
    sta storm_ph
    sta pground
    sta hud_dirty
    lda #$FF
    sta praft
    sta door_y
    lda #STORM_HOLD
    sta storm_t
    ldx #0
@d: lda mt_map,x
    cmp #MT_DOOR
    bne :+
    stx door_idx
    txa
    and #$F0
    sta door_y
    txa
    asl a
    asl a
    asl a
    asl a
    sta door_x
:   inx
    bne @d
    rts

; X = object slot: find the floor under it and derive its resting height.
obj_rest:
    lda o_x,x
    lsr a
    lsr a
    lsr a
    lsr a
    sta tmp2
    lda o_y,x
    and #$F0
    ora tmp2
    tay
@l: tya
    clc
    adc #16
    bcs @bottom
    cmp #240
    bcs @bottom
    tay
    stx tmp2
    ldx mt_map,y
    lda mt_type,x
    ldx tmp2
    cmp #T_SOLID
    bne @l
    tya
    and #$F0
    jmp @got
@bottom:
    lda #240
@got:
    sta tmp2
    lda o_type,x
    cmp #O_RAFT
    beq @raft
    lda tmp2
    sec
    sbc #16
    sta o_rest,x
    lda o_type,x
    cmp #O_CRAB
    bne @r
    lda o_rest,x
    sta o_y,x
@r: rts
@raft:
    lda tmp2
    sec
    sbc #8
    sta o_rest,x
    rts

; A = how many big lighthouse lamps to light (scenes only)
light_lamps:
    sta tmp0
    ldx #0
@l: lda tmp0
    beq @r
    lda mt_map,x
    cmp #MT_BLAMP_L
    bne @n
    lda #MT_BLIT_L
    sta mt_map,x
    lda #MT_BLIT_R
    sta mt_map+1,x
    dec tmp0
@n: inx
    bne @l
@r: rts

; Draw palette, nametable and attributes from mt_map (rendering off).
room_draw:
    lda palidx
    asl a
    asl a
    asl a
    asl a
    tax
    ldy #0
@p: lda island_pals,x
    sta pal_buf,y
    inx
    iny
    cpy #16
    bne @p
@s: lda sprite_pals-16,y
    sta pal_buf,y
    iny
    cpy #32
    bne @s
    lda pal_buf
    sta pal_buf+16
    lda #$3F
    sta PPUADDR
    ldx #0
    stx PPUADDR
@w: lda pal_buf,x
    sta PPUDATA
    inx
    cpx #32
    bne @w
    lda #$20
    sta PPUADDR
    lda #0
    sta PPUADDR
    tax
@rp:
    stx tmp0
    ldy #16
@t: sty tmp1
    ldy mt_map,x
    lda mt_tl,y
    sta PPUDATA
    lda mt_tr,y
    sta PPUDATA
    ldy tmp1
    inx
    dey
    bne @t
    ldx tmp0
    ldy #16
@b: sty tmp1
    ldy mt_map,x
    lda mt_bl,y
    sta PPUDATA
    lda mt_br,y
    sta PPUDATA
    ldy tmp1
    inx
    dey
    bne @b
    cpx #240
    bne @rp
    ldx #0
@a: ldy mt_map+17,x
    lda mt_pal,y
    asl a
    asl a
    sta tmp0
    ldy mt_map+16,x
    lda mt_pal,y
    ora tmp0
    asl a
    asl a
    sta tmp0
    ldy mt_map+1,x
    lda mt_pal,y
    ora tmp0
    asl a
    asl a
    sta tmp0
    ldy mt_map,x
    lda mt_pal,y
    ora tmp0
    sta PPUDATA
    inx
    inx
    txa
    and #$0F
    bne @a
    txa
    clc
    adc #16
    tax
    bne @a
    rts

hud_draw:
    ldx #2
    ldy #1
    jsr calc_addr
    lda addr_hi
    sta PPUADDR
    lda addr_lo
    sta PPUADDR
    lda room
    lsr a
    lsr a
    lsr a
    clc
    adc #T_0+1
    sta PPUDATA
    lda str_dash
    sta PPUDATA
    lda room
    and #7
    clc
    adc #T_0+1
    sta PPUDATA
    lda name_ptr
    sta ptr0
    lda name_ptr+1
    sta ptr0+1
    ldx #6
    ldy #1
    jsr puts_xy
    lda hint_ptr
    sta ptr0
    lda hint_ptr+1
    sta ptr0+1
    ldx #4
    ldy #4
    jsr puts_xy
    PRINT 22, 2, str_tide
    lda #$23                ; ember icons use the lighthouse palette
    sta PPUADDR
    lda #$C0
    sta PPUADDR
    sta PPUDATA
    lda #$30
    sta PPUDATA
    inc hud_dirty
    rts

; Queue ember icons and tide pips.
hud_flush:
    lda hud_dirty
    bne :+
    rts
:   lda #0
    sta hud_dirty
    ldx vb_pos
    lda #$20
    sta vbuf,x
    lda #$42
    sta vbuf+1,x
    lda e_count
    sta vbuf+2,x
    inx
    inx
    inx
    ldy #0
@e: sty tmp0
    lda e_state,y
    tay
    lda icon_tbl,y
    sta vbuf,x
    inx
    ldy tmp0
    iny
    cpy e_count
    bne @e
    lda #$20
    sta vbuf,x
    lda #$5B
    sta vbuf+1,x
    lda #3
    sta vbuf+2,x
    inx
    inx
    inx
    ldy #0
@p: lda #T_PIP_ON
    cpy tide_level
    bcc :+
    beq :+
    lda #T_PIP_OFF
:   sta vbuf,x
    inx
    iny
    cpy #3
    bne @p
    lda #0
    sta vbuf,x
    stx vb_pos
    rts

; Swap the lamp above the door for its lit version.
light_door_lamp:
    lda door_idx
    sec
    sbc #16
    sta tmp0
    lsr a
    lsr a
    lsr a
    lsr a
    sta tmp1                ; metatile row
    lsr a
    lsr a
    ora #$20
    sta addr_hi
    lda tmp1
    and #3
    lsr a
    ror a
    ror a                   ; (row & 3) << 6
    sta addr_lo
    lda tmp0
    and #$0F
    asl a
    ora addr_lo
    sta addr_lo
    ldx vb_pos
    lda addr_hi
    sta vbuf,x
    sta vbuf+5,x
    lda addr_lo
    sta vbuf+1,x
    clc
    adc #32
    sta vbuf+6,x
    lda #2
    sta vbuf+2,x
    sta vbuf+7,x
    lda mt_tl+MT_LAMPLIT
    sta vbuf+3,x
    lda mt_tr+MT_LAMPLIT
    sta vbuf+4,x
    lda mt_bl+MT_LAMPLIT
    sta vbuf+8,x
    lda mt_br+MT_LAMPLIT
    sta vbuf+9,x
    lda #0
    sta vbuf+10,x
    txa
    clc
    adc #10
    sta vb_pos
    rts

; ---------------------------------------------------------------- collision
; X = pixel x, Y = pixel y -> A = collision type. Coral is solid only while
; its whole cell is under water, sandcastle only while wholly above it.
; Clobbers X, Y.
get_type:
    cpy #240
    bcs @solid
    tya
    and #$F0
    sta tmp_t
    txa
    lsr a
    lsr a
    lsr a
    lsr a
    ora tmp_t
    tax
    ldy mt_map,x
    lda mt_type,y
    cmp #T_CORAL
    bne @castle
    lda tmp_t
    cmp water_y
    bcs @solid
@air:
    lda #T_AIR
    rts
@castle:
    cmp #T_CASTLE
    bne @r
    lda tmp_t               ; sandcastle: solid only while wholly above water
    clc
    adc #16
    cmp water_y
    beq @solid
    bcs @air
@solid:
    lda #T_SOLID
@r: rts

; A = y, chk_x = x -> carry set if solid
chk_pt:
    tay
    ldx chk_x
    jsr get_type
    cmp #T_SOLID
    beq :+
    clc
    rts
:   sec
    rts

; A = x: test Pim's body column at three heights
check_col:
    sta chk_x
    lda py
    clc
    adc #3
    jsr chk_pt
    bcs @r
    lda py
    clc
    adc #9
    jsr chk_pt
    bcs @r
    lda py
    clc
    adc #15
    jsr chk_pt
@r: rts

; A = y: test under/over Pim's two feet columns
check_row:
    sta chk_y
    lda px
    clc
    adc #4
    sta chk_x
    lda chk_y
    jsr chk_pt
    bcs @r
    lda px
    clc
    adc #11
    sta chk_x
    lda chk_y
    jsr chk_pt
@r: rts

; Carry set if Pim has something to stand on (solid, dock or raft).
supported:
    lda py
    clc
    adc #16
    sta feet
    jsr check_row
    bcs @yes
    lda feet
    and #15
    bne @raft
    lda px
    clc
    adc #4
    tax
    ldy feet
    jsr get_type
    cmp #T_PLAT
    beq @yes
    lda px
    clc
    adc #11
    tax
    ldy feet
    jsr get_type
    cmp #T_PLAT
    beq @yes
@raft:
    ldx #MAXOBJ-1
@lp:
    lda o_type,x
    cmp #O_RAFT
    bne @nx
    lda feet
    sec
    sbc o_y,x
    cmp #4
    bcs @nx
    lda px
    clc
    adc #11
    cmp o_x,x
    bcc @nx
    lda o_x,x
    clc
    adc #27
    cmp px
    bcc @nx
    lda o_y,x
    sec
    sbc #16
    sta py
    stx praft
@yes:
    sec
    rts
@nx:
    dex
    bpl @lp
    clc
    rts

; ------------------------------------------------------------------- player
; Walk/swim sideways up to tmp_n pixels according to the d-pad.
p_horiz:
    lda pad
    and #BTN_RIGHT
    beq @chkl
    lda #0
    sta pface
@r: lda px
    cmp #240
    bcs @done
    clc
    adc #12
    jsr check_col
    bcs @done
    inc px
    dec tmp_n
    bne @r
    beq @moved
@chkl:
    lda pad
    and #BTN_LEFT
    beq @done
    lda #$40
    sta pface
@l: lda px
    beq @done
    clc
    adc #3
    jsr check_col
    bcs @done
    dec px
    dec tmp_n
    bne @l
@moved:
    lda #1
    sta pmoving
@done:
    rts

player_update:
    lda px                  ; caught inside a block that just turned solid: float up out of it
    clc
    adc #8
    tax
    lda py
    clc
    adc #9
    tay
    jsr get_type
    cmp #T_SOLID
    bne :+
    lda py
    cmp #34
    bcc :+
    dec py
    rts
:   ldx praft
    bmi :+
    lda o_y,x
    sec
    sbc #16
    sta py
:   lda #$FF
    sta praft
    lda #0
    sta pmoving
    lda py
    clc
    adc #8
    cmp water_y
    bcs @wet
    lda pwet
    beq @dry
    lda py                  ; was swimming: follow a falling surface down
    clc
    adc #11
    cmp water_y
    bcc @dry
    lda py
    clc
    adc #16
    jsr check_row
    bcs @dry
    inc py
    jmp swim_mode
@wet:
    lda pwet
    bne :+
    lda #1
    sta pwet
    lda #SFX_SPLASH
    jsr sfx_play
    jsr drop_embers
:   jmp swim_mode
@dry:
    lda #0
    sta pwet
    ; fall through

land_mode:
    lda pbell
    beq :+
    dec pbell
:   lda #1
    sta tmp_n
    lda frame_count
    and #3
    bne :+
    inc tmp_n
:   jsr p_horiz
    lda pground
    beq @nojump
    lda pad_new
    and #BTN_A
    beq @nojump
    lda #$C0                ; jump: -4.25 px/frame
    sta vyl
    lda #$FB
    sta vyh
    lda #0
    sta pground
    lda #SFX_JUMP
    jsr sfx_play
@nojump:
    lda vyh                 ; releasing A cuts the jump short
    bpl @grav
    cmp #$FE
    bcs @grav
    lda pad
    and #BTN_A
    bne @grav
    lda #$FE
    sta vyh
    lda #$80
    sta vyl
@grav:
    lda vyl
    clc
    adc #$40
    sta vyl
    lda vyh
    adc #0
    sta vyh
    bmi @mv
    cmp #4
    bcc @mv
    lda #4
    sta vyh
    lda #0
    sta vyl
@mv:
    lda pys
    clc
    adc vyl
    sta pys
    lda vyh
    adc #0
    sta tmp_n               ; whole pixels to move this frame (signed)
    lda vyh
    bmi @rise
@fall:
    jsr supported
    bcs @land
    lda tmp_n
    beq @air
    dec tmp_n
    inc py
    bne @fall
@land:
    lda #0
    sta vyl
    sta vyh
    sta pys
    lda #1
    sta pground
    rts
@air:
    lda #0
    sta pground
    rts
@rise:
    lda #0
    sta pground
@rl:
    lda tmp_n
    beq @rdone
    lda py
    cmp #34
    bcc @bonk
    clc
    adc #2
    jsr check_row
    bcs @bonk
    dec py
    inc tmp_n
    bne @rl
@rdone:
    rts
@bonk:
    lda #0
    sta vyl
    sta vyh
    rts

swim_mode:
    lda #0
    sta pground
    sta vyl
    sta vyh
    sta pys
    sta pbell
    lda frame_count
    and #1
    clc
    adc #1
    sta tmp_n
    jsr p_horiz
    lda pad_new             ; A at the surface: hop out of the water
    and #BTN_A
    beq @vert
    lda py
    clc
    adc #6
    cmp water_y
    beq :+
    bcs @vert
:   lda water_y
    sec
    sbc #9
    sta tmp0
    clc
    adc #2
    jsr check_row
    bcs @vert
    lda tmp0
    sta py
    lda #$FC                ; -4 px/frame
    sta vyh
    lda #0
    sta vyl
    sta pwet
    lda #SFX_JUMP
    jmp sfx_play
@vert:
    lda pad
    and #BTN_UP
    bne @up
    lda pad
    and #BTN_DOWN
    bne @down
    lda frame_count         ; buoyancy
    and #1
    beq @r
@up:
    lda py
    clc
    adc #8
    cmp water_y
    beq @r
    bcc @r
    lda py
    clc
    adc #2
    jsr check_row
    bcs @r
    dec py
    rts
@down:
    lda py
    clc
    adc #16
    jsr check_row
    bcs @r
    inc py
@r: rts

drop_embers:
    lda carried
    beq @r
    ldx #3
@l: lda e_state,x
    cmp #1
    bne :+
    lda #0
    sta e_state,x
:   dex
    bpl @l
    lda #0
    sta carried
    inc hud_dirty
    lda #SFX_FIZZ
    jmp sfx_play
@r: rts

kill_player:
    lda pstate
    bne @r
    lda #P_DYING
    sta pstate
    lda #45
    sta timer
    lda #SFX_DEATH
    jmp sfx_play
@r: rts

; Hazards, ember pickup and the beacon door.
player_touch:
    lda px
    clc
    adc #8
    tax
    lda py
    clc
    adc #10
    tay
    jsr get_type
    cmp #T_HAZ
    beq @die
    lda px
    clc
    adc #8
    tax
    lda py
    clc
    adc #15
    tay
    jsr get_type
    cmp #T_HAZ
    bne :+
@die:
    jmp kill_player
:   lda pwet
    beq :+
    rts
:   ldx e_count
    dex
@e: lda e_state,x
    bne @ne
    lda e_y,x
    clc
    adc #4
    cmp water_y
    bcs @ne
    lda px
    clc
    adc #4
    sec
    sbc e_x,x
    bcs :+
    eor #$FF
    adc #1
:   cmp #10
    bcs @ne
    lda py
    clc
    adc #4
    sec
    sbc e_y,x
    bcs :+
    eor #$FF
    adc #1
:   cmp #12
    bcs @ne
    lda #1
    sta e_state,x
    inc carried
    inc hud_dirty
    lda #SFX_PICKUP
    jsr sfx_play
@ne:
    dex
    bpl @e
    lda carried
    beq @r
    lda py
    cmp door_y
    bne @r
    lda px
    sec
    sbc door_x
    bcs :+
    eor #$FF
    adc #1
:   cmp #9
    bcs @r
    ldx #3
@b: lda e_state,x
    cmp #1
    bne :+
    lda #2
    sta e_state,x
    inc banked
:   dex
    bpl @b
    lda #0
    sta carried
    inc hud_dirty
    lda banked
    cmp e_count
    beq @clear
    lda #SFX_BANK
    jmp sfx_play
@clear:
    lda #P_CLEAR
    sta pstate
    lda #110
    sta timer
    lda #SFX_CLEAR
    jsr sfx_play
    jmp light_door_lamp
@r: rts

; --------------------------------------------------------------------- tide
tide_update:
    lda pstate
    bne @move
    lda storm
    beq @bell
    dec storm_t             ; storm rooms: the sea moves by itself
    bne @move
    lda #STORM_HOLD
    sta storm_t
    inc storm_ph
    lda storm_ph
    and #3
    tax
    lda storm_seq,x
    sta tide_level
    inc hud_dirty
    lda #5
    sta flash
    lda #SFX_THUNDER
    jsr sfx_play
    jmp @move
@bell:
    lda pad_new
    and #BTN_B
    beq @move
    ldx tide_level
    lda tide_y,x
    cmp water_y
    bne @move
    lda pad
    and #BTN_DOWN
    bne @down
    cpx #2
    beq @deny
    inc tide_level
    lda #SFX_BELL_UP
    bne @rung
@down:
    cpx #0
    beq @deny
    dec tide_level
    lda #SFX_BELL_DOWN
@rung:
    jsr sfx_play
    lda #24
    sta pbell
    inc hud_dirty
    bne @move
@deny:
    lda #SFX_DENY
    jsr sfx_play
@move:
    ldx tide_level
    lda tide_y,x
    cmp water_y
    beq @done
    bcc @up
    inc water_y
    bne @done
@up:
    dec water_y
@done:
    jmp set_split

flash_update:
    lda flash
    beq @r
    dec flash
    beq @restore
    lda #$10
    bne @set
@restore:
    lda palidx
    asl a
    asl a
    asl a
    asl a
    tax
    lda island_pals,x
@set:
    sta pal_buf
    sta pal_buf+16
    inc pal_dirty
@r: rts

; ------------------------------------------------------------------ objects
; carry set if object X overlaps Pim
overlap:
    lda px
    sec
    sbc o_x,x
    bcs :+
    eor #$FF
    adc #1
:   cmp #11
    bcs @no
    lda py
    sec
    sbc o_y,x
    bcs :+
    eor #$FF
    adc #1
:   cmp #12
    bcs @no
    sec
    rts
@no:
    clc
    rts

; Step object obj_i one pixel in o_dir, turning at walls, urchins and screen
; edges; with tmp_n != 0 it also refuses to walk off a ledge.
obj_step:
    ldx obj_i
    lda o_dir,x
    bmi @left
    lda o_x,x
    cmp #240
    bcs @turn
    clc
    adc #16
    bne @chk
@left:
    lda o_x,x
    beq @turn
    sec
    sbc #1
@chk:
    sta chk_x
    lda o_y,x
    clc
    adc #8
    tay
    ldx chk_x
    jsr get_type
    ldx obj_i
    cmp #T_SOLID
    beq @turn
    cmp #T_HAZ
    beq @turn
    lda tmp_n
    beq @go
    lda o_y,x
    clc
    adc #16
    tay
    ldx chk_x
    jsr get_type
    ldx obj_i
    cmp #T_SOLID
    beq @go
    cmp #T_PLAT
    beq @go
@turn:
    lda o_dir,x
    eor #$FE
    sta o_dir,x
    rts
@go:
    lda o_x,x
    clc
    adc o_dir,x
    sta o_x,x
    rts

objects_update:
    lda #MAXOBJ-1
    sta obj_i
@loop:
    ldx obj_i
    lda o_type,x
    bne :+
    jmp @next
:   lda o_x,x
    sta d_x
    lda o_type,x
    cmp #O_RAFT
    bne :+
    jmp @raft
:   cmp #O_JELLY
    bne :+
    jmp @jelly
:
    ; ---- crab: walks when dry, sleeps when covered
    lda o_y,x
    sta d_y
    clc
    adc #10
    cmp water_y
    bcs @sleep
    lda frame_count
    and #1
    bne :+
    lda #1
    sta tmp_n
    jsr obj_step
:   ldx obj_i
    lda o_x,x
    sta d_x
    lda #F_CRAB1
    sta d_frame
    lda frame_count
    and #8
    beq :+
    lda #F_CRAB2
    sta d_frame
:   lda #1
    sta d_attr
    jsr draw16
    jmp @hit
@sleep:
    lda #F_CRAB_SLEEP
    sta d_frame
    lda #1
    sta d_attr
    jsr draw16
    jmp @next
    ; ---- raft: floats at the waterline, rests on the floor
@raft:
    lda water_y
    sec
    sbc #6
    cmp o_rest,x
    bcc :+
    lda o_rest,x
:   sta o_y,x
    sta d_y
    lda #3
    sta d_attr
    lda #SPR_RAFT_L
    jsr spr8
    jsr @r8
    lda #SPR_RAFT_M
    jsr spr8
    jsr @r8
    lda #SPR_RAFT_M
    jsr spr8
    jsr @r8
    lda #$43
    sta d_attr
    lda #SPR_RAFT_L
    jsr spr8
    jmp @next
@r8:
    lda d_x
    clc
    adc #8
    sta d_x
    rts
    ; ---- jellyfish: bobs at the surface, harmless when beached
@jelly:
    lda water_y
    clc
    adc #2
    cmp o_rest,x
    bcc @float
    beq @float
    lda o_rest,x
    sta o_y,x
    sta d_y
    lda #F_JELLY1
    sta d_frame
    lda #2
    sta d_attr
    jsr draw16
    jmp @next
@float:
    sta o_y,x
    lda frame_count
    and #1
    bne :+
    lda #0
    sta tmp_n
    jsr obj_step
:   ldx obj_i
    lda o_x,x
    sta d_x
    lda o_y,x
    sta d_y
    lda #F_JELLY1
    sta d_frame
    lda frame_count
    and #16
    beq :+
    lda #F_JELLY2
    sta d_frame
:   lda #2
    sta d_attr
    jsr draw16
@hit:
    lda pstate
    bne @next
    ldx obj_i
    jsr overlap
    bcc @next
    jsr kill_player
@next:
    dec obj_i
    bmi :+
    jmp @loop
:   rts

; ------------------------------------------------------------------ drawing
draw_player:
    lda pstate
    cmp #P_HIDDEN
    bne :+
    rts
:   cmp #P_DYING
    bne @body
    lda px
    clc
    adc #4
    sta d_x
    lda py
    clc
    adc #4
    sta d_y
    lda #1
    sta d_attr
    lda #SPR_POOF1
    ldx timer
    cpx #24
    bcs :+
    lda #SPR_POOF2
:   jmp spr8
@body:
    lda px
    sta d_x
    lda py
    sta d_y
    lda pface
    sta d_attr
    lda pwet
    beq @land
    lda #F_PIM_SWIM1
    ldx frame_count
    cpx #$80
    bcc @set
    lda frame_count
    and #16
    beq :+
    lda #F_PIM_SWIM2
    bne @set
:   lda #F_PIM_SWIM1
    bne @set
@land:
    lda pbell
    beq :+
    lda #F_PIM_BELL
    bne @set
:   lda pground
    bne :+
    lda #F_PIM_JUMP
    bne @set
:   lda pmoving
    bne :+
    lda #F_PIM_IDLE
    beq @set
:   lda frame_count
    and #8
    beq :+
    lda #F_PIM_WALK1
    bne @set
:   lda #F_PIM_WALK2
@set:
    sta d_frame
    jsr draw16
    lda carried             ; a flame over Pim's head while carrying
    beq @note
    lda px
    clc
    adc #4
    sta d_x
    lda py
    sec
    sbc #9
    sta d_y
    lda frame_count
    and #8
    asl a
    asl a
    asl a
    ora #1
    sta d_attr
    lda #SPR_EMBER
    jsr spr8
@note:
    lda pbell
    beq @r
    lda px
    clc
    adc #12
    sta d_x
    lda pbell
    lsr a
    clc
    adc py
    sec
    sbc #20
    sta d_y
    lda #0
    sta d_attr
    lda #SPR_NOTE
    jsr spr8
@r: rts

draw_embers:
    ldx e_count
    bne :+
    rts
:   dex
@l: stx obj_i
    lda e_state,x
    bne @n
    lda e_x,x
    sta d_x
    lda e_y,x
    sta d_y
    clc
    adc #4
    cmp water_y
    bcc @lit
    lda #1
    sta d_attr
    lda #SPR_EMBER_DIM
    bne @put
@lit:
    lda frame_count
    and #8
    asl a
    asl a
    asl a
    ora #1
    sta d_attr
    lda #SPR_EMBER
@put:
    jsr spr8
@n: ldx obj_i
    dex
    bpl @l
    rts

; Two specks of foam drifting along the waterline.
draw_glints:
    lda split_on
    bne :+
    rts
:   lda frame_count
    and #3
    bne :+
    inc glint_x
:   lda glint_x
    jsr @one
    lda glint_x
    clc
    adc #$80
@one:
    sta d_x
    clc
    adc #3
    tax
    ldy water_y
    jsr get_type
    cmp #T_SOLID
    beq @r
    lda water_y
    sta d_y
    lda #2
    sta d_attr
    lda #SPR_GLINT
    jmp spr8
@r: rts

scene_frame:
    jsr oam_begin
    jsr set_split
    jmp draw_glints

; ------------------------------------------------------------------- states
state_tbl:
    .word st_title-1, st_pass-1, st_card-1, st_play-1, st_end-1

; A = room number
start_room:
    sta room
    jsr room_begin
    jsr room_draw
    jsr hud_draw
    lda #S_PLAY
    sta state
    lda room
    lsr a
    lsr a
    lsr a
    tax
    lda island_song,x
    jsr music_play
    jmp ppu_on

st_play:
    lda pstate
    bne @run
    lda pad_new
    and #BTN_START
    beq :+
    lda paused
    eor #1
    sta paused
    jsr pause_text
    lda #SFX_MENU
    jsr sfx_play
:   lda paused
    beq :+
    rts
:   lda pad_new
    and #BTN_SELECT
    beq @run
    lda room
    jmp start_room
@run:
    jsr oam_begin
    jsr flash_update
    jsr tide_update
    jsr objects_update
    lda pstate
    beq @alive
    cmp #P_DYING
    beq @dying
    dec timer
    bne @draw
    inc room
    lda room
    cmp #NUM_ROOMS
    bne :+
    jmp enter_end
:   and #7
    bne :+
    jmp enter_card
:   lda room
    jmp start_room
@dying:
    dec timer
    bne @draw
    lda room
    jmp start_room
@alive:
    jsr player_update
    jsr player_touch
@draw:
    jsr draw_player
    jsr draw_embers
    jsr draw_glints
    jmp hud_flush

; Show "PAUSE  CODE xxxx" in place of the room name, or put the name back.
pause_text:
    PRINTB 6, 1, str_blank
    lda paused
    bne :+
    lda name_ptr
    sta ptr0
    lda name_ptr+1
    sta ptr0+1
    ldx #6
    ldy #1
    jmp puts_buf
:   PRINTB 6, 1, str_pause
    ldx #18
    ldy #1
    ; fall through

; queue the 4-letter code of the current room at X,Y
code_buf:
    jsr calc_addr
    ldx vb_pos
    lda addr_hi
    sta vbuf,x
    lda addr_lo
    sta vbuf+1,x
    lda #4
    sta vbuf+2,x
    lda room
    asl a
    asl a
    tay
    lda #4
    sta tmp0
@l: lda passwords,y
    clc
    adc #T_A
    sta vbuf+3,x
    inx
    iny
    dec tmp0
    bne @l
    lda #0
    sta vbuf+3,x
    inx
    inx
    inx
    stx vb_pos
    rts

enter_title:
    lda #SCENE_TITLE
    jsr room_begin
    lda #255
    jsr light_lamps
    jsr room_draw
    PRINT 8, 3, logo_row0
    PRINT 8, 4, logo_row1
    PRINT 8, 5, logo_row2
    PRINT 2, 7, str_sub
    PRINT 12, 12, str_start
    PRINT 12, 14, str_password
    lda #0
    sta menu_sel
    lda #S_TITLE
    sta state
    lda #P_HIDDEN
    sta pstate
    lda #SONG_TITLE
    jsr music_play
    jmp ppu_on

st_title:
    jsr scene_frame
    lda #32
    sta d_x
    lda #128
    sta d_y
    lda #0
    sta d_attr
    lda #F_PIM_IDLE
    ldx frame_count
    cpx #$C0
    bcc :+
    lda #F_PIM_BELL
:   sta d_frame
    jsr draw16
    lda #84
    sta d_x
    lda menu_sel
    asl a
    asl a
    asl a
    asl a
    clc
    adc #96
    sta d_y
    lda frame_count
    and #8
    asl a
    asl a
    asl a
    ora #1
    sta d_attr
    lda #SPR_EMBER
    jsr spr8
    lda pad_new
    and #(BTN_UP | BTN_DOWN | BTN_SELECT)
    beq :+
    lda menu_sel
    eor #1
    sta menu_sel
    lda #SFX_MENU
    jsr sfx_play
:   lda pad_new
    and #(BTN_START | BTN_A)
    beq @r
    lda #SFX_START
    jsr sfx_play
    lda menu_sel
    beq :+
    jmp enter_pass
:   lda #0
    sta room
    jmp enter_card
@r: rts

enter_pass:
    lda #SCENE_CARD
    jsr room_begin
    jsr room_draw
    PRINT 11, 5, str_enter
    PRINT 6, 12, str_passhelp
    lda #0
    sta pw
    sta pw+1
    sta pw+2
    sta pw+3
    sta pw_pos
    lda #S_PASS
    sta state
    lda #P_HIDDEN
    sta pstate
    jmp ppu_on

st_pass:
    jsr scene_frame
    lda pad_new
    and #BTN_RIGHT
    beq :+
    inc pw_pos
:   lda pad_new
    and #BTN_LEFT
    beq :+
    dec pw_pos
:   lda pw_pos
    and #3
    sta pw_pos
    tax
    lda pad_new
    and #BTN_UP
    beq :+
    inc pw,x
    lda pw,x
    cmp #26
    bcc :+
    lda #0
    sta pw,x
:   lda pad_new
    and #BTN_DOWN
    beq :+
    dec pw,x
    bpl :+
    lda #25
    sta pw,x
:   ldx vb_pos              ; redraw the four letters, a blank after each
    lda #$21
    sta vbuf,x
    lda #$0C
    sta vbuf+1,x
    lda #8
    sta vbuf+2,x
    ldy #0
@l: lda pw,y
    clc
    adc #T_A
    sta vbuf+3,x
    lda #T_SPACE
    sta vbuf+4,x
    inx
    inx
    iny
    cpy #4
    bne @l
    lda #0
    sta vbuf+3,x
    txa
    clc
    adc #3
    sta vb_pos
    lda pw_pos              ; cursor under the active letter
    asl a
    asl a
    asl a
    asl a
    clc
    adc #96
    sta d_x
    lda #76
    sta d_y
    lda #1
    sta d_attr
    lda #SPR_EMBER
    jsr spr8
    lda pad_new
    and #BTN_B
    beq :+
    jmp enter_title
:   lda pad_new
    and #(BTN_START | BTN_A)
    beq @r
    ldx #0
    ldy #0
@c: lda passwords,x
    cmp pw
    bne @n
    lda passwords+1,x
    cmp pw+1
    bne @n
    lda passwords+2,x
    cmp pw+2
    bne @n
    lda passwords+3,x
    cmp pw+3
    bne @n
    sty room
    lda #SFX_START
    jsr sfx_play
    jmp enter_card
@n: inx
    inx
    inx
    inx
    iny
    cpy #NUM_ROOMS
    bne @c
    lda #SFX_DENY
    jsr sfx_play
@r: rts

; Island card for the island that `room` belongs to.
enter_card:
    lda #SCENE_CARD
    jsr room_begin
    lda room
    lsr a
    lsr a
    lsr a
    sta palidx
    jsr light_lamps
    jsr room_draw
    lda palidx
    cmp #4
    beq @last
    PRINT 9, 3, str_island
    lda palidx
    clc
    adc #T_0+1
    sta PPUDATA
    PRINT 17, 3, str_of4
@last:
    lda palidx
    asl a
    tax
    lda island_names,x
    sta ptr0
    lda island_names+1,x
    sta ptr0+1
    ldx #9
    ldy #5
    jsr puts_xy
    PRINT 11, 7, str_code
    ldx #16
    ldy #7
    jsr code_buf
    lda #S_CARD
    sta state
    lda #P_HIDDEN
    sta pstate
    lda #200
    sta timer
    ldx palidx
    lda island_song,x
    jsr music_play
    jmp ppu_on

st_card:
    jsr scene_frame
    lda pad_new
    and #(BTN_START | BTN_A)
    bne :+
    dec timer
    bne @r
:   lda room
    jmp start_room
@r: rts

enter_end:
    lda #SCENE_CARD
    jsr room_begin
    lda #4
    jsr light_lamps
    jsr room_draw
    PRINT 3, 3, str_end1
    PRINT 4, 5, str_end2
    PRINT 5, 8, str_end3
    lda #S_END
    sta state
    lda #P_HIDDEN
    sta pstate
    lda #SONG_ENDING
    jsr music_play
    jmp ppu_on

st_end:
    jsr scene_frame
    lda frame_count         ; Pim swims home across the bay
    sta d_x
    lda water_y
    sec
    sbc #8
    sta d_y
    lda #0
    sta d_attr
    lda #F_PIM_SWIM1
    ldx frame_count
    cpx #$80
    bcc :+
    lda #F_PIM_SWIM2
:   sta d_frame
    lda d_x
    cmp #240
    bcs :+
    jsr draw16
:   lda pad_new
    and #BTN_START
    beq @r
    jmp enter_title
@r: rts

; ===================================================================== data
.segment "RODATA"

str_dash:     .byte "-", $FF
str_tide:     .byte "TIDE", $FF
str_blank:    .byte "                        ", $FF
str_pause:    .byte "PAUSE  CODE ", $FF
str_sub:      .byte "THE LAST LIGHTHOUSE", $FF
str_start:    .byte "START", $FF
str_password: .byte "PASSWORD", $FF
str_enter:    .byte "ENTER CODE", $FF
str_passhelp: .byte "A: OK      B: BACK", $FF
str_island:   .byte "ISLAND ", $FF
str_of4:      .byte " OF 4", $FF
str_code:     .byte "CODE", $FF
str_end1:     .byte "ALL THE LIGHTS BURN AGAIN.", $FF
str_end2:     .byte "THE SEA IS SAFE TONIGHT.", $FF
str_end3:     .byte "THANK YOU FOR PLAYING!", $FF
name_0:       .byte "DRIFTWOOD COVE", $FF
name_1:       .byte " JELLY SHOALS", $FF
name_2:       .byte " CORAL GATES", $FF
name_3:       .byte "  STORMBREAK", $FF
name_4:       .byte "THE LAST LIGHT", $FF
island_names: .word name_0, name_1, name_2, name_3, name_4
island_song:  .byte SONG_SHANTY, SONG_SHOALS, SONG_SHANTY, SONG_STORM, SONG_STORM
storm_seq:    .byte 0, 1, 2, 1
icon_tbl:     .byte T_ICON_EMPTY, T_ICON_CARRY, T_ICON_BANK

; background palettes per island: sky/water, stone/moss, wood/sand, lighthouse.
; Entry 1 of the first and third palette must match (the water colour).
island_pals:
    .byte $0C,$1C,$2C,$30, $0C,$00,$10,$1A, $0C,$1C,$17,$37, $0C,$16,$30,$38
    .byte $01,$11,$21,$30, $01,$00,$10,$2A, $01,$11,$17,$37, $01,$16,$30,$38
    .byte $03,$12,$22,$30, $03,$00,$10,$2A, $03,$12,$17,$37, $03,$15,$30,$38
    .byte $0F,$0C,$1C,$30, $0F,$00,$10,$0B, $0F,$0C,$07,$17, $0F,$06,$10,$28
    .byte $0F,$0C,$1C,$30, $0F,$00,$10,$1A, $0F,$0C,$17,$37, $0F,$16,$30,$38
sprite_pals:
    .byte $0F,$0F,$28,$17, $0F,$16,$27,$30, $0F,$14,$25,$30, $0F,$0F,$17,$27

.include "levels.inc"
.include "sound.s"
