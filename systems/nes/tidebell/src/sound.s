; TIDEBELL sound driver: 4 music channels + 2 sound-effect channels on the 2A03.
; Streams are compiled by tools/build_music.py.

NCH = 6             ; 0 pulse1, 1 pulse2, 2 triangle, 3 noise, 4 sfx pulse (on pulse2), 5 sfx noise

.segment "ZEROPAGE"
sptr:       .res 2
stmp:       .res 1
s_src:      .res 1
s_reg:      .res 1

.segment "BSS"
ch_lo:      .res NCH
ch_hi:      .res NCH        ; 0 = channel idle
ch_wait:    .res NCH
ch_len:     .res NCH
ch_note:    .res NCH
ch_inst:    .res NCH
ch_env:     .res NCH
ch_new:     .res NCH
hw_owner:   .res 5          ; indexed by register offset 0 / 4
snd_speed:  .res 1
snd_tick:   .res 1
cur_song:   .res 1
snd_lock:   .res 1
sfx_sx:     .res 1
sfx_sy:     .res 1

.segment "CODE"

sound_init:
    lda #$40
    sta $4017
    lda #$0F
    sta $4015
    lda #$08
    sta $4001
    sta $4005
    lda #$30
    sta $4000
    sta $4004
    sta $400C
    lda #$80
    sta $4008
    ldx #NCH-1
    lda #0
@l: sta ch_hi,x
    sta ch_note,x
    dex
    bpl @l
    sta snd_lock
    lda #$FF
    sta cur_song
    sta hw_owner
    sta hw_owner+4
    rts

; A = song number. Does nothing if that song is already playing.
music_play:
    cmp cur_song
    beq @rts
    inc snd_lock
    sta cur_song
    asl a
    asl a
    asl a
    tax
    ldy #0
@l: lda song_table,x
    sta ch_lo,y
    lda song_table+1,x
    sta ch_hi,y
    lda #1
    sta ch_wait,y
    sta ch_len,y
    lda #0
    sta ch_note,y
    sta ch_inst,y
    inx
    inx
    iny
    cpy #4
    bne @l
    ldx cur_song
    lda song_speed,x
    sta snd_speed
    lda #1
    sta snd_tick
    dec snd_lock
@rts:
    rts

; A = effect number. Preserves X and Y.
sfx_play:
    stx sfx_sx
    sty sfx_sy
    inc snd_lock
    asl a
    asl a
    tax
    ldy #4
@l: lda sfx_table+1,x
    beq @skip
    sta ch_hi,y
    lda sfx_table,x
    sta ch_lo,y
    lda #1
    sta ch_wait,y
    sta ch_len,y
    lda #0
    sta ch_note,y
@skip:
    inx
    inx
    iny
    cpy #6
    bne @l
    dec snd_lock
    ldx sfx_sx
    ldy sfx_sy
    rts

; Called once per frame from NMI.
sound_update:
    lda snd_lock
    beq :+
    rts
:   dec snd_tick
    bne @sfx
    lda snd_speed
    sta snd_tick
    ldx #3
@m: jsr ch_advance
    dex
    bpl @m
@sfx:
    ldx #5
    jsr ch_advance
    ldx #4
    jsr ch_advance
    ; pulse 1
    ldx #0
    ldy #0
    jsr out_pulse
    ; pulse 2: effect wins over music
    ldx #4
    lda ch_hi+4
    bne :+
    ldx #1
:   ldy #4
    jsr out_pulse
    ; triangle
    lda ch_note+2
    beq @troff
    lda ch_inst+2
    beq @tron
    lda ch_env+2
    cmp #7
    bcs @troff
@tron:
    lda #$FF
    sta $4008
    lda ch_new+2
    beq @noise
    lda #0
    sta ch_new+2
    ldx ch_note+2
    lda per_lo,x
    sta $400A
    lda per_hi,x
    ora #$08
    sta $400B
    jmp @noise
@troff:
    lda #$80
    sta $4008
@noise:
    ldx #5
    lda ch_hi+5
    bne :+
    ldx #3
:   lda ch_note,x
    bne @non
    lda #$30
    sta $400C
    bne @env
@non:
    stx s_src
    jsr calc_vol
    ora #$30
    sta $400C
    ldx s_src
    lda ch_new,x
    beq @env
    lda #0
    sta ch_new,x
    ldy ch_note,x
    dey
    tya
    and #$0F
    sta $400E
    lda #$08
    sta $400F
@env:
    ldx #NCH-1
@e: lda ch_env,x
    cmp #255
    beq :+
    inc ch_env,x
:   dex
    bpl @e
    rts

; X = channel -> A = volume 0-15 from its instrument envelope. Clobbers X, Y.
calc_vol:
    lda ch_inst,x
    tay
    lda ch_env,x
    ldx in_shift,y
    beq @ns
@sh:
    lsr a
    dex
    bne @sh
@ns:
    sta stmp
    lda in_vol,y
    sec
    sbc stmp
    bcc @sus
    cmp in_sus,y
    bcs @ok
@sus:
    lda in_sus,y
@ok:
    rts

; X = source channel, Y = register offset (0 or 4)
out_pulse:
    stx s_src
    sty s_reg
    lda ch_note,x
    beq @silent
    jsr calc_vol            ; leaves Y = instrument
    ora in_duty,y
    ora #$30
    ldy s_reg
    sta $4000,y
    ldx s_src
    lda ch_new,x
    bne @per
    txa
    cmp hw_owner,y
    beq @done
@per:
    lda #0
    sta ch_new,x
    txa
    sta hw_owner,y
    lda ch_note,x
    tax
    lda per_lo,x
    sta $4002,y
    lda per_hi,x
    ora #$08
    sta $4003,y
@done:
    rts
@silent:
    lda #$30
    sta $4000,y
    lda #$FF
    sta hw_owner,y
    rts

; X = channel. Reads the stream until the next note or rest. Preserves X.
ch_advance:
    lda ch_hi,x
    beq @rts
    dec ch_wait,x
    bne @rts
    sta sptr+1
    lda ch_lo,x
    sta sptr
    ldy #0
@rd:
    lda (sptr),y
    iny
    cmp #$80
    bcs @cmd
    sta ch_note,x
    lda #0
    sta ch_env,x
    lda #1
    sta ch_new,x
    lda ch_len,x
    sta ch_wait,x
    tya
    clc
    adc sptr
    sta ch_lo,x
    lda sptr+1
    adc #0
    sta ch_hi,x
@rts:
    rts
@cmd:
    cmp #$FF
    beq @end
    cmp #$FE
    beq @jmp
    cmp #$C0
    bcs @inst
    and #$3F
    sta ch_len,x
    jmp @rd
@inst:
    and #$0F
    sta ch_inst,x
    jmp @rd
@jmp:
    lda (sptr),y
    pha
    iny
    lda (sptr),y
    sta sptr+1
    pla
    sta sptr
    ldy #0
    jmp @rd
@end:
    lda #0
    sta ch_hi,x
    sta ch_note,x
    rts

.segment "RODATA"
;              0 lead 1 soft 2 pluck 3 bell 4 hat 5 drum 6 blip 7 wash 8 echo
in_duty:  .byte $80,  $40,   $00,    $80,   0,    0,     $80,   0,     $40
in_vol:   .byte 11,   7,     10,     14,    7,    12,    10,    12,    5
in_shift: .byte 2,    3,     1,      1,     0,    0,     4,     2,     3
in_sus:   .byte 6,    4,     0,      2,     0,    0,     8,     0,     3
.include "music.inc"
