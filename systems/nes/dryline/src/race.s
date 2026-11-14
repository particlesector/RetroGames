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
c_steer:.res NCARS          ; heading change per frame, signed
c_wp:   .res NCARS          ; next waypoint gate to cross
c_lap:  .res NCARS          ; laps started (0 on the grid)
c_pos:  .res NCARS          ; race position 1-4
c_fin:  .res NCARS          ; finishing order, 0 while racing
c_stuck:.res NCARS          ; frames spent nearly stationary
c_skill:.res NCARS          ; rivals: share of the speed limit they dare, /256
race_state: .res 1          ; 0 grid, 1 racing, 2 player finished
race_timer: .res 1
fin_count:  .res 1
hud_lap:    .res 1          ; what the HUD currently shows
hud_pos:    .res 1
hud_msg:    .res 1
ai_dx:      .res 1
ai_dy:      .res 1
ai_c:       .res 2
race_time:  .res 2          ; frames since the start

.segment "CODE"

RS_GRID = 0
RS_RACE = 1
RS_DONE = 2

; A = circuit number
race_begin:
    jsr load_track
    jsr cars_init
    jsr weather_init
    lda #RS_GRID
    sta race_state
    lda #200
    sta race_timer
    lda #0
    sta fin_count
    sta race_time
    sta race_time+1
    lda #$FF
    sta hud_lap
    sta hud_pos
    sta hud_msg
    lda #1
    sta split_on
    jmp ppu_on

race_frame:
    jsr oam_begin
    lda race_state
    bne @go
    dec race_timer          ; on the grid: nobody moves until the lights go out
    bne @draw
    lda #RS_RACE
    sta race_state
    bne @draw
@go:
    inc race_time
    bne :+
    inc race_time+1
:   jsr weather_tick
    lda #NCARS-1
    sta car
@l: ldx car
    bne @rival
    lda demo                ; attract mode and tests: car 0 drives itself too
    bne @rival
    jsr player_input
    jmp @upd
@rival:
    jsr ai_think
@upd:
    jsr car_update
    jsr car_gate
    dec car
    bpl @l
    jsr collide
    jsr rank
    lda race_state
    cmp #RS_DONE
    bne @draw
    lda pad_new
    and #BTN_START
    beq @draw
    lda cur_track
    jmp race_begin
@draw:
    lda #NCARS-1
    sta car
@d: jsr car_draw
    dec car
    bpl @d
    jsr rain_draw
    jmp hud_update

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
    sta c_steer,x
    sta c_wp,x
    sta c_lap,x
    sta c_fin,x
    sta c_stuck,x
    lda skills,x
    sta c_skill,x
    txa
    clc
    adc #1
    sta c_pos,x
    dex
    bpl @l
    rts

skills: .byte 255, 250, 238, 226

player_input:
    lda pad
    sta c_in
    ldy #0
    and #BTN_LEFT
    beq :+
    ldy #$FD
:   lda pad
    and #BTN_RIGHT
    beq :+
    ldy #3
:   sty c_steer
    rts

; A * X, both signed -> prod, signed 16 bits
smul:
    ldy #0
    cmp #$80
    bcc :+
    eor #$FF
    adc #0
    iny
:   pha
    txa
    cmp #$80
    bcc :+
    eor #$FF
    adc #0
    iny
:   tax
    pla
    sty sgn
    jsr mul8
    lda sgn
    lsr a
    bcc @r
    sec
    lda #0
    sbc prod
    sta prod
    lda #0
    sbc prod+1
    sta prod+1
@r: rts

; A rival decides its controls: steer towards a waypoint a little way ahead and
; hold the speed limit of the next gate. The turn direction is the sign of the
; cross product of the car's heading and the direction to the target.
ai_think:
    jsr ai_pit_decide
    ldx car
    lda c_pit,x
    beq @line
    lda pit_rect            ; pitting: aim for the middle of the box
    clc
    adc pit_rect+2
    ror a
    sec
    sbc c_xh,x
    sta ai_dx
    lda pit_rect+1
    clc
    adc pit_rect+3
    ror a
    sec
    sbc c_yh,x
    sta ai_dy
    jmp @steer
