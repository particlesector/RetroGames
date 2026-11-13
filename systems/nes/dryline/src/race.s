; The race screen: cars, physics and drawing.

.segment "BSS"
c_xl:   .res NCARS          ; position, 8.8 pixels
c_xh:   .res NCARS
c_yl:   .res NCARS
c_yh:   .res NCARS
c_vxl:  .res NCARS          ; velocity, signed 8.8 pixels per frame
c_vxh:  .res NCARS
c_vyl:  .res NCARS
c_vyh:  .res NCARS
c_ang:  .res NCARS          ; heading, 256 steps to a full turn, 0 = east, clockwise
c_spd:  .res NCARS          ; engine speed in 1/64 pixel per frame
c_in:   .res NCARS          ; controls, as controller bits
c_surf: .res NCARS          ; surface under the car: 0 road, 1 grass, 2 gravel
c_slip: .res NCARS          ; how hard the car is sliding this frame

.segment "CODE"

; A = circuit number
race_begin:
    jsr load_track
    PRINT 1, 1, str_title
    lda #<track_name
    sta ptr0
    lda #>track_name
    sta ptr0+1
    ldx #1
    ldy #2
    jsr puts_xy
    jsr cars_init
    lda #1
    sta split_on
    jmp ppu_on

race_frame:
    jsr oam_begin
    lda pad
    sta c_in
    lda #NCARS-1
    sta car
@l: jsr car_update
    jsr car_draw
    dec car
    bpl @l
    rts

.segment "RACE0"

cars_init:
    ldx #NCARS-1
@l: txa
    asl a
    tay
    lda grid_xy,y
    sta c_xh,x
    lda grid_xy+1,y
    sta c_yh,x
    lda grid_ang
    sta c_ang,x
    lda #0
    sta c_xl,x
    sta c_yl,x
    sta c_vxl,x
    sta c_vxh,x
    sta c_vyl,x
    sta c_vyh,x
    sta c_spd,x
    sta c_in,x
    sta c_surf,x
    sta c_slip,x
    dex
    bpl @l
    rts

; A * X, unsigned -> prod (16 bits), by the quarter-square method.
mul8:
    sta m_a
    stx m_b
    sec
    sbc m_b
    bcs :+
    eor #$FF
    adc #1
:   tay
    lda m_a
    clc
    adc m_b
    tax
    bcs @hi
    lda sq_lo,x
    sec
    sbc sq_lo,y
    sta prod
    lda sq_hi,x
    sbc sq_hi,y
    sta prod+1
    rts
@hi:
    lda sq2_lo,x
    sec
    sbc sq_lo,y
    sta prod
    lda sq2_hi,x
    sbc sq_hi,y
    sta prod+1
    rts

; A = angle -> prod = sin(angle) * speed of the current car, signed 8.8 pixels per frame
trig_spd:
    tay
    lda sin_tbl,y
    sta sgn
    bpl :+
    eor #$FF
    clc
    adc #1
:   pha
    ldx car
    lda c_spd,x
    tax
    pla
    jsr mul8
    ldx #5
@s: lsr prod+1
    ror prod
    dex
    bne @s
    lda sgn
    bpl @r
    sec
    lda #0
    sbc prod
    sta prod
    lda #0
    sbc prod+1
    sta prod+1
@r: rts

; Pull velocity component bv towards prod by 1/2^gshift of the difference.
; The size of the difference is added to the current car's slip.
blend:
    lda prod
    sec
    sbc bv
    sta bd
    lda prod+1
    sbc bv+1
    sta bd+1
    bpl @pos
    sec
    lda #0
    sbc bd
    sta tmp0
    lda #0
    sbc bd+1
    jmp @mag
@pos:
    lda bd
    sta tmp0
    lda bd+1
@mag:
    cmp #2                  ; 2 pixels a frame or more: saturate
    bcs @sat
    lsr a
    ror tmp0
    lsr tmp0                ; tmp0 = |difference| in 1/64 pixel
    lda tmp0
    bcc @add
@sat:
    lda #255
@add:
    ldx car
    clc
    adc c_slip,x
    bcc :+
    lda #255
:   sta c_slip,x
    ldy gshift
@s: lda bd+1
    cmp #$80
    ror bd+1
    ror bd
    dey
    bne @s
    lda bv
    clc
    adc bd
    sta bv
    lda bv+1
    adc bd+1
    sta bv+1
    rts

; X = pixel x, Y = pixel y -> A = surface type 0-3
get_surface:
    tya
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    clc
    adc #>surface
    sta ptr1+1
    tya
    and #$3C
    asl a
    asl a
    sta tmp0
    txa
    lsr a
    lsr a
    lsr a
    lsr a
    ora tmp0
    sta ptr1
    txa
    lsr a
    lsr a
    and #3
    tax
    ldy #0
    lda (ptr1),y
    cpx #0
    beq @m
