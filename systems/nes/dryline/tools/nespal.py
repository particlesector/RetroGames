"""NES master palette (approximate 2C02 RGB values) and the colour roles DRYLINE's tools draw with."""
import numpy as np

_rows = [
 "626262 001FB2 2404C8 5200B2 730076 800024 730B00 522800 244400 005700 005C00 005324 003C76 000000 000000 000000",
 "ABABAB 0D57FF 4B30FF 8A13FF BC08D6 D21269 C72E00 9D5400 607B00 209800 00A300 009942 007DB4 000000 000000 000000",
 "FFFFFF 53AEFF 9085FF D365FF FF57FF FF5DCF FF7757 FA9E00 BDC700 7AE700 43F611 26EF7E 2CD5F6 4E4E4E 000000 000000",
 "FFFFFF B6E1FF CED1FF E9C3FF FFBCFF FFBDF4 FFC6C3 FFD59A E9E681 CEF481 B6FB9A A9FAC3 A9F0F4 B8B8B8 000000 000000"]
NES = np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)] for r in _rows for h in r.split()], dtype=np.int32)

# pixel roles used while drawing a circuit
G, GD, GL, SA, RO, WH, RE, WA, WL, WW, K, GY, AC = range(13)
ROLES = ["GROUND", "GDARK", "GLIGHT", "SAND", "ROAD", "WHITE", "KERB", "WATER", "WLIGHT", "WWHITE", "BLACK", "GREY", "ACCENT"]

# Background palettes as roles. Entry 0 is the shared backdrop (the ground).
#   0 road: tarmac, paint, kerb. In rain the kerb colour becomes "dried tarmac", which is
#     what lets one palette show both the wet road and the dry line.
#   1 nature   2 water   3 structures and the HUD
PALS = [[G, RO, WH, RE], [G, GD, GL, SA], [G, WA, WL, WW], [G, K, GY, AC]]

# theme -> role -> NES colour, fair weather then rain
THEMES = {
    "meadow": (dict(GROUND=0x1A, GDARK=0x0A, GLIGHT=0x2A, SAND=0x38, ROAD=0x00, WHITE=0x30, KERB=0x16,
                    WATER=0x11, WLIGHT=0x21, WWHITE=0x30, BLACK=0x0F, GREY=0x10, ACCENT=0x28),
               dict(GROUND=0x0A, GDARK=0x09, GLIGHT=0x1A, SAND=0x28, ROAD=0x0C, WHITE=0x30, KERB=0x00,
                    WATER=0x01, WLIGHT=0x11, WWHITE=0x21, BLACK=0x0F, GREY=0x10, ACCENT=0x28)),
}

def palette_bytes(theme, rain):
    roles = THEMES[theme][1 if rain else 0]
    return [roles[ROLES[r]] for p in PALS for r in p]