@line:
    lda c_spd,x
    asl a
    rol a
    rol a
    and #3
    clc
    adc #1
    adc c_wp,x
    cmp #MAXWP
    bcc :+
    sbc #MAXWP
:   tay
    lda wp_x,y
    sec
    sbc c_xh,x
    sta ai_dx
    lda wp_y,y
    sec
    sbc c_yh,x
    sta ai_dy
@steer:
    lda c_ang,x
    clc
    adc #64
    tay
    lda sin_tbl,y
    ldx ai_dy
    jsr smul
    lda prod
    sta ai_c
    lda prod+1
    sta ai_c+1
    ldx car
    ldy c_ang,x
    lda sin_tbl,y
    ldx ai_dx
    jsr smul
    lda ai_c
    sec
    sbc prod
    sta ai_c
    lda ai_c+1
    sbc prod+1
    sta ai_c+1
    php
    bpl :+
    sec
    lda #0
    sbc ai_c
    sta ai_c
    lda #0
    sbc ai_c+1
    sta ai_c+1
:   ldy #3
    lda ai_c+1
    cmp #3
    bcs @rate
    dey
    cmp #1
    bcs @rate
    dey
    lda ai_c
    cmp #64
    bcs @rate
    dey
@rate:
    ldx car
    tya
    plp
    bpl :+
    eor #$FF
    clc
    adc #1
:   sta c_steer,x
    ; speed: the gate's limit, scaled by nerve and by what the tyres will take
    ldy c_wp,x
    lda wp_s,y
    ldx car
    pha
    lda c_skill,x
    tax
    pla
    jsr mul8
    ldx car
    ldy c_cond,x
    lda cond_ai,y
    ldx prod+1
    jsr mul8
    ldx car
    lda c_pit,x
    beq @lim
    lda #52                 ; pit approach: slow, and stop once inside the box
    cmp prod+1
    bcs :+
    sta prod+1
:   lda c_arm,x
    beq @lim
    lda c_xh,x
    cmp pit_rect
    bcc @lim
    cmp pit_rect+2
    bcs @lim
    lda c_yh,x
    cmp pit_rect+1
    bcc @lim
    cmp pit_rect+3
    bcs @lim
    lda #0
    sta prod+1
@lim:
    lda c_spd,x
    cmp prod+1
    bcc @gas
    sbc prod+1
    cmp #8
    bcc @coast
    lda #BTN_B
    bne @set
@coast:
    lda #0
    beq @set
@gas:
    lda #BTN_A
@set:
    sta c_in,x
    ; a rival that has been stationary for two seconds is put back on the line
    lda c_spd,x
    cmp #12
    bcs @moving
    inc c_stuck,x
    lda c_stuck,x
    cmp #120
    bcc @r
    ldy c_wp,x
    bne :+
    ldy #MAXWP
:   dey
    lda wp_x,y
    sta c_xh,x
    lda wp_y,y
    sta c_yh,x
    lda wp_a,y
    sta c_ang,x
    lda #0
    sta c_vxl,x
    sta c_vxh,x
    sta c_vyl,x
    sta c_vyh,x
@moving:
    lda #0
    sta c_stuck,x
@r: rts

; Has the car crossed its next gate? A gate is the line through a waypoint at
; right angles to the racing line; crossing means being on its far side.
car_gate:
    ldx car
    ldy c_wp,x
    lda c_xh,x
    sec
    sbc wp_x,y
    sta ai_dx
    bcs :+
    eor #$FF
    adc #1
:   cmp #48
    bcc @far5_334
    jmp @r
@far5_334:
    lda c_yh,x
    sec
    sbc wp_y,y
    sta ai_dy
    bcs :+
    eor #$FF
    adc #1
:   cmp #48
    bcs @r
    lda wp_a,y
    pha
    clc
    adc #64
    tay
    lda sin_tbl,y
    ldx ai_dx
    jsr smul
    lda prod
    sta ai_c
    lda prod+1
    sta ai_c+1
    pla
    tay
    lda sin_tbl,y
    ldx ai_dy
    jsr smul
    lda ai_c
    clc
    adc prod
    lda ai_c+1
    adc prod+1
    bmi @r
    ldx car
    lda c_wp,x
    bne :+
    inc c_lap,x             ; gate 0 is the start line
    lda c_lap,x
    cmp track_laps
    bcc :+
    beq :+
    lda c_fin,x
    bne :+
    inc fin_count
    lda fin_count
    sta c_fin,x
    cpx #0
    bne :+
    lda #RS_DONE
    sta race_state
