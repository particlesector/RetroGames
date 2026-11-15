; KITESONG: an Atari 2600 rhythm flyer. 8 KB, F8 bank switching.
;
; Bank 1 (the main bank, where the console starts): the frame loop, input, the kernels (play,
; title, results) and their tables. Bank 0: the songs and the music driver, which once a frame
; times the song, plays the bass, drums and caught chimes, judges catches and misses, and builds
; the display list the play kernel draws the chimes from. The banks meet at a trampoline at
; $FFE0 in each (CallBank0), and both reset through $FFF0.
;
; The play screen, 192 lines: 12 of status (the wind meter), the sky in 10 bands of 14 lines
; (one a lane: a band's first line places player 1 for its chime, the second moves it and sets
; its colour and copies, then 12 drawn lines), and 40 lines of hills. Every line strobes HMOVE,
; so its 8-pixel blank on the left is the same on every line. The kite is player 0 at x 116;
; chimes come from the left on the wind, 16 pixels an eighth note, and reach the kite when their
; note is due.

        .setcpu "6502X"
        .include "vcs.inc"

KITE_X    = 116          ; the kite's column; a chime reaches it on its beat
KITE_H    = 10
KITE_TOP  = 110          ; kite_y's range: 0 (top of the sky) to this
NBANDS    = 10
WIN       = 6            ; pixels either side of a chime's beat that catch it
METER_MAX = 10
MISS_COST = 2            ; the wind lost to a miss; a catch gives one back

M_TITLE   = 0
M_PLAY    = 1
M_FALL    = 2
M_RESULT  = 3

R_AGAIN   = 0
R_CLEAR   = 1
R_PERFECT = 2

CMD_FRAME = 0            ; bank 0 commands, in A at CallBank0
CMD_START = 1

; ---- RAM ----
        .segment "ZEROPAGE"
mode:       .res 1
sel:        .res 1      ; the title's chosen song
song:       .res 1
free:       .res 1      ; nonzero: Free Flight
stars:      .res 1      ; a bit a song: played perfectly
result:     .res 1
meter:      .res 1      ; the wind: 0 and the kite falls
caught:     .res 1
total:      .res 1      ; the song's chimes
sky:        .res 1      ; its theme
kite_y:     .res 1      ; the kite's top line in the sky's 120 counted lines
kite_band:  .res 1      ; the band its middle is in (0 the top: lane 9)
joy_prev:   .res 1
sw_prev:    .res 1
overruns:   .res 1
frame_n:    .res 1      ; frames whose logic outran VBLANK or the overscan
idle:       .res 1      ; the title's (or a demo's results') quiet time, a count every 4 frames
demo:       .res 1      ; nonzero: the game flies itself (attract mode)
demo_song:  .res 1      ; the next song it flies
fire:       .res 1      ; bit 7 held, bit 6 pressed this frame
; music
tempo:      .res 1      ; frames an eighth
tick:       .res 1      ; frames into the eighth
step:       .res 1      ; eighth in the bar
beat:       .res 1
base:       .res 2      ; the song's time at this eighth, in pixels (16 an eighth)
now:        .res 2      ; and at this frame
bars:       .res 2      ; the bar playing
bars0:      .res 2      ; the first (Free Flight loops)
mel:        .res 2      ; the next chime's event
pxt:        .res 2      ; pixels into an eighth, by frame (PXTn)
ev:         .res 2      ; the next chime's time, in pixels
cur_lane:   .res 1      ; its lane, $FE a rest, $FF the end
cur_hit:    .res 1      ; the kite is on it, within its window
m_vol:      .res 1      ; the melody (channel 1)
m_age:      .res 1
m_note:     .res 1      ; its lane
b_vol:      .res 1      ; bass and snare (channel 0)
b_age:      .res 1
b_kind:     .res 1      ; 0 bass, 1 snare
b_root:     .res 1
; the display list, a band each (band 0 the top)
lane_x:     .res NBANDS ; where player 1 goes
lane_end:   .res 1      ; $FF: past the last band
lane_nus:   .res NBANDS ; its copies (NUSIZ1)
lane_chl:   .res NBANDS ; <CHIME, or <ZERO for none
; Free Flight's notes, newest first, drifting left
NREC = 4
rec_band:   .res NREC   ; $FF none
rec_x:      .res NREC
; the kernels
band:       .res 1
nextx:      .res 1
kite_cnt:   .res 1
kite_ptr:   .res 2
ch_ptr:     .res 2
sky_ptr:    .res 2
sun_ptr:    .res 2
hud_bits:   .res 1
hud_col:    .res 1
hill_col:   .res 1
; scratch: the display list's build (bank 0) or the text and digit pointers (bank 1)
scratch:    .res 18
mask        = scratch       ; 10: a band's copies found so far
t_ptr       = scratch + 10  ; 2
t_time      = scratch + 12  ; 2
t_n         = scratch + 14
t_tmp       = scratch + 15
t_band      = scratch + 16
dptr        = scratch       ; 8: four digit pointers
tmp         = scratch + 16  ; bank 1's logic
tmp2        = scratch + 17


