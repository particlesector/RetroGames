; The head-up display: two rows of text and icons above the track.
;   row 1:  LAP 2-6  POS 1   <weather icon> forecast
;   row 2:  <tyre icon> SLICK <wear bar>     message
; Each group is redrawn only when what it shows has changed, one group per frame.

.segment "BSS"
hud_lap:    .res 1          ; what each group currently shows
hud_pos:    .res 1
hud_wx:     .res 1
hud_tyre:   .res 1
hud_msg:    .res 1

.segment "RACE1"

hud_init:
    lda #$FF
    sta hud_lap
    sta hud_pos
    sta hud_wx
    sta hud_tyre
    sta hud_msg
    rts

; Start a VRAM queue entry: A = address low byte in row 1 ($20xx), Y = length. Leaves X at the data.
hud_open:
    ldx vb_pos
    sta vbuf+1,x
    lda #$20
    sta vbuf,x
    tya
    sta vbuf+2,x
    inx
    inx
    inx
    rts

hud_close:
    lda #0
    sta vbuf,x
    stx vb_pos
    rts

; A = 0..99 -> two digit tiles into the queue at X
hud_num:
    ldy #T_0
:   cmp #10
    bcc :+
    sbc #10
    iny
    bne :-
:   pha
    tya
    sta vbuf,x
    inx
    pla
    clc
    adc #T_0
    sta vbuf,x
    inx
    rts

; Y = offset into hud_text, tmp0 = count
hud_str:
:   lda hud_text,y
    sta vbuf,x
    inx
    iny
    dec tmp0
    bne :-
    rts

hud_update:
    ; ---- lap and position
    lda c_lap
    bne :+
    lda #1
:   cmp track_laps
    bcc :+
    lda track_laps
:   sta tmp1
    cmp hud_lap
    bne @lap
    lda c_pos
    cmp hud_pos
    beq @wx
@lap:
    lda tmp1
    sta hud_lap
    lda c_pos
    sta hud_pos
    lda #$21
    ldy #14
    jsr hud_open
    ldy #TX_LAP
    lda #14
    sta tmp0
    jsr hud_str
    lda hud_lap
    clc
    adc #T_0
    sta vbuf-10,x
    lda track_laps
    clc
    adc #T_0
    sta vbuf-8,x
    lda hud_pos
    clc
    adc #T_0
    sta vbuf-1,x
    jmp hud_close
    ; ---- forecast: changes at most once a second
@wx:
    lda wx_sec
    eor weather
    cmp hud_wx
    bne @far1_115
    jmp @tyre
@far1_115:
    sta hud_wx
    lda #$31
    ldy #14
    jsr hud_open
    lda weather
    bne @notdry
    lda rain_at
    beq @dry
    sec
    sbc wx_sec
    bcc @dry
    beq @dry
    pha                     ; rain on the way
    lda #T_CLOUD
    sta vbuf,x
    inx
    ldy #TX_RAININ
    lda #9
    sta tmp0
    jsr hud_str
    pla
    jsr hud_num
    lda #T_ROAD
    sta vbuf,x
    sta vbuf+1,x
    inx
    inx
    jmp hud_close
@dry:
    lda #T_SUN
    ldy #TX_DRY
    bne @plain
@notdry:
    cmp #W_RAIN
    bne @drying
    lda #T_RAIN
    sta vbuf,x
    inx
    ldy #TX_RAIN
    lda #6
    sta tmp0
    jsr hud_str
    lda rain_end
    sec
    sbc wx_sec
    bcs :+
    lda #0
:   jsr hud_num
    ldy #TX_BLANK
    lda #5
    sta tmp0
    jsr hud_str
    jmp hud_close
@drying:
    lda #T_CLOUD
    ldy #TX_DRYING
@plain:
    sta vbuf,x
    inx
    lda #13
    sta tmp0
    jsr hud_str
    jmp hud_close
    ; ---- tyres: compound and an eight-segment wear bar
@tyre:
    lda c_wear
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    sta tmp1                ; segments used up, 0-7
    asl a
    ora c_tyre
    cmp hud_tyre
    beq @msg
    sta hud_tyre
    lda #$41
    ldy #16
    jsr hud_open
    lda #T_SLICK
    ldy #TX_SLICK
    lda c_tyre
    beq :+
    lda #T_WET
    ldy #TX_WET
    bne :++
:   lda #T_SLICK
:   sta vbuf,x
    inx
    lda #7
    sta tmp0
    jsr hud_str
    lda #8
    sec
    sbc tmp1
    sta tmp1                ; segments left
    ldy #0
:   lda #T_BAR_ON
    cpy tmp1
    bcc :+
    lda #T_BAR_OFF
:   sta vbuf,x
    inx
    iny
    cpy #8
    bne :--
    jmp hud_close
    ; ---- message: start lights, the flag, or the tyre being fitted
@msg:
    ldy #0
    lda c_serv
    beq :+
    ldy #6
    lda c_want
    beq @have
    iny
    bne @have
:   lda race_state
    cmp #RS_DONE
    bne :+
    ldy #5
    bne @have
:   cmp #RS_RACE
    bne :+
    lda race_time+1
    bne @have
    lda race_time
    cmp #90
    bcs @have
    ldy #4
    bne @have
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
    clc
    adc #TX_MSGS
    pha
    lda #$53
    ldy #8
    jsr hud_open
    pla
    tay
    lda #8
    sta tmp0
    jsr hud_str
    jmp hud_close
@r: rts

hud_text:
TX_LAP = * - hud_text
    .byte "LAP 1-1  POS 1"
TX_RAININ = * - hud_text
    .byte " RAIN IN "
TX_RAIN = * - hud_text
    .byte " RAIN "
TX_BLANK = * - hud_text
    .byte "     "
TX_DRY = * - hud_text
    .byte " DRY         "
TX_DRYING = * - hud_text
    .byte " DRYING      "
TX_SLICK = * - hud_text
    .byte " SLICK "
TX_WET = * - hud_text
    .byte " WET   "
TX_MSGS = * - hud_text
    .byte "        ", "READY   ", "READY  .", "READY ..", "GO!     ", "FINISH! ", "FIT SLK ", "FIT WET "