:   inc c_wp,x
    lda c_wp,x
    cmp #MAXWP
    bcc @r
    lda #0
    sta c_wp,x
@r: rts

; Cars that overlap are pushed apart and trade velocities.
collide:
    ldx #0
@i: txa
    tay
    iny
@j: lda c_xh,x
    sec
    sbc c_xh,y
    bcs :+
    eor #$FF
    adc #1
:   cmp #8
    bcc @far4_405
    jmp @next
@far4_405:
    lda c_yh,x
    sec
    sbc c_yh,y
    bcs :+
    eor #$FF
    adc #1
:   cmp #8
    bcc @far3_413
    jmp @next
@far3_413:
    lda c_xh,x              ; one pixel apart on each axis
    cmp c_xh,y
    bcc :+
    inc c_xh,x
    lda c_xh,y
    sbc #1
    sta c_xh,y
    jmp @py
:   dec c_xh,x
    lda c_xh,y
    adc #1
    sta c_xh,y
@py:
    lda c_yh,x
    cmp c_yh,y
    bcc :+
    inc c_yh,x
    lda c_yh,y
    sbc #1
    sta c_yh,y
    jmp @swap
:   dec c_yh,x
    lda c_yh,y
    adc #1
    sta c_yh,y
@swap:
    lda c_vxl,x
    pha
    lda c_vxl,y
    sta c_vxl,x
    pla
    sta c_vxl,y
    lda c_vxh,x
    pha
    lda c_vxh,y
    sta c_vxh,x
    pla
    sta c_vxh,y
    lda c_vyl,x
    pha
    lda c_vyl,y
    sta c_vyl,x
    pla
    sta c_vyl,y
    lda c_vyh,x
    pha
    lda c_vyh,y
    sta c_vyh,x
    pla
    sta c_vyh,y
    lda c_spd,x             ; both leave at their average speed
    lsr a
    sta tmp0
    lda c_spd,y
    lsr a
    clc
    adc tmp0
    sta c_spd,x
    sta c_spd,y
@next:
    iny
    cpy #NCARS
    beq @far2_476
    jmp @j
@far2_476:
    inx
    cpx #NCARS-1
    beq @far1_479
    jmp @i
@far1_479:
    rts

; Positions: finishers keep their order, the rest are ranked by lap then gate.
rank:
    ldx #NCARS-1
@i: lda c_fin,x
    beq :+
    sta c_pos,x
    bne @nx
:   lda #1
    sta tmp0
    ldy #NCARS-1
@j:
    sty tmp1
    cpx tmp1
    beq @nj
    lda c_fin,y
    bne @ahead
    lda c_lap,y
    cmp c_lap,x
    bcc @nj
    bne @ahead
    lda c_wp,y              ; same lap: gate 0 means "about to complete it", so rotate by one
    sec
    sbc #1
    sta tmp2
    lda c_wp,x
    sec
    sbc #1
    cmp tmp2
    bcc @ahead
    bne @nj
    stx tmp3                ; level: the lower-numbered car is ahead
    cpy tmp3
    bcs @nj
@ahead:
    inc tmp0
@nj:
    dey
    bpl @j
    lda tmp0
    sta c_pos,x
@nx:
    dex
    bpl @i
    rts

; Redraw the parts of the HUD that changed.
hud_update:
    lda c_lap
    bne :+
    lda #1
:   cmp track_laps
    bcc :+
    lda track_laps
:   cmp hud_lap
    bne @redraw
    lda c_pos
    cmp hud_pos
    bne @redraw
    jmp @msg
@redraw:
    sta tmp0
    lda c_lap
    bne :+
    lda #1
:   cmp track_laps
    bcc :+
    lda track_laps
:   sta hud_lap
    lda c_pos
    sta hud_pos
    ldx vb_pos
    lda #$20
    sta vbuf,x
    lda #$21
    sta vbuf+1,x
    lda #14
    sta vbuf+2,x
    ldy #0