; =================================================================================================
; Bank 0: the songs and the music driver
; =================================================================================================
        .segment "CODE0"

Bank0Entry:
        cmp #CMD_START
        bne @frame
        jmp StartSong
@frame: jmp MusicFrame

; ---- A song's start: its header, time 0, the first chime ----
StartSong:
        lda song
        asl
        tax
        lda SONGS,x
        sta t_ptr
        lda SONGS+1,x
        sta t_ptr+1
        ldy #0
        lda (t_ptr),y
        sta tempo
        iny
        lda (t_ptr),y
        sta sky
        iny
        lda (t_ptr),y
        sta beat
        iny
        lda (t_ptr),y
        sta total
        iny
        lda (t_ptr),y
        sta bars
        sta bars0
        iny
        lda (t_ptr),y
        sta bars+1
        sta bars0+1
        iny
        lda (t_ptr),y
        sta mel
        iny
        lda (t_ptr),y
        sta mel+1
        iny
        lda (t_ptr),y
        sta pxt
        iny
        lda (t_ptr),y
        sta pxt+1
        lda #0
        sta tick
        sta step
        sta base
        sta base+1
        sta caught
        sta cur_hit
        sta m_vol
        sta b_vol
        sta m_age
        sta b_age
        lda #METER_MAX
        sta meter
        ldy #0                  ; the first event: its time and lane
        lda (mel),y
        sta ev
        sty ev+1
        iny
        lda (mel),y
        sta cur_lane
        lda #$FF
        ldx #NREC-1
@rec:   sta rec_band,x
        dex
        bpl @rec
        rts

; ---- A frame of the song ----
MusicFrame:
        ldy tick                ; now = base + the pixels this far into the eighth
        lda (pxt),y
        clc
        adc base
        sta now
        lda base+1
        adc #0
        sta now+1
        lda tick
        bne @mid
        jsr NewEighth
@mid:   lda free
        bne @free
        jsr Judge
        lda mode
        cmp #M_PLAY
        bne @quiet              ; the kite fell
        jsr Voices
        jsr BuildList
        jmp Advance
@free:  jsr FreeFlight
        jsr Voices
        jsr BuildFree
        jmp Advance
@quiet: lda #0
        sta AUDV0
        sta AUDV1
        rts

; The clock: the next frame, eighth and bar. The end of the bars ends a song (Free Flight loops).
Advance:
        inc tick
        lda tick
        cmp tempo
        bcc @done
        lda #0
        sta tick
        lda base
        clc
        adc #16
        sta base
        bcc @b
        inc base+1
@b:     inc step
        lda step
        cmp #8
        bcc @done
        lda #0
        sta step
        inc bars
        bne @c
        inc bars+1
@c:     ldy #0
        lda (bars),y
        cmp #$FF
        bne @done
        lda free
        beq SongEnd
        lda bars0
        sta bars
        lda bars0+1
        sta bars+1
@done:  rts

SongEnd:
        lda #R_CLEAR
        ldx caught
        cpx total
        bne @set
        lda song                ; a perfect song lights its star
        tax
        lda BIT8,x
        ora stars
        sta stars
        lda #R_PERFECT
@set:   sta result
        lda #M_RESULT
        sta mode
        lda #0
        sta AUDV0
        sta AUDV1
        rts

BIT8:   .byte $01, $02, $04, $08, $10, $20, $40, $80

; A new eighth: the beat pattern's bass or snare, on the bar's chord.
NewEighth:
        lda beat
        asl
        asl
        asl
        ora step
        tax
        lda BEATS,x
        beq @none
        cmp #2
        beq @snare
        ldy #0
        lda (bars),y
        sta b_root
        lda #0
        sta b_kind
        sta b_age
        lda #7
        sta b_vol
@none:  rts
@snare: lda #1
        sta b_kind
        lda #0
        sta b_age
        lda #8
        sta b_vol
        rts

; Beats: per eighth, 0 nothing, 1 bass, 2 snare (assets/songs.txt has them).
BEATS:  .byte 1, 0, 1, 2, 1, 0, 1, 2
        .byte 1, 0, 2, 0, 1, 0, 2, 0
        .byte 1, 1, 1, 1, 2, 1, 1, 1
        .byte 1, 0, 0, 1, 0, 0, 1, 0

