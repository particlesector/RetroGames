"""Headless NES harness: drives a libretro core (Nestopia) through ctypes.

    emu = Emu("game.nes"); emu.frame(A | RIGHT); emu.ram[0x10]; emu.screenshot().save("x.png")
"""
import ctypes as C, os
import numpy as np
from PIL import Image

B, Y, SELECT, START, UP, DOWN, LEFT, RIGHT, A = (1 << i for i in range(9))
CORE = os.environ.get("NES_CORE", "/usr/lib/x86_64-linux-gnu/libretro/nestopia_libretro.so")

class GameInfo(C.Structure):
    _fields_ = [("path", C.c_char_p), ("data", C.c_void_p), ("size", C.c_size_t), ("meta", C.c_char_p)]

class Emu:
    def __init__(self, rom, core=CORE):
        self.lib = lib = C.CDLL(core)
        self.pixfmt, self.pad, self.frame_img, self.audio = 0, 0, None, []
        self.record_audio = False
        self._sysdir = C.c_char_p(os.environ.get("TMPDIR", "/tmp").encode())
        ENV = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
        VID = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
        AUD = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
        AUDB = C.CFUNCTYPE(C.c_size_t, C.POINTER(C.c_int16), C.c_size_t)
        POLL = C.CFUNCTYPE(None)
        INP = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)
        def env(cmd, data):
            if cmd == 10:
                self.pixfmt = C.cast(data, C.POINTER(C.c_int))[0]; return True
            if cmd in (9, 31):     # system / save directory: the core insists on one
                C.cast(data, C.POINTER(C.c_char_p))[0] = self._sysdir; return True
            return False
        def vid(data, w, h, pitch):
            if not data: return
            buf = np.ctypeslib.as_array(C.cast(data, C.POINTER(C.c_uint8)), shape=(h, pitch))
            if self.pixfmt == 1:   # XRGB8888
                a = buf[:, :w * 4].reshape(h, w, 4)[:, :, [2, 1, 0]]
            else:                  # RGB565
                p = buf[:, :w * 2].copy().view(np.uint16).reshape(h, w)
                a = np.stack([(p >> 11) << 3, ((p >> 5) & 63) << 2, (p & 31) << 3], -1).astype(np.uint8)
            self.frame_img = a.copy()
        def audb(data, n):
            if self.record_audio:
                self.audio.append(np.ctypeslib.as_array(data, shape=(n * 2,)).copy())
            return n
        def inp(port, dev, idx, id_):
            return 1 if port == 0 and dev == 1 and id_ < 16 and (self.pad >> id_) & 1 else 0
        self._cbs = [ENV(env), VID(vid), AUD(lambda l, r: None), AUDB(audb), POLL(lambda: None), INP(inp)]
        lib.retro_set_environment(self._cbs[0]); lib.retro_set_video_refresh(self._cbs[1])
        lib.retro_set_audio_sample(self._cbs[2]); lib.retro_set_audio_sample_batch(self._cbs[3])
        lib.retro_set_input_poll(self._cbs[4]); lib.retro_set_input_state(self._cbs[5])
        lib.retro_init()
        self._rom = open(rom, "rb").read()
        gi = GameInfo(rom.encode(), C.cast(C.c_char_p(self._rom), C.c_void_p), len(self._rom), None)
        lib.retro_load_game.argtypes = [C.POINTER(GameInfo)]; lib.retro_load_game.restype = C.c_bool
        assert lib.retro_load_game(C.byref(gi)), "core refused ROM"
        lib.retro_set_controller_port_device(0, 1)      # standard pad in port 1
        lib.retro_get_memory_data.restype = C.c_void_p; lib.retro_get_memory_size.restype = C.c_size_t
        n = lib.retro_get_memory_size(2)
        self.ram = np.ctypeslib.as_array(C.cast(lib.retro_get_memory_data(2), C.POINTER(C.c_uint8)), shape=(n,))
        self.frames = 0

    def frame(self, pad=0, n=1):
        self.pad = pad
        for _ in range(n):
            self.lib.retro_run(); self.frames += 1

    def screenshot(self, scale=1):
        im = Image.fromarray(self.frame_img)
        return im.resize((im.width * scale, im.height * scale), Image.NEAREST) if scale > 1 else im

def labels(path):
    """Parse an ld65 -Ln label file into {name: address}."""
    d = {}
    for line in open(path):
        p = line.split()
        if len(p) == 3 and p[0] == "al": d[p[2].lstrip(".")] = int(p[1], 16)
    return d
