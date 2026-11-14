; Weather, the dry line, tyres and pit stops.

W_DRY = 0
W_RAIN = 1
W_DRYING = 2
SERVICE_FRAMES = 150
DRYING_SECONDS = 14
VB_LIMIT = 68               ; leave room in the VRAM queue for the HUD

.segment "BSS"
weather:    .res 1
wx_sec:     .res 1          ; seconds since the lights went out
wx_frames:  .res 1
dry_timer:  .res 1
sweep_on:   .res 1          ; after the track dries, tiles are put back to plain tarmac a few per frame
sweep_ptr:  .res 2
c_tyre:     .res NCARS      ; 0 slick, 1 wet
c_wear:     .res NCARS      ; 0 new .. 255 gone
c_wacc:     .res NCARS
c_cond:     .res NCARS      ; tyre * 3 + wetness under the car (0 dry, 1 damp, 2 wet)
c_tlo:      .res NCARS      ; the tile the car was last on
c_thi:      .res NCARS
c_serv:     .res NCARS      ; frames of pit service left
c_want:     .res NCARS      ; tyre being fitted
c_arm:      .res NCARS      ; 1 once the car has left the pit box
c_pit:      .res NCARS      ; rival is heading for the pits
c_pitlap:   .res NCARS      ; lap on which a rival last made its pit decision

.segment "RACE1"

weather_init:
    lda #W_DRY
    sta weather
    lda #0
    sta wx_sec
    sta wx_frames
    sta sweep_on
    lda rng
    ora rng+1
    bne :+
    inc rng
:   ldx #NCARS-1
@l: lda #0
    sta c_tyre,x
    sta c_wear,x
    sta c_wacc,x
    sta c_cond,x
    sta c_serv,x
    sta c_pit,x
    sta c_tlo,x
    sta c_thi,x
    lda #$FF
    sta c_pitlap,x
    lda #1
    sta c_arm,x
    dex
    bpl @l
    rts

rnd:
    lda rng
    asl a
    rol rng+1
    bcc :+
    eor #$2D
:   sta rng
    eor rng+1
    rts

set_palette:                ; A = 0 fair, 16 rain
    tax
    ldy #0
@l: lda pal_fair,x
    sta pal_buf,y
    inx
    iny
    cpy #16
    bne @l
    lda pal_buf
    sta pal_buf+16
    inc pal_dirty
    rts

; Once a frame while racing.
weather_tick:
    inc wx_frames
    lda wx_frames
    cmp #60
    bcc @frame
    lda #0
    sta wx_frames
    lda wx_sec
    cmp #255
    beq :+
    inc wx_sec
:   lda weather
    bne @notdry
    lda rain_at             ; dry: has the rain arrived?
    beq @frame
    cmp wx_sec
    bne @frame
    lda #W_RAIN
    sta weather
    lda #16
    jsr set_palette
    jmp @frame
@notdry:
    cmp #W_RAIN
    bne @drying
    lda wx_sec
    cmp rain_end
    bcc @frame
    lda #W_DRYING
    sta weather
    lda #DRYING_SECONDS
    sta dry_timer
    bne @frame
@drying:
    dec dry_timer
    bne @frame
    lda #W_DRY
    sta weather
    lda #0
    jsr set_palette
    lda #1
    sta sweep_on
    lda #<wetmap
    sta sweep_ptr
    lda #>wetmap
    sta sweep_ptr+1
@frame:
    lda weather
    beq @sweep
    cmp #W_RAIN
    bne @dry
    jsr rnd_tile            ; rain puts water back on three tiles a frame
    jsr tile_wet
    jsr rnd_tile
    jsr tile_wet
    jsr rnd_tile
    jmp tile_wet
@dry:
    lda #5                  ; sun and wind dry five
    sta tmp3
:   jsr rnd_tile
    jsr tile_dry
    dec tmp3
    bne :-
    rts
@sweep:
    lda sweep_on
    beq @r
    lda #24
    sta tmp3
@sw:
    lda sweep_ptr
    sta ptr1
    lda sweep_ptr+1
    sta ptr1+1
    ldy #0
    lda (ptr1),y
    and #3
    beq @clean
    ldx vb_pos
    cpx #VB_LIMIT
    bcs @r                  ; queue full: carry on next frame
    lda #$80
    sta (ptr1),y
    jsr tile_redraw
