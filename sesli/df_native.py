"""DeepFilterNet through its synchronous C API (deepfilter.dll, built from DeepFilterNet's libDF with the
'capi' feature). One call = one 10 ms frame, computed right there: no hidden threads, no timers, so it
cannot fall behind silently. If a frame ever takes too long, the engine notices and copes."""
import ctypes as C
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
from paths import res
DLL = res('bin', 'deepfilter.dll')
MODEL = res('models', 'DeepFilterNet3_onnx.tar.gz')


class DeepFilter:
    def __init__(self, atten_lim_db=100.0, post_filter_beta=0.02, model=MODEL):
        self.lib = C.CDLL(DLL)
        self.lib.df_create.restype = C.c_void_p
        self.lib.df_create.argtypes = [C.c_char_p, C.c_float]
        self.lib.df_get_frame_length.restype = C.c_size_t
        self.lib.df_get_frame_length.argtypes = [C.c_void_p]
        self.lib.df_set_atten_lim.argtypes = [C.c_void_p, C.c_float]
        self.lib.df_set_post_filter_beta.argtypes = [C.c_void_p, C.c_float]
        self.lib.df_process_frame.restype = C.c_float
        self.lib.df_process_frame.argtypes = [C.c_void_p, C.POINTER(C.c_float), C.POINTER(C.c_float)]
        self.st = self.lib.df_create(model.encode(), float(atten_lim_db))
        self.hop = int(self.lib.df_get_frame_length(self.st))
        self.lib.df_set_post_filter_beta(self.st, float(post_filter_beta))
        self.inb = np.zeros(self.hop, np.float32)
        self.outb = np.zeros(self.hop, np.float32)
        self.pi = self.inb.ctypes.data_as(C.POINTER(C.c_float))
        self.po = self.outb.ctypes.data_as(C.POINTER(C.c_float))
        self.lsnr = 0.0

    def set_atten(self, db):
        self.lib.df_set_atten_lim(self.st, float(db))

    def process(self, x):
        """x: float32 array, length a multiple of the hop (480 at 48 kHz)."""
        out = np.empty(len(x), np.float32)
        for i in range(0, len(x), self.hop):
            self.inb[:] = x[i:i + self.hop]
            self.lsnr = self.lib.df_process_frame(self.st, self.pi, self.po)
            out[i:i + self.hop] = self.outb
        return out