; ---- Catches and misses: the next chime, against the kite ----
Judge:
        lda cur_lane
        cmp #$FF
        beq @rts
        sec                     ; t_time = now - the chime's time (signed)
        lda now
        sbc ev
        sta t_time
        lda now+1
        sbc ev+1
        sta t_time+1
        lda cur_lane
        cmp #$FE
        bne @chime
        lda t_time+1            ; a rest: passes on its time
        bmi @rts
        jmp NextEvent
@chime: lda t_time+1
        bpl @due
        cmp #$FF                ; early: only within the window
        bne @rts
        lda t_time
        cmp #256-WIN
        bcc @rts
@due:   lda #9                  ; is the kite in its lane?
        sec
        sbc cur_lane
        cmp kite_band
        bne @off
        lda #1
        sta cur_hit
@off:   lda cur_hit
        beq @late
        lda t_time+1            ; caught: it rings on its beat (or now, if the kite came late)
        bmi @rts
        lda cur_lane
        sta m_note
        lda #12
        sta m_vol
        lda #0
        sta m_age
        inc caught
        lda meter
        cmp #METER_MAX
        bcs @next
        inc meter
@next:  jmp NextEvent
@late:  lda t_time+1            ; not caught: missed once past the window
        bmi @rts
        bne @miss
        lda t_time
        cmp #WIN+1
        bcc @rts
@miss:  lda meter
        sec
        sbc #MISS_COST
        bcs @m
        lda #0
@m:     sta meter
        bne NextEvent
        lda #M_FALL             ; out of wind: the kite falls
        sta mode
@rts:   rts

NextEvent:
        lda mel
        clc
        adc #2
        sta mel
        bcc @a
        inc mel+1
@a:     ldy #0
        lda (mel),y
        clc
        adc ev
        sta ev
        bcc @b
        inc ev+1
@b:     iny
        lda (mel),y
        sta cur_lane
        lda #0
        sta cur_hit
        rts

; ---- Free Flight: the button plays the note at the kite's height ----
FreeFlight:
        ldx #NREC-1             ; the notes drift left, a pixel a frame
@drift: lda rec_band,x
        bmi @nx
        dec rec_x,x
        bpl @nx
        lda #$FF
        sta rec_band,x
@nx:    dex
        bpl @drift
        bit fire
        bvc @held
        lda #9                  ; pressed: the note, and a chime where the kite is
        sec
        sbc kite_band
        sta m_note
        lda #12
        sta m_vol
        lda #0
        sta m_age
        ldx #NREC-2
@shift: lda rec_band,x
        sta rec_band+1,x
        lda rec_x,x
        sta rec_x+1,x
        dex
        bpl @shift
        lda kite_band
        sta rec_band
        lda #KITE_X
        sta rec_x
        rts
@held:  bit fire                ; held: the note sustains
        bpl @rts
        lda m_vol
        cmp #9
        bcs @rts
        lda #9
        sta m_vol
@rts:   rts

; ---- The two channels, from the voices' state ----
Voices:
        inc b_age
        lda b_kind
        bne @snare
        ldx b_root
        lda ROOT_C,x
        sta AUDC0
        lda ROOT_F,x
        sta AUDF0
        lda b_age
        cmp #3
        bcc @bv
        lda #0
        sta b_age
        lda b_vol
        cmp #4
        bcc @bv
        dec b_vol
@bv:    lda b_vol
        sta AUDV0
        jmp @mel
@snare: lda #8
        sta AUDC0
        lda #3
        sta AUDF0
        lda b_vol
        sec
        sbc #2
        bcs @sv
        lda #0
@sv:    sta b_vol
        sta AUDV0
@mel:   ldx m_note
        lda LANE_C,x
        sta AUDC1
        lda LANE_F,x
        sta AUDF1
        inc m_age
        lda m_age
        cmp #5
        bcc @mv
        lda #0
        sta m_age
        lda m_vol
        beq @mv
        dec m_vol
@mv:    lda m_vol
        sta AUDV1
        rts

; The bass's chords (C2 F2 A2 Bb2 on the buzzy 4-bit poly, G3 on the pure tone) and the
; melody's lanes (C4 D4 E4 A4 on the pure tone /6, C5 D5 E5 G5 A5 C6 on /2): the notes the
; TIA plays within 20 cents.
ROOT_C: .byte 1, 1, 1, 1, 12
ROOT_F: .byte 31, 23, 18, 17, 26
LANE_C: .byte 12, 12, 12, 12, 4, 4, 4, 4, 4, 4
LANE_F: .byte 19, 17, 15, 11, 29, 26, 23, 19, 17, 14