@clean:
    inc sweep_ptr
    bne :+
    inc sweep_ptr+1
:   lda sweep_ptr+1
    cmp #>(wetmap+960)
    bcc :+
    lda sweep_ptr
    cmp #<(wetmap+960)
    bcc :+
    lda #0
    sta sweep_on
    rts
:   dec tmp3
    bne @sw
@r: rts

; ptr1 -> a random tile's entry in wetmap
rnd_tile:
    jsr rnd
    sta ptr1
    jsr rnd
    and #3
    clc
    adc #>wetmap
    sta ptr1+1
    rts

; One step wetter / drier for the tile at ptr1, if it is a tile that can change.
tile_wet:
    lda ptr1+1
    cmp #>(wetmap+$3C0)
    bcc :+
    lda ptr1
    cmp #$C0
    bcs tw_r
:   ldx vb_pos
    cpx #VB_LIMIT
    bcs tw_r
    ldy #0
    lda (ptr1),y
    bpl tw_r
    and #3
    beq tw_r
    lda (ptr1),y
    sec
    sbc #1
    sta (ptr1),y
    jmp tile_redraw
tw_r:
    rts

tile_dry:
    lda ptr1+1
    cmp #>(wetmap+$3C0)
    bcc :+
    lda ptr1
    cmp #$C0
    bcs tw_r
:   ldx vb_pos
    cpx #VB_LIMIT
    bcs tw_r
    ldy #0
    lda (ptr1),y
    bpl tw_r
    and #3
    cmp #2
    bcs tw_r
    lda (ptr1),y
    clc
    adc #1
    sta (ptr1),y
    ; fall through

; Queue the tile at ptr1 for redrawing from its wetmap byte.
tile_redraw:
    ldy #0
    lda (ptr1),y
    and #3
    clc
    adc #T_ROAD
    ldx vb_pos
    sta vbuf+3,x
    lda ptr1+1
    sec
    sbc #>wetmap-$20
    sta vbuf,x
    lda ptr1
    sta vbuf+1,x
    lda #1
    sta vbuf+2,x
    lda #0
    sta vbuf+4,x
    txa
    clc
    adc #4
    sta vb_pos
    rts

; Work out what the current car is driving on: sets c_cond and, in the wet,
; dries the tile it has just driven onto.
car_cond:
    ldx car
    lda c_tyre,x
    asl a
    adc c_tyre,x
    sta tmp1                ; tyre * 3
    lda weather
    bne @wet
@done:
    lda tmp1
    sta c_cond,x
    rts
@wet:
    lda c_yh,x
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    clc
    adc #>wetmap
    sta ptr1+1
    lda c_yh,x
    and #$38
    asl a
    asl a
    sta tmp0
    lda c_xh,x
    lsr a
    lsr a
    lsr a
    ora tmp0
    sta ptr1
    ldy #0
    lda (ptr1),y
    bpl @soaked             ; edges, kerbs and painted lines never dry
    lda ptr1
    cmp c_tlo,x
    bne @new
    lda ptr1+1
    cmp c_thi,x
    beq @same
@new:
    lda ptr1
    sta c_tlo,x
    lda ptr1+1
    sta c_thi,x
    lda tmp1
    pha
    jsr tile_dry
    pla
    sta tmp1
    ldx car
@same:
    ldy #0
    lda (ptr1),y
    and #3
    eor #3                  ; level 0,1,2 -> 3,2,1
    sec
    sbc #1                  ; -> wetness 2,1,0
    clc
    adc tmp1
    sta tmp1
    jmp @done
@soaked:
    lda tmp1
    clc
    adc #2
    sta tmp1
    jmp @done

; Tyres wear with distance, faster when mistreated.
car_wear:
    ldx car
    lda c_spd,x
    cmp #24
    bcc @r
    ldy c_cond,x
    lda c_slip,x
    lsr a
    lsr a
    lsr a
    clc
    adc cond_wear,y
    clc
    adc c_wacc,x
    sta c_wacc,x
    bcc @r
    lda c_wear,x
    cmp #255
    beq @r
    inc c_wear,x
@r: rts