@t: lda str_hud,y
    sta vbuf+3,x
    inx
    iny
    cpy #14
    bne @t
    lda #0
    sta vbuf+3,x
    lda hud_lap
    clc
    adc #T_0
    sta vbuf+3-14+4,x
    lda track_laps
    clc
    adc #T_0
    sta vbuf+3-14+6,x
    lda hud_pos
    clc
    adc #T_0
    sta vbuf+3-14+13,x
    txa
    clc
    adc #3
    sta vb_pos
@msg:
    ldy #0                  ; message: which light, or the flag
    lda race_state
    cmp #RS_DONE
    bne :+
    ldy #5
    bne @have
:   cmp #RS_RACE
    bne :+
    ldy #4
    lda race_time+1
    bne @blank
    lda race_time
    cmp #90
    bcc @have
@blank:
    ldy #0
    beq @have
:   lda race_timer
    cmp #150
    bcs @have
    iny
    cmp #100
    bcs @have
    iny
    cmp #50
    bcs @have
    iny
@have:
    cpy hud_msg
    beq @r
    sty hud_msg
    tya
    asl a
    asl a
    asl a
    tay
    ldx vb_pos
    lda #$20
    sta vbuf,x
    lda #$41
    sta vbuf+1,x
    lda #8
    sta vbuf+2,x
    lda #8
    sta tmp0
@m: lda str_msgs,y
    sta vbuf+3,x
    inx
    iny
    dec tmp0
    bne @m
    lda #0
    sta vbuf+3,x
    txa
    clc
    adc #3
    sta vb_pos
@r: rts

str_hud:  .byte "LAP 1-1  POS 1"
str_msgs: .byte "        ", "READY   ", "READY  .", "READY ..", "GO!     ", "FINISH! "

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

; Pull velocity component bv towards prod by gval/256 of the difference.
; The size of the difference is added to the current car's slip.
blend:
    lda prod
    sec
    sbc bv
    sta bd
    lda prod+1
    sbc bv+1
    sta bd+1
    sta sgn
    bpl :+
    sec
    lda #0
    sbc bd
    sta bd
    lda #0
    sbc bd+1
    sta bd+1
:   lda bd+1                ; slip: |difference| in 1/64 pixel, saturating
    cmp #1
    bcs @sat
    lda bd
    lsr a
    lsr a
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
    lda bd                  ; |difference| * gval / 256
    ldx gval
    jsr mul8
    lda prod+1
    bne :+
    lda bd+1                ; too small to scale: close the gap outright so cars come fully to rest
    bne :+
    lda bd
:   sta tmp0
    lda #0
    sta tmp1
    lda bd+1
    beq :+
    ldx gval
    jsr mul8
    lda prod
    clc
    adc tmp0
    sta tmp0
    lda prod+1
    adc #0
    sta tmp1
:   lda sgn
    bmi @neg
    lda bv
    clc
    adc tmp0
    sta bv
    lda bv+1
    adc tmp1
    sta bv+1
    rts
@neg:
    lda bv
    sec
    sbc tmp0
    sta bv
    lda bv+1
    sbc tmp1
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
    jsr service_tick
    bcc :+
    rts
:   jsr car_cond
    ldx car
    lda #0
    sta c_slip,x
    lda c_spd,x             ; steering needs some speed
    cmp #16
    bcc @speed
    lda c_ang,x
    clc
    adc c_steer,x
    sta c_ang,x
@speed:
    ldy c_surf,x
    lda surf_max,y
    cpy #0
    bne :+
    ldy c_cond,x            ; on tarmac the tyres and the wet decide, less a little for wear
    lda c_wear,x
    lsr a
    lsr a
    lsr a
    lsr a
    sta tmp1
    lda cond_max,y
    sec
    sbc tmp1
:   sta tmp1
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
    clc
    adc #1                  ; then +1 a frame
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
    cpy #0
    bne :+
    ldy c_cond,x
    lda c_wear,x
    lsr a
    lsr a
    lsr a
    sta tmp0
    lda cond_grip,y
    sec
    sbc tmp0
:   sta gval
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
    jsr car_wear
    jmp pit_check
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
surf_grip: .byte 64, 36, 56, 64      ; share of the velocity error corrected per frame, /256

.segment "RODATA"