; ---- The display list ----
; Each band shows its nearest chime, and up to two more behind it as player 1's copies when
; they're 16, 32 or 64 pixels on (1, 2 or 4 eighths); others in the band wait their turn.
ClearList:
        lda #0
        ldx #NBANDS-1
@c:     sta mask,x
        dex
        bpl @c
        rts

; A chime at x (A) in band X, nearest first.
Insert:
        sta t_tmp
        lda mask,x
        bne @more
        lda #$80
        sta mask,x
        lda t_tmp
        sta lane_nus,x          ; the nearest's x, until FinishList
        rts
@more:  lda lane_nus,x          ; its distance behind the nearest
        sec
        sbc t_tmp
        ldy #1
        cmp #16
        beq @bit
        ldy #2
        cmp #32
        beq @bit
        ldy #8
        cmp #64
        bne @rts
@bit:   tya
        ora mask,x
        and #$0F
        tay
        lda ALLOWED,y
        beq @rts
        tya
        ora #$80
        sta mask,x
@rts:   rts

FinishList:
        ldx #NBANDS-1
@f:     lda mask,x
        beq @none
        and #$0F
        tay
        lda lane_nus,x
        sec
        sbc COPY_OFF,y
        sta lane_x,x
        lda COPY_MODE,y
        sta lane_nus,x
        lda #<CHIME
        sta lane_chl,x
        jmp @nx
@none:  lda #0
        sta lane_x,x
        sta lane_nus,x
        lda #<ZERO
        sta lane_chl,x
@nx:    dex
        bpl @f
        rts

; By the copies found (bit 0: 16 on, bit 1: 32, bit 3: 64): allowed, the main copy's offset
; back from the nearest, and NUSIZ1.
ALLOWED:   .byte 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0
COPY_OFF:  .byte 0, 16, 32, 32, 0, 0, 0, 0, 64, 0, 64, 0, 0, 0, 0, 0
COPY_MODE: .byte 0, 1, 2, 3, 0, 0, 0, 0, 4, 0, 6, 0, 0, 0, 0, 0

; The song's next chimes, from the next one on, while they're on the screen.
BuildList:
        jsr ClearList
        lda mel
        sta t_ptr
        lda mel+1
        sta t_ptr+1
        lda ev
        sta t_time
        lda ev+1
        sta t_time+1
        lda #12
        sta t_n
@ev:    ldy #1
        lda (t_ptr),y
        cmp #$FF
        beq @done
        cmp #$FE
        beq @next
        eor #$FF                ; its band: 9 - lane
        sec
        adc #9
        sta t_band
        sec                     ; ahead = its time - now
        lda t_time
        sbc now
        tax
        lda t_time+1
        sbc now+1
        bmi @late
        bne @done
        cpx #KITE_X+1
        bcs @done
        txa
        eor #$FF                ; x = KITE_X - ahead
        sec
        adc #KITE_X
        jmp @put
@late:  lda #KITE_X             ; in its window after the beat: at the kite
@put:   ldx t_band
        jsr Insert
@next:  dec t_n
        beq @done
        lda t_ptr
        clc
        adc #2
        sta t_ptr
        bcc @a
        inc t_ptr+1
@a:     ldy #0
        lda (t_ptr),y
        clc
        adc t_time
        sta t_time
        bcc @ev
        inc t_time+1
        jmp @ev
@done:  jmp FinishList

; Free Flight's notes, newest (nearest the kite) first.
BuildFree:
        jsr ClearList
        ldy #0
@r:     lda rec_band,y
        bmi @nx
        tax
        lda rec_x,y
        sty t_n
        jsr Insert
        ldy t_n
@nx:    iny
        cpy #NREC
        bcc @r
        jmp FinishList

        .include "songs.inc"

; ---- Bank 0's trampoline and reset ----
        .segment "TRAMP0"
        .res 3, $EA             ; $FFE0: bank 1's STA $FFF8 lands us at $FFE3
        jsr Bank0Entry          ; $FFE3
        sta $FFF9               ; $FFE6: back to bank 1, which goes on at $FFE9

        .segment "VEC0"
        sta $FFF9               ; $FFF0: whichever bank starts, go to bank 1's Start
        jmp Start
        .res 4, $FF
        .word $FFF0, $FFF0, $FFF0


; =================================================================================================
; Bank 1: the frame, input and the kernels
; =================================================================================================
        .segment "TABLES1"
        .include "tables.inc"

        .segment "CODE1"

Start:  sei
        cld
        ldx #0
        txa
