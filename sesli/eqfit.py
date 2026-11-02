"""Fit the 5-band EQ so the voice (after noise removal) matches the Discord tonal target."""
import json, os
import numpy as np
from scipy import signal, optimize

from dsp import SR
from biquad import eq_sos

HERE = os.path.dirname(os.path.abspath(__file__))
from paths import res
TARGET = json.load(open(res('target.json')))
CS = np.array(TARGET['bands'])
T_LTAS = np.array(TARGET['ltas'])


def ltas(x, frame_db_floor):
    """1/3-octave long-term spectrum of speech frames (10 ms frames above floor), 0 dB at 300-3k."""
    n = 480
    k = len(x) // n
    fr = x[:k * n].reshape(k, n)
    lv = 10 * np.log10((fr ** 2).mean(1) + 1e-14)
    seg = fr[lv > frame_db_floor].ravel()
    if len(seg) < SR * 3:
        raise ValueError('not enough speech captured')
    f, P = signal.welch(seg, SR, nperseg=4096)
    out = []
    for c in CS:
        m = (f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))
        out.append(10 * np.log10(P[m].mean() + 1e-20))
    out = np.array(out)
    ref = (CS >= 300) & (CS <= 3000)
    return out - out[ref].mean()


def eq_from(v):
    return [['lowshelf', v[0], v[1], 0.7], ['peak', v[2], v[3], v[4]], ['peak', v[5], v[6], v[7]],
            ['peak', v[8], v[9], v[10]], ['highshelf', v[11], v[12], 0.7]]


def fit(measured_ltas):
    use = (CS >= 80) & (CS <= 12500)
    mid = (CS[use] >= 300) & (CS[use] <= 3000)
    t = (T_LTAS - measured_ltas)[use]
    t = t - t[mid].mean()

    def loss(v):
        _, h = signal.sosfreqz(eq_sos([tuple(e) for e in eq_from(v)], SR), worN=CS[use], fs=SR)
        e = 20 * np.log10(np.abs(h)) - t
        e = e - e[mid].mean()
        return (e ** 2).mean() + 0.002 * np.sum(np.array(v)[[1, 3, 6, 9, 12]] ** 2)

    v0 = [120, 0, 700, 0, 1, 3500, -2, 0.8, 8000, -3, 2, 10000, 0]
    lo = [40, -12, 200, -12, 0.3, 1500, -12, 0.3, 5000, -12, 0.5, 6000, -12]
    hi = [300, 12, 1500, 12, 4, 6000, 12, 4, 11000, 12, 6, 16000, 12]
    r = optimize.minimize(loss, v0, bounds=list(zip(lo, hi)), method='L-BFGS-B')
    eq = [[k, float(f), float(g), float(q)] for k, f, g, q in eq_from(r.x)]
    return eq, float(np.sqrt(r.fun)), float(np.sqrt((t ** 2).mean()))


def bass_ratio_target():
    """Discord target: median of (80-250 Hz level - 300-3000 Hz level) over speech blocks,
    measured with the assistant's own filters (stored in target.json)."""
    return float(TARGET['bass_mid_db'])
