"""Headless Atari 2600 harness: drives Stella's libretro core through ctypes.

    emu = Emu("game.F8"); emu.frame(UP | FIRE); emu.ram[0x10]; emu.screenshot().save("x.png")

`ram` is the console's 128 bytes ($80-$FF): ram[addr - 0x80]. Joystick bits as Stella's core
maps a joypad: FIRE is B, RESET is Start, SELECT is Select. Needs only Pillow (no numpy).
STELLA_CORE names the core (default: Debian's libretro-stella package).
"""
import ctypes as C
import os
import struct
import wave

from PIL import Image

FIRE, _, SELECT, RESET, UP, DOWN, LEFT, RIGHT = (1 << i for i in range(8))
CORE = os.environ.get("STELLA_CORE", "/usr/lib/x86_64-linux-gnu/libretro/stella_libretro.so")


class AVInfo(C.Structure):
    _fields_ = [("base_w", C.c_uint), ("base_h", C.c_uint), ("max_w", C.c_uint), ("max_h", C.c_uint),
                ("aspect", C.c_float), ("fps", C.c_double), ("rate", C.c_double)]


class GameInfo(C.Structure):
    _fields_ = [("path", C.c_char_p), ("data", C.c_void_p), ("size", C.c_size_t), ("meta", C.c_char_p)]


class Emu:
    _live = None    # a core holds one game: a new Emu closes the last

    def __init__(self, rom, core=CORE):
        if Emu._live is not None:
            Emu._live.close()
        Emu._live = self
        self.lib = lib = C.CDLL(core)
        self.pixfmt, self.pad, self.frame_img = 0, 0, None
        self.audio = bytearray()
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
                self.pixfmt = C.cast(data, C.POINTER(C.c_int))[0]
                return True
            if cmd in (9, 31):
                C.cast(data, C.POINTER(C.c_char_p))[0] = self._sysdir
                return True
            return False

        def vid(data, w, h, pitch):
            if not data:
                return
            raw = C.string_at(data, h * pitch)
            if self.pixfmt == 1:      # XRGB8888
                rows = [raw[y * pitch:y * pitch + 4 * w] for y in range(h)]
                img = Image.frombytes("RGB", (w, h), b"".join(rows), "raw", "BGRX")
            else:                     # RGB565
                rows = [raw[y * pitch:y * pitch + 2 * w] for y in range(h)]
                img = Image.frombytes("RGB", (w, h), b"".join(rows), "raw", "BGR;16")
            self.frame_img = img

        def audb(data, n):
            if self.record_audio:
                self.audio += C.string_at(data, 4 * n)
            return n

        def inp(port, dev, idx, id_):
            return 1 if port == 0 and dev == 1 and id_ < 16 and (self.pad >> id_) & 1 else 0

        self._cbs = [ENV(env), VID(vid), AUD(lambda l, r: None), AUDB(audb), POLL(lambda: None), INP(inp)]
        lib.retro_set_environment(self._cbs[0])
        lib.retro_set_video_refresh(self._cbs[1])
        lib.retro_set_audio_sample(self._cbs[2])
        lib.retro_set_audio_sample_batch(self._cbs[3])
        lib.retro_set_input_poll(self._cbs[4])
        lib.retro_set_input_state(self._cbs[5])
        lib.retro_init()
        self._rom = open(rom, "rb").read()
        gi = GameInfo(rom.encode(), C.cast(C.c_char_p(self._rom), C.c_void_p), len(self._rom), None)
        lib.retro_load_game.argtypes = [C.POINTER(GameInfo)]
        lib.retro_load_game.restype = C.c_bool
        assert lib.retro_load_game(C.byref(gi)), "core refused ROM"
        lib.retro_set_controller_port_device(0, 1)
        av = AVInfo()
        lib.retro_get_system_av_info(C.byref(av))
        self.fps, self.rate = av.fps, av.rate
        lib.retro_get_memory_data.restype = C.c_void_p
        lib.retro_get_memory_size.restype = C.c_size_t
        n = lib.retro_get_memory_size(2)
        self.ram = (C.c_uint8 * n).from_address(lib.retro_get_memory_data(2))
        self.frames = 0

    def close(self):
        if Emu._live is self:
            self.lib.retro_unload_game()
            self.lib.retro_deinit()
            Emu._live = None

    def frame(self, pad=0, n=1):
        self.pad = pad
        for _ in range(n):
            self.lib.retro_run()
            self.frames += 1

    def screenshot(self):
        return self.frame_img

    def save_audio(self, path, rate=None):
        """The recorded sound (16-bit stereo, as the core gives it) as a WAV."""
        rate = int(round(rate or self.rate))
        with wave.open(path, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(bytes(self.audio))


def labels(path):
    """Parse an ld65 -Ln label file into {name: address}."""
    d = {}
    for line in open(path):
        p = line.split()
        if len(p) == 3 and p[0] == "al":
            d[p[2].lstrip(".")] = int(p[1], 16)
    return d