@clr:   sta $00,x
        inx
        bne @clr
        dex
        txs
        lda #$FF
        sta lane_end
        lda #>CHIME
        sta ch_ptr+1
.ifdef AUTOSTART                ; a debug build that flies song AUTOSTART - 1 at once
        lda #AUTOSTART - 1
        sta sel
        jsr StartPlay
.endif

; ---- The frame: 3 lines of VSYNC, 37 of VBLANK, 192 of picture, 30 of overscan ----
Frame:  lda #2
        sta WSYNC
        sta VSYNC
        sta VBLANK
        sta WSYNC
        sta WSYNC
        lda #0
        sta WSYNC
        sta VSYNC
        lda #42
        sta TIM64T
        inc frame_n
        jsr Logic
        bit TIMINT              ; the logic ran past its time (tests check this stays 0)
        bpl @vb
        inc overruns
@vb:    lda INTIM
        bne @vb
        lda mode
        cmp #M_TITLE
        bne @k1
        jmp KernelTitle
@k1:    cmp #M_RESULT
        bne @k2
        jmp KernelResult
@k2:    jmp KernelPlay

Overscan:
        sta WSYNC
        lda #2
        sta VBLANK
        lda #38
        sta TIM64T
        lda #0
        sta PF0
        sta PF1
        sta PF2
        sta GRP0
        sta GRP1
        lda mode
        cmp #M_PLAY
        bne @os
        lda #CMD_FRAME
        jsr CallBank0
        bit TIMINT
        bpl @os
        inc overruns
@os:    lda INTIM
        bne @os
        jmp Frame

; ---- The VBLANK's logic, by mode ----
Logic:  jsr ReadInput
        lda mode
        cmp #M_TITLE
        bne @l1
        jmp TitleLogic
@l1:    cmp #M_RESULT
        bne @l2
        jmp ResultLogic
@l2:    jmp PlayLogic

