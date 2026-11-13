; Hardware registers, constants and RAM layout.

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

BANK_RACE0 = 0
BANK_RACE1 = 1
BANK_MENU = 2
BANK_TRK0 = 4
BANK_MUSIC = 8

CHR_SPRITES = 4             ; first 1 KB page of the sprite tiles
CHR_TRACKS = 8              ; first page of circuit 0; each circuit has TRACK_PAGES pages

MASK_ON = $1E
TOP = 32                    ; first scanline of the track area
NCARS = 4

; The MMC3 counter value for a split at scanline S is S + IRQ_FIRST for the first
; split of a frame and (S - previous S) + IRQ_NEXT for later ones. Found by
; comparing the picture with the reference image (tests/test_picture.py).
IRQ_FIRST = 256 - 1
IRQ_NEXT = 256 - 1

oam = $0200

; battery RAM
wetmap  = $6000             ; one byte per 8x8 tile: bit 7 can dry, bit 6 kerb-cell tile, bits 0-1 dryness
surface = $6400             ; 2 bits per 4x4 pixels: 0 road, 1 grass, 2 gravel, 3 solid
wp_x    = $6800             ; racing line: MAXWP waypoints, four parallel arrays
wp_y    = wp_x + 96
wp_a    = wp_y + 96         ; heading towards the next waypoint
wp_s    = wp_a + 96         ; speed limit in 1/64 pixel per frame

.segment "ZEROPAGE"
tmp0:        .res 1
tmp1:        .res 1
tmp2:        .res 1
tmp3:        .res 1
ptr0:        .res 2
ptr1:        .res 2
cnt:         .res 2
nmi_ready:   .res 1
frame_count: .res 1
ppumask_s:   .res 1
ppuctrl_s:   .res 1
split_on:    .res 1
irq_idx:     .res 1
irq_bank:    .res 1
pal_dirty:   .res 1
vb_pos:      .res 1
pad:         .res 2
pad_new:     .res 2
pad_prev:    .res 2
state:       .res 1
oam_i:       .res 1
d_x:         .res 1
d_y:         .res 1
d_frame:     .res 1
d_attr:      .res 1
addr_hi:     .res 1
addr_lo:     .res 1
cur_track:   .res 1
car:         .res 1         ; index of the car being updated
m_a:         .res 1         ; multiply scratch
m_b:         .res 1
prod:        .res 2
bv:          .res 2         ; blend scratch: a velocity component
bd:          .res 2
gshift:      .res 1
nxl:         .res 1
nxh:         .res 1
nyl:         .res 1
nyh:         .res 1
sgn:         .res 1
demo:        .res 1

.segment "BSS"
vbuf:        .res 96        ; NMI VRAM queue: hi, lo, len, data..., 0
pal_buf:     .res 32
pal_fair:    .res 16
pal_rain:    .res 16
track_name:  .res 17
band_count:  .res 1
band_split:  .res 3
band_page:   .res 4
band_latch:  .res 4         ; last entry stays 0
track_laps:  .res 1
grid_xy:     .res 8         ; x,y for each grid slot
grid_ang:    .res 1

.macro PRINT col, row, str
    lda #<(str)
    sta ptr0
    lda #>(str)
    sta ptr0+1
    ldx #(col)
    ldy #(row)
    jsr puts_xy
.endmacro