@s: lsr a
    lsr a
    dex
    bne @s
@m: and #3
    rts

; Advance the car in `car` by one frame from its controls in c_in.
car_update:
    ldx car
    lda #0
    sta c_slip,x
    ; steering needs some speed
    lda c_spd,x
    cmp #16
    bcc @speed
    lda c_in,x
    and #BTN_LEFT
    beq :+
    lda c_ang,x
    sec
    sbc #3
    sta c_ang,x
:   lda c_in,x
    and #BTN_RIGHT
    beq @speed
    lda c_ang,x
    clc
    adc #3
    sta c_ang,x
@speed:
    ldy c_surf,x
    lda surf_max,y
    sta tmp1
    lda c_in,x
    and #BTN_B
    beq @nobrake
    lda c_spd,x
    sec
    sbc #4
    bcs :+
    lda #0
:   sta c_spd,x
    jmp @vel
@nobrake:
    lda c_in,x
    and #BTN_A
    beq @coast
    lda c_spd,x
    cmp #96
    bcs @top
    adc #3                  ; brisk up to 1.5 pixels a frame
    bne @set
@top:
    cmp #255
    beq @cap
    adc #0                  ; then +1 a frame (the cmp left carry set)
@set:
    sta c_spd,x
    jmp @cap
@coast:
    lda frame_count
    and #1
    bne @cap
    lda c_spd,x
    beq @cap
    dec c_spd,x
@cap:
    lda c_spd,x
    cmp tmp1
    bcc @vel
    beq @vel
    sbc #3
    cmp tmp1
    bcs :+
    lda tmp1
:   sta c_spd,x
@vel:
    ldy c_surf,x
    lda surf_grip,y
    sta gshift
    ; x
    lda c_ang,x
    clc
    adc #64
    jsr trig_spd
    ldx car
    lda c_vxl,x
    sta bv
    lda c_vxh,x
    sta bv+1
    jsr blend
    ldx car
    lda bv
    sta c_vxl,x
    lda bv+1
    sta c_vxh,x
    ; y
    lda c_ang,x
    jsr trig_spd
    ldx car
    lda c_vyl,x
    sta bv
    lda c_vyh,x
    sta bv+1
    jsr blend
    ldx car
    lda bv
    sta c_vyl,x
    lda bv+1
    sta c_vyh,x
    ; move
    lda c_xl,x
    clc
    adc c_vxl,x
    sta nxl
    lda c_xh,x
    adc c_vxh,x
    sta nxh
    lda c_yl,x
    clc
    adc c_vyl,x
    sta nyl
    lda c_yh,x
    adc c_vyh,x
    sta nyh
    lda nxh
    cmp #9
    bcc @hit
    cmp #247
    bcs @hit
    lda nyh
    cmp #TOP+8
    bcc @hit
    cmp #232
    bcs @hit
    ldx nxh
    ldy nyh
    jsr get_surface
    cmp #3
    beq @hit
    ldx car
    sta c_surf,x
    lda nxl
    sta c_xl,x
    lda nxh
    sta c_xh,x
    lda nyl
    sta c_yl,x
    lda nyh
    sta c_yh,x
    rts
@hit:                       ; solid: stay put, bounce back at half speed
    ldx car
    sec
    lda #0
    sbc c_vxl,x
    sta c_vxl,x
    lda #0
    sbc c_vxh,x
    cmp #$80
    ror a
    sta c_vxh,x
    ror c_vxl,x
    sec
    lda #0
    sbc c_vyl,x
    sta c_vyl,x
    lda #0
    sbc c_vyh,x
    cmp #$80
    ror a
    sta c_vyh,x
    ror c_vyl,x
    lsr c_spd,x
    rts

car_draw:
    ldx car
    lda c_ang,x
    clc
    adc #4
    lsr a
    lsr a
    lsr a
    tay
    lda heading_frame,y
    sta d_frame
    lda heading_flip,y
    ora car
    sta d_attr
    lda c_xh,x
    sec
    sbc #8
    sta tmp0
    lda c_yh,x
    sec
    sbc #8
    sta tmp1
    lda #0
    sta tmp3
    lda d_attr
    and #$40
    beq :+
    inc tmp3
:   lda d_attr
    bpl :+
    lda tmp3
    ora #2
    sta tmp3
:   lda #0
    sta tmp2
@l: lda tmp2
    eor tmp3
    clc
    adc d_frame
    tay
    lda car_tiles,y
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
    rts

surf_max:  .byte 160, 80, 48, 0     ; top speed on road, grass, gravel
surf_grip: .byte 2, 3, 2, 2         ; velocity follows heading by 1/2^n per frame

.segment "RODATA"
str_title: .byte "DRYLINE GRAND PRIX", $FF
