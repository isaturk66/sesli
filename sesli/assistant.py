"""Setup assistant logic: measures noise, speech, peaks and bass build-up from the raw mic,
then plans the placement + gain that gives the best quality you are comfortable with.

Model (why this works without knowing centimetres):
- Moving the mic changes your voice level at the mic; the room noise stays the same. So the
  voice-to-noise ratio (SNR) depends on distance only, and a level change of +X dB at fixed gain
  means you moved X dB "closer" (6 dB = half the distance).
- The gain knob moves voice and noise together; it only sets where the loud peaks land.
So: first choose distance by SNR and bass build-up (unless you lock it), then set gain so your
loudest moments peak around -10 dBFS.
"""
import numpy as np
from scipy import signal

from dsp import SR, BLOCK
import eqfit

SNR_GREAT = 30.0      # dB, speech (>80 Hz, 90th pct) over noise (>150 Hz, median)
SNR_OK = 25.0
PEAK_TARGET = -10.0   # dBFS for the loudest moments
LEVEL_TOL = 1.5       # dB window for live guidance
MAX_CLOSER = 9.0      # never ask for more than ~1/3 of the distance
MAX_BACK = 6.0       # (x2 allowed when the mic is extremely close)
BASS_EXCESS = 6.0     # dB over the target's 80-250 Hz level = too close (proximity boom)
SNR_TOO_CLOSE = 40.0  # dB: this far above the room means the mic is very close (boom, pops, clipping)
SNR_BACK_TO = 34.0    # where to aim when backing off: still very clean


class Analyzer:
    """Turns raw 10 ms blocks into per-block measurements."""

    def __init__(self):
        mk = lambda *a, **k: signal.butter(*a, fs=SR, output='sos', **k)
        self.f80 = mk(4, 80, 'highpass'); self.z80 = np.zeros((2, 2))
        self.f150 = mk(4, 150, 'highpass'); self.z150 = np.zeros((2, 2))
        self.fb = mk(2, [80, 250], 'bandpass'); self.zb = np.zeros((2, 2))
        self.fm = mk(2, [300, 3000], 'bandpass'); self.zm = np.zeros((2, 2))

    def block(self, x):
        a, self.z80 = signal.sosfilt(self.f80, x, zi=self.z80)
        b, self.z150 = signal.sosfilt(self.f150, x, zi=self.z150)
        c, self.zb = signal.sosfilt(self.fb, x, zi=self.zb)
        d, self.zm = signal.sosfilt(self.fm, x, zi=self.zm)
        L = lambda s: 10 * np.log10((s ** 2).mean() + 1e-14)
        pk = float(np.abs(x).max())
        return dict(l80=L(a), l150=L(b), bass=L(c), mid=L(d), peak=pk)


def flat_top_clipped(peaks_raw):
    """peaks_raw: concatenated raw audio; clipping = many samples stuck at the same max value."""
    a = np.abs(peaks_raw)
    m = a.max()
    return bool(m > 0.98 or (a >= m * 0.9999).sum() > 20)


def summarize(silence, talk, loud, raw_talk_loud):
    N = float(np.median([b['l150'] for b in silence[50:]]))
    lv = np.array([b['l80'] for b in talk])
    S = float(np.percentile(lv, 90))
    speechy = [b for b in talk + loud if b['l80'] > N + 12]
    bass = float(np.median([b['bass'] - b['mid'] for b in speechy])) if speechy else 0.0
    P = 20 * np.log10(max(b['peak'] for b in talk + loud) + 1e-9)
    clipped = flat_top_clipped(raw_talk_loud)
    K = float(np.clip(P - S, 8, 25))
    if clipped:
        K = max(K, 18.0)  # the real peak was higher than we could see
    return dict(noise=N, speech=S, peak=P, crest=K, clipped=clipped, snr=S - N, bass=bass)


def plan(m, locked):
    """Return the move (dB, + = closer) and the target speech level for the gain step."""
    snr = m['snr']
    bass_excess = m['bass'] - eqfit.bass_ratio_target()
    move, why = 0.0, ''
    if not locked:
        if snr < SNR_GREAT:
            move = min(SNR_GREAT - snr, MAX_CLOSER)
            why = 'closer'
        else:
            # too close shows up as any of: far more voice-over-room than needed, proximity boom,
            # or clipping while the voice is already very clean. Back off, but keep SNR >= SNR_BACK_TO.
            back = 0.0
            if snr > SNR_TOO_CLOSE:
                back = max(back, snr - SNR_BACK_TO)
            if bass_excess > BASS_EXCESS:
                back = max(back, bass_excess - BASS_EXCESS)
            if m['clipped'] and snr > SNR_BACK_TO + 2:
                back = max(back, 6.0)
            back = min(back, snr - SNR_BACK_TO, MAX_BACK * 2)
            if back > 0:
                move, why = -back, 'back'
        if abs(move) < 1.5:
            move, why = 0.0, ''
    target_speech = PEAK_TARGET - m['crest']
    expected_snr = snr + move
    if expected_snr >= SNR_GREAT:
        quality = 'great'
    elif expected_snr >= SNR_OK:
        quality = 'good'
    else:
        quality = 'ok'  # noise removal works harder; small quality hit
    return dict(move=move, why=why, target_speech=target_speech, expected_snr=expected_snr,
                quality=quality, bass_excess=bass_excess)


def distance_hint(move_db):
    r = 10 ** (-move_db / 20)
    return r, f'about {r * 100:.0f}% of your current distance (e.g. 20 cm → {20 * r:.0f} cm)'


class LiveLevel:
    """Rolling 'how loud is your talking right now' (90th pct of the last 1.5 s of speech blocks)."""

    def __init__(self, noise_db):
        self.noise = noise_db
        self.buf = []

    def push(self, b):
        if b['l80'] > self.noise + 10:
            self.buf.append(b['l80'])
            self.buf = self.buf[-150:]

    def value(self):
        return float(np.percentile(self.buf, 90)) if len(self.buf) > 40 else None