; Stopping in the pit box starts a service.
pit_check:
    ldx car
    lda c_xh,x
    cmp pit_rect
    bcc @out
    cmp pit_rect+2
    bcs @out
    lda c_yh,x
    cmp pit_rect+1
    bcc @out
    cmp pit_rect+3
    bcs @out
    lda c_arm,x
    beq @r
    lda c_spd,x
    cmp #14
    bcs @r
    lda #0
    sta c_arm,x
    sta c_pit,x
    lda #SERVICE_FRAMES
    sta c_serv,x
    cpx #0
    bne @rival
    lda demo
    bne @rival
    lda c_tyre              ; the player is offered the other compound; left/right changes it
    eor #1
    sta c_want
    rts
@rival:
    jsr rain_soon
    sta c_want,x
@r: rts
@out:
    lda #1
    sta c_arm,x
    rts

; A = 1 if it is raining or will be within ten seconds, else 0. Preserves X.
rain_soon:
    lda weather
    cmp #W_RAIN
    beq @yes
    cmp #W_DRYING
    beq @no
    lda rain_at
    beq @no
    sec
    sbc wx_sec
    bcc @no
    cmp #10
    bcs @no
@yes:
    lda #1
    rts
@no:
    lda #0
    rts

; A car being serviced stands still; returns with carry set if that is the case.
service_tick:
    ldx car
    lda c_serv,x
    bne :+
    clc
    rts
:   lda #0
    sta c_spd,x
    sta c_vxl,x
    sta c_vxh,x
    sta c_vyl,x
    sta c_vyh,x
    cpx #0
    bne @count
    lda pad_new
    and #BTN_LEFT
    beq :+
    lda #0
    sta c_want
:   lda pad_new
    and #BTN_RIGHT
    beq @count
    lda #1
    sta c_want
@count:
    dec c_serv,x
    bne @hold
    lda c_want,x
    sta c_tyre,x
    lda #0
    sta c_wear,x
@hold:
    sec
    rts

; Should this rival pit? Asked once a lap, at the waypoint before the pit box.
ai_pit_decide:
    ldx car
    lda c_wp,x
    cmp pit_wp
    bne @r
    lda c_lap,x
    cmp c_pitlap,x
    beq @r
    sta c_pitlap,x
    cmp track_laps
    bcs @r                  ; not on the last lap
    lda c_wear,x
    cmp #190
    bcs @yes
    lda weather
    cmp #W_RAIN
    bne :+
    lda c_tyre,x            ; raining: slicks must come off
    beq @yes
    rts
:   cmp #W_DRYING
    bne :+
    lda c_tyre,x            ; drying: wets come off once it is nearly dry
    beq @r
    lda dry_timer
    cmp #7
    bcc @yes
    rts
:   lda c_tyre,x            ; dry
    bne @yes
    lda rain_at             ; some rivals gamble on the forecast
    beq @r
    sec
    sbc wx_sec
    bcc @r
    cmp ai_gamble,x
    bcs @r
@yes:
    lda #1
    sta c_pit,x
@r: rts

; Falling rain: eight streaks.
rain_draw:
    lda weather
    cmp #W_RAIN
    bne @r
    lda #7
    sta tmp3
@l: lda tmp3
    asl a
    asl a
    asl a
    asl a
    asl a
    sta tmp0
    lda frame_count
    asl a
    asl a
    clc
    adc tmp0
    adc tmp3
    and #$7F
    clc
    adc #TOP+8
    ldx tmp3
    cpx #4
    bcc :+
    adc #71
:   sta d_y
    lda tmp3
    asl a
    asl a
    asl a
    adc tmp3
    asl a
    asl a
    sec
    sbc frame_count
    sbc frame_count
    sta d_x
    lda #0
    sta d_attr
    lda #SPR_RAIN
    jsr spr8
    dec tmp3
    bpl @l
@r: rts

;           slick: dry damp wet   wet tyre: dry damp wet
cond_max:   .byte 160, 150, 124,            132, 138, 136
cond_grip:  .byte 64,  40,  20,             56,  56,  44
cond_ai:    .byte 255, 214, 150,            205, 215, 208
cond_wear:  .byte 5,   5,   4,              26,  12,  5
ai_gamble:  .byte 0, 9, 0, 5        ; seconds of warning at which each rival fits wets early