; Joystick and switches: `fire` bit 7 held, bit 6 pressed this frame; joy_prev the directions
; held (SWCHA's player 0 bits, 1 pushed: 7 right, 6 left, 5 down, 4 up) and tmp2 those pushed
; this frame; tmp the console switches pressed this frame (bit 0 Reset, bit 1 Select).
ReadInput:
        lda INPT4
        eor #$80
        and #$80
        sta tmp                 ; held now
        lda fire
        eor #$80
        and tmp                 ; and not before
        lsr
        ora tmp
        sta fire
        lda SWCHB
        eor #$FF
        and #$03
        tax
        eor sw_prev
        stx sw_prev
        and sw_prev
        sta tmp
        lda SWCHA
        eor #$FF
        and #$F0
        tax
        eor joy_prev
        stx joy_prev
        and joy_prev
        sta tmp2
        rts

; ---- Title: left and right (or Select) choose a song, the button (or Reset) flies it ----
TitleLogic:
        lda #0
        sta AUDV0
        sta AUDV1
        sta demo
        jsr Quiet               ; ten quiet seconds start a demo
        bcc @in
        lda idle
        cmp #150
        bcc @in
        lda demo_song
        sta sel
        inc demo_song
        lda demo_song
        cmp #NSONGS-1
        bcc @ds
        lda #0
        sta demo_song
@ds:    inc demo
        jmp StartPlay
@in:    lda tmp2
        and #$80                ; right
        bne @next
        lda tmp
        and #$02                ; Select
        bne @next
        lda tmp2
        and #$40                ; left
        beq @go
        dec sel
        bpl @go
        lda #NSONGS-1
        sta sel
        jmp @go
@next:  inc sel
        lda sel
        cmp #NSONGS
        bcc @go
        lda #0
        sta sel
@go:    bit fire
        bvs StartPlay
        lda tmp
        and #$01                ; Reset
        bne StartPlay
        lda #0                  ; the title's hills and sky
        sta sky
        jmp SetTheme

StartPlay:
        lda #0
        sta idle
        lda sel
        sta song
        ldx #0
        cmp #NSONGS-1
        bne @f
        inx
@f:     stx free
        lda #CMD_START
        jsr CallBank0
        lda #61                 ; the middle lane
        sta kite_y
        lda #M_PLAY
        sta mode
        jsr SetTheme
        jmp PrepPlay

; Carry set if nothing was touched this frame (and idle counts up, every 4 frames);
; clear (and idle back to 0) if anything was.
Quiet:  lda joy_prev
        ora fire
        ora tmp
        beq @q
        lda #0
        sta idle
        clc
        rts
@q:     lda frame_n
        and #3
        bne @s
        inc idle
@s:     sec
        rts

; The song's sky: its colours, sun (or moon), hills and kite.
SetTheme:
        ldx sky
        lda THEME_SKY_L,x
        sta sky_ptr
        lda THEME_SKY_H,x
        sta sky_ptr+1
        lda THEME_SUN_L,x
        sta sun_ptr
        lda THEME_SUN_H,x
        sta sun_ptr+1
        lda THEME_HILL,x
        sta hill_col
        lda THEME_KITE,x
        sta COLUP0
        rts

THEME_SKY_L: .byte <SKY_DUSK, <SKY_NIGHT, <SKY_GALE, <SKY_DAWN
THEME_SKY_H: .byte >SKY_DUSK, >SKY_NIGHT, >SKY_GALE, >SKY_DAWN
THEME_SUN_L: .byte <SUN_BIG, <SUN_MOON, <SUN_NONE, <SUN_BIG
THEME_SUN_H: .byte >SUN_BIG, >SUN_MOON, >SUN_NONE, >SUN_BIG
THEME_SUNC:  .byte $2C, $0C, $00, $1E
THEME_HILL:  .byte $62, $90, $02, $C4
THEME_KITE:  .byte $A6, $1E, $36, $86

; Each lane's chime colour, the top band (C6) first.
LANE_COL:    .byte $4C, $3C, $2C, $1E, $DC, $CC, $AC, $9C, $8C, $6C

; ---- Play: the joystick flies the kite; Select (or in Free Flight, Reset) quits ----
PlayLogic:
        lda mode
        cmp #M_FALL
        bne @play
        lda kite_y              ; out of wind: down it goes
        clc
        adc #2
        cmp #KITE_TOP
        bcc @f
        lda #R_AGAIN
        sta result
        lda #M_RESULT
        sta mode
        lda #KITE_TOP
@f:     sta kite_y
        jmp PrepPlay
@play:  lda demo
        beq @own
        jsr Quiet               ; a demo: anything touched ends it
        bcc @quit
        jsr Autopilot
        jmp @fly
@own:   lda tmp
        and #$02
        bne @quit
        lda free
        beq @fly
        lda tmp
        and #$01
        bne @quit
@fly:   lda joy_prev
        and #$10                ; up
        beq @dn
        lda kite_y
        sec
        sbc #3
        bcs @up
        lda #0
@up:    sta kite_y
        jmp @band
@dn:    lda joy_prev
        and #$20                ; down
        beq @drift
        lda kite_y
        clc
        adc #3
        cmp #KITE_TOP
        bcc @dn2
        lda #KITE_TOP
@dn2:   sta kite_y
        jmp @band
@drift: ldx kite_band           ; left alone, it settles on its lane
        lda LANE_Y,x
        cmp kite_y
        beq @band
        bcs @low
        dec kite_y
        jmp @band
@low:   inc kite_y
@band:  lda kite_y              ; its band: (kite_y + 5) / 12
        clc
        adc #5
        ldx #0
@div:   cmp #12
        bcc @bd
        sbc #12
        inx
        bne @div
@bd:    stx kite_band
        jmp PrepPlay
@quit:  lda #M_TITLE
        sta mode
        lda #0
        sta AUDV0
        sta AUDV1
        rts

; The demo's pilot: toward the next chime's lane, as the tests' bot flies (into joy_prev).
Autopilot:
        lda #0
        sta joy_prev
        lda cur_lane
        cmp #10
        bcs @r
        eor #$FF                ; its band: 9 - lane
        sec
        adc #9
        tax
        lda LANE_Y,x
        sec
        sbc kite_y              ; target - kite_y
        beq @r
        bcs @dn
        cmp #$FF                ; just above: close enough
        beq @r
        lda #$10                ; up
        sta joy_prev
        rts
@dn:    cmp #2
        bcc @r
        lda #$20                ; down
        sta joy_prev
@r:     rts

; A band's kite_y with the kite centred on its chimes.
LANE_Y: .byte 1, 13, 25, 37, 49, 61, 73, 85, 97, 109

; The play kernel's setup: the kite (placed as the chimes are, so the two line up), its
; skip-draw counter and pointer, and the wind meter.
PrepPlay:
        lda #KITE_X
        sta WSYNC
        sta HMOVE
        sec
@d:     sbc #15
        bcs @d
        eor #7
        asl
        asl
        asl
        asl
        sta HMP0
        sta RESP0
        sta WSYNC
        sta HMOVE
        lda kite_y              ; kite_cnt = KITE_H + kite_y
        clc
        adc #KITE_H
        sta kite_cnt
        lda #<(KITE_GFX + KITE_H - 120)   ; kite_ptr = KITE_GFX + kite_y + KITE_H - 120
        clc
        adc kite_y
        sta kite_ptr
        lda #>(KITE_GFX + KITE_H - 120)
        adc #0
        sta kite_ptr+1
        ldx meter
        lda METER_BITS,x
        ldy free                ; no wind to lose in Free Flight
        beq @m
        lda #0
@m:     sta hud_bits
        lda #$C8                ; green, red when low
        cpx #5
        bcs @c
        lda #$46
@c:     sta hud_col
        sta HMCLR
        rts

METER_BITS: .byte $00, $80, $80, $C0, $C0, $E0, $E0, $F0, $F8, $FC, $FF

; ---- Results: the button (or Reset) goes back to the title ----
ResultLogic:
        lda #0
        sta AUDV0
        sta AUDV1
        lda demo
        beq @own
        jsr Quiet
        bcc @back
        lda idle
        cmp #60
        bcs @back
        bcc @show
@own:   bit fire
        bvs @back
        lda tmp
        and #$03
        beq @show
@back:  lda #M_TITLE
        sta mode
        lda #0
        sta idle
        rts
@show:  lda #0
        sta sky
        jsr SetTheme
        lda #64                 ; the digits: player 0 the tens, player 1 the ones
        ldx #0
        jsr PosObj
        lda #72
        inx
        jsr PosObj
        sta WSYNC
        sta HMOVE
        lda caught
        ldx #0
        jsr DigitPtrs
        lda total
        ldx #4
        jsr DigitPtrs
        sta HMCLR
        rts

; dptr+X and dptr+X+2: DIGITS for A's tens and ones.
DigitPtrs:
        ldy #0
@t:     cmp #10
        bcc @o
        sbc #10
        iny
        bne @t
@o:     sta tmp
        asl
        asl
        adc tmp                 ; ones x 5
        adc #<DIGITS
        sta dptr+2,x
        lda #>DIGITS
        adc #0
        sta dptr+3,x
        tya
        sta tmp
        asl
        asl
        adc tmp
        adc #<DIGITS
        sta dptr,x
        lda #>DIGITS
        adc #0
        sta dptr+1,x
        rts

; Places object X (0 player 0, 1 player 1) at A, roughly; its HMOVE is the caller's next.
PosObj: sta WSYNC
        sec
@d:     sbc #15
        bcs @d
        eor #7
        asl
        asl
        asl
        asl
        sta HMP0,x
        sta RESP0,x
        rts

; ---- The play kernel: 12 status lines, the sky's 10 bands, 40 lines of hills ----
KernelPlay:
        sta WSYNC               ; status line 0
        sta HMOVE
        lda #0
        sta VBLANK
        sta COLUBK
        sta PF0
        sta PF1
        sta PF2
        sta GRP0
        sta GRP1
        sta NUSIZ0
        lda #1
        sta CTRLPF              ; reflected: the sun in the middle
        lda hud_col
        sta COLUPF
        ldx #11
@hud:   sta WSYNC               ; status lines 1-11: the meter on 4-7
        sta HMOVE
        lda #0
        cpx #8
        bcs @h0
        cpx #4
        bcc @h0
        lda hud_bits
@h0:    sta PF2
        dex
        bne @hud
        ldx sky
        lda THEME_SUNC,x
        sta COLUPF
        lda #0
        sta band
        ldy #119
        lda lane_x
@band:  sta WSYNC               ; a band's first line: player 1 to its chime (A = x <= 120)
        sta HMOVE
        sec
@div:   sbc #15
        bcs @div
        eor #7
        asl
        asl
        asl
        asl
        sta HMP1
        sta RESP1
        sta WSYNC               ; its second: the fine move, colour, copies, graphics
        sta HMOVE
        ldx band
        lda LANE_COL,x
        sta COLUP1
        lda lane_nus,x
        sta NUSIZ1
        lda lane_chl,x
        sta ch_ptr
        sta HMCLR               ; 24 cycles after HMOVE
        lda lane_x+1,x          ; the next band's x, or lane_end's $FF
        sta nextx
        inc band
        ldx #12
@line:  sta WSYNC               ; 12 drawn lines
        sta HMOVE
        lda (ch_ptr),y          ; the chime, before the picture starts
        sta GRP1
        lda (sky_ptr),y
        sta COLUBK
        lda (sun_ptr),y
        sta PF2
        lda #KITE_H-1           ; the kite (skip-draw)
        dcp kite_cnt
        bcs @kd
        lda #0
        .byte $2C
@kd:    lda (kite_ptr),y
        sta GRP0
        dey
        dex
        bne @line
        lda nextx
        bpl @band
        lda hill_col
        sta COLUPF
        jmp Hills

; 40 lines of hills, then the overscan.
Hills:  ldy #39
@h:     sta WSYNC
        sta HMOVE
        lda HILL0,y
        sta PF0
        lda HILL1,y
        sta PF1
        lda HILL2,y
        sta PF2
        lda #0
        sta GRP0
        sta GRP1
        dey
        bpl @h
        jmp Overscan

; ---- Title and results: sky lines and text in the playfield ----
; Inline (no JSR): a block's last line and the next block's first must fit one line.

; n lines of sky; X the sky's colour (SKY_DUSK,x), down a step a line.
.macro SKY n
        .local l, k
        lda #n
        sta tmp
l:      sta WSYNC
        sta HMOVE
        lda SKY_DUSK,x
        sta COLUBK
        lda #0
        sta PF0
        sta PF1
        sta PF2
        dex
        bpl k
        inx
k:      dec tmp
        bne l
.endmacro

; 20 lines of text: string Y (a TX_ offset), 4 lines a row, the playfield not reflected.
.macro TEXT
        .local row, done
        lda #5
        sta tmp2
row:
        .repeat 4
        sta WSYNC
        sta HMOVE
        lda SKY_DUSK,x
        sta COLUBK
        lda TXT0,y
        sta PF0
        lda TXT1,y
        sta PF1
        lda TXT2,y
        sta PF2
        lda TXT3,y
        sta PF0
        lda TXT4,y
        sta PF1
        lda TXT5,y
        sta PF2
        .endrepeat
        iny
        dec tmp2
        beq done
        jmp row
done:
.endmacro

; 20 lines: the two digits at dptr and dptr+2, 4 lines a row (Y from 0).
.macro DIGITS2
        .local row
        lda #5
        sta tmp2
row:
        .repeat 4
        sta WSYNC
        sta HMOVE
        lda SKY_DUSK,x
        sta COLUBK
        lda (dptr),y
        sta GRP0
        lda (dptr+2),y
        sta GRP1
        .endrepeat
        iny
        dec tmp2
        bne row
        lda #0
        sta GRP0
        sta GRP1
.endmacro

KernelTitle:
        sta WSYNC               ; line 0
        sta HMOVE
        lda #0
        sta VBLANK
        sta CTRLPF
        sta GRP0
        sta GRP1
        lda #$0E
        sta COLUPF
        ldx #119
        SKY 23
        ldy #TX_TITLE
        TEXT
        SKY 30
        lda sel                 ; the song's name
        sta tmp
        asl
        asl
        adc tmp
        adc #TX_NAME0
        tay
        TEXT
        SKY 10
        ldy #TX_BLANK           ; its star
        lda sel
        tay
        lda BIT8_1,y
        and stars
        beq @ns
        ldy #TX_PERFECT
        .byte $2C
@ns:    ldy #TX_BLANK
        TEXT
        SKY 28
        lda hill_col
        sta COLUPF
        lda #1
        sta CTRLPF
        jmp Hills

BIT8_1: .byte $01, $02, $04, $08, $10, $20, $40, $80

KernelResult:
        sta WSYNC               ; line 0
        sta HMOVE
        lda #0
        sta VBLANK
        sta CTRLPF
        sta GRP0
        sta GRP1
        sta NUSIZ0
        sta NUSIZ1
        lda #$0E
        sta COLUPF
        ldx #119
        SKY 30
        ldy result
        lda RESULT_TX,y
        tay
        TEXT
        SKY 20
        lda #$1E                ; chimes caught, in gold
        sta COLUP0
        sta COLUP1
        ldy #0
        DIGITS2
        SKY 10
        lda #$0E                ; of the song's chimes, in white
        sta COLUP0
        sta COLUP1
        lda dptr+4
        sta dptr
        lda dptr+5
        sta dptr+1
        lda dptr+6
        sta dptr+2
        lda dptr+7
        sta dptr+3
        ldy #0
        DIGITS2
        SKY 31
        lda hill_col
        sta COLUPF
        lda #1
        sta CTRLPF
        jmp Hills

RESULT_TX: .byte TX_AGAIN, TX_CLEAR, TX_PERFECT

; ---- Bank 1's trampoline to bank 0, and its reset ----
        .segment "TRAMP1"
CallBank0:
        sta $FFF8               ; $FFE0: to bank 0, which goes on at $FFE3
        .res 6, $EA
        rts                     ; $FFE9: back from bank 0

        .segment "VEC1"
        sta $FFF9               ; $FFF0
        jmp Start               ; $FFF3
        .res 4, $FF
        .word $FFF0, $FFF0, $FFF0
