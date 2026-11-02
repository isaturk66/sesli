"""Streaming version of the chain (same blocks as ../chain.py), processed in 10 ms blocks at 48 kHz.
HPF -> DeepFilterNet -> EQ -> expander -> AGC -> limiter. All state is kept between blocks."""
import numpy as np
from scipy import signal

from biquad import eq_sos
from df_native import DeepFilter

SR = 48000
BLOCK = 480
SUB = 48  # 1 ms control-rate sub-blocks


def db(x):
    return 20 * np.log10(np.maximum(x, 1e-9))


class Chain:
    def __init__(self, profile):
        self.p = profile
        self.hpf = signal.butter(4, 80, 'highpass', fs=SR, output='sos')
        self.hpf_zi = np.zeros((self.hpf.shape[0], 2))
        self.set_eq(profile['eq'])
        self.set_character(profile.get('character_eq') or [])
        self.char_bypass = False  # tune-by-ear records the voice without the current character
        self.dfn = DeepFilter(atten_lim_db=profile.get('nr_atten_db', 100.0), post_filter_beta=0.02)
        # expander
        self.exp_env = 0.0
        self.exp_g = 1.0
        self.exp_at = np.exp(-1 / (1000 * 5 / 1000))     # per-ms coefficients
        self.exp_re = np.exp(-1 / (1000 * 120 / 1000))
        # agc
        self.agc_gain_db = profile.get('agc_start_db', 0.0)
        self.agc_hist = []
        self.agc_g_prev = 10 ** (self.agc_gain_db / 20)
        # limiter
        self.lim_g = 1.0
        self.lim_re = np.exp(-1 / (1000 * 80 / 1000))
        self.enabled = True

    def set_eq(self, eq):
        self.eq = eq_sos([tuple(e) for e in eq], SR) if eq else None
        self.eq_zi = np.zeros((self.eq.shape[0], 2)) if self.eq is not None else None

    def set_character(self, eq):
        """Voice character from "Tune by ear" (on top of the calibrated EQ). Empty = none."""
        self.char = eq_sos([tuple(e) for e in eq], SR) if eq else None
        self.char_zi = np.zeros((self.char.shape[0], 2)) if self.char is not None else None

    def set_strength(self, atten_db):
        self.p['nr_atten_db'] = atten_db
        self.dfn.set_atten(atten_db)

    def hp(self, x):
        y, self.hpf_zi = signal.sosfilt(self.hpf, x, zi=self.hpf_zi)
        return y

    def post_nr(self, x):
        """HPF + DeepFilterNet only (used by calibration to measure the voice before EQ)."""
        return self.dfn.process(self.hp(x).astype(np.float32))

    def process(self, x):
        """x: float32[BLOCK] raw mic. Returns (out, post_nr)."""
        n = self.post_nr(x)
        if not self.enabled:
            return np.clip(x, -1, 1).astype(np.float32), n  # processing off: raw mic passes through
        y = n.astype(np.float64)
        if self.eq is not None:
            y, self.eq_zi = signal.sosfilt(self.eq, y, zi=self.eq_zi)
        if self.char is not None and not self.char_bypass:
            y, self.char_zi = signal.sosfilt(self.char, y, zi=self.char_zi)
        y = self._expander(y)
        y = self._agc(y)
        y = self._limiter(y)
        return y.astype(np.float32), n

    def _ramp(self, g_prev, g_new):
        return np.linspace(g_prev, g_new, SUB, endpoint=False)

    def _expander(self, y):
        thr = self.p['exp_thresh_db']
        out = np.empty_like(y)
        for i in range(0, len(y), SUB):
            s = y[i:i + SUB]
            lvl = np.abs(s).max()
            c = self.exp_at if lvl > self.exp_env else self.exp_re
            self.exp_env = c * self.exp_env + (1 - c) * lvl
            under = min(db(self.exp_env) - thr, 0.0)
            g = 10 ** (max(under * 2.0, -40.0) / 20)  # ratio 3 -> slope 2, 40 dB range
            out[i:i + SUB] = s * self._ramp(self.exp_g, g)
            self.exp_g = g
        return out

    def _agc(self, y):
        self.agc_hist.append(float((y ** 2).mean()))
        if len(self.agc_hist) > 40:
            self.agc_hist.pop(0)
        lvl = 10 * np.log10(np.mean(self.agc_hist) + 1e-14)
        if lvl > self.p['agc_gate_db']:
            err = self.p['agc_target_db'] - (lvl + self.agc_gain_db)
            self.agc_gain_db += float(np.clip(err, -0.015, 0.015))  # 1.5 dB/s
            self.agc_gain_db = float(np.clip(self.agc_gain_db, -12, 12))
        g = 10 ** (self.agc_gain_db / 20)
        out = y * np.linspace(self.agc_g_prev, g, len(y), endpoint=False)
        self.agc_g_prev = g
        return out

    def _limiter(self, y):
        c = 10 ** (-1.0 / 20)
        out = np.empty_like(y)
        for i in range(0, len(y), SUB):
            s = y[i:i + SUB]
            need = min(1.0, c / max(np.abs(s).max(), 1e-9))
            g = need if need < self.lim_g else self.lim_re * self.lim_g + (1 - self.lim_re) * need
            # attack must be instant inside the sub-block: use the smaller gain for the whole sub-block
            out[i:i + SUB] = s * min(g, self.lim_g) if need < self.lim_g else s * self._ramp(self.lim_g, g)
            self.lim_g = g
        return np.clip(out, -0.999, 0.999)
