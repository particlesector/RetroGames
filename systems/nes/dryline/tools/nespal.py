"""NES master palette (approximate 2C02 RGB values) and the colour roles DRYLINE's tools draw with."""
import numpy as np

_rows = [
 "626262 001FB2 2404C8 5200B2 730076 800024 730B00 522800 244400 005700 005C00 005324 003C76 000000 000000 000000",
 "ABABAB 0D57FF 4B30FF 8A13FF BC08D6 D21269 C72E00 9D5400 607B00 209800 00A300 009942 007DB4 000000 000000 000000",
 "FFFFFF 53AEFF 9085FF D365FF FF57FF FF5DCF FF7757 FA9E00 BDC700 7AE700 43F611 26EF7E 2CD5F6 4E4E4E 000000 000000",
 "FFFFFF B6E1FF CED1FF E9C3FF FFBCFF FFBDF4 FFC6C3 FFD59A E9E681 CEF481 B6FB9A A9FAC3 A9F0F4 B8B8B8 000000 000000"]
NES = np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)] for r in _rows for h in r.split()], dtype=np.int32)

# pixel roles used while drawing a circuit
G, GD, GL, SA, RO, DR, WH, RE, WA, WL = range(10)
ROLES = ["GRASS", "GDARK", "GLIGHT", "SAND", "ROAD", "DRIED", "WHITE", "RED", "WATER", "WLIGHT"]

# background palettes as roles. Entry 0 is the shared backdrop.
#   0 kerbs    1 nature    2 water    3 road (entry 3 = tarmac the cars have dried)
PALS = [[G, RO, WH, RE], [G, GD, GL, SA], [G, WA, WL, WH], [G, RO, WH, DR]]

# theme -> role -> NES colour, in fair weather and in rain. In rain ROAD is the dark wet
# surface and DRIED is the normal tarmac colour, so the dry line appears by itself.
THEMES = {
    "meadow": (dict(GRASS=0x1A, GDARK=0x0A, GLIGHT=0x2A, SAND=0x38, ROAD=0x00, DRIED=0x00, WHITE=0x30, RED=0x16, WATER=0x11, WLIGHT=0x21),
               dict(GRASS=0x0A, GDARK=0x09, GLIGHT=0x1A, SAND=0x28, ROAD=0x0C, DRIED=0x00, WHITE=0x30, RED=0x16, WATER=0x01, WLIGHT=0x11)),
}

def palette_bytes(theme, rain):
    roles = THEMES[theme][1 if rain else 0]
    return [roles[ROLES[r]] for p in PALS for r in p]
