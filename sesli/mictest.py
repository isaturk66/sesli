"""Test my mic: record 10 s, then switch between the original mic and Sesli's output at the same moment.
Labeled (it's a demo, not a test). Both play exactly as they are: the raw mic as it comes in, and the
final audio others receive (level included)."""
import queue, time
import tkinter as tk
import numpy as np
from scipy import signal

from i18n import T
from tuner import (LoopPlayer, Timeline, SR, COUNT_IN, BG, CARD, INK, MUTE, LINE, ACC, BAD, SOFT,
                   FONT, BIG, HUGE)

REC_SECONDS = 10
MAX_LAG = int(0.15 * SR)  # the noise remover delays the output a little; align within ±150 ms


def prepare(raw, out):
    """Align the original to Sesli's output (the noise remover adds a little latency). Levels stay as they are."""
    hp = signal.butter(2, 150, 'highpass', fs=SR, output='sos')
    a, b = signal.sosfilt(hp, raw), signal.sosfilt(hp, out)
    n = len(a)
    c = signal.correlate(b, a, mode='full', method='fft')[n - 1:n - 1 + MAX_LAG]  # out lags raw by 0..MAX_LAG
    lag = int(np.argmax(c))
    raw = np.concatenate([np.zeros(lag), raw[:n - lag]])
    return np.clip(raw, -1, 1).astype(np.float32), out.astype(np.float32)


class MicTest(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app, self.e = app, app.engine
        self.title(T('test_title'))
        self.configure(bg=BG)
        self.resizable(False, False)
        try:
            from paths import res
            self.iconbitmap(res('assets', 'icon.ico'))
        except Exception:
            pass
        self.card = tk.Frame(self, bg=CARD, highlightbackground=LINE, highlightthickness=1, width=500, height=380)
        self.card.pack(padx=14, pady=14)
        self.card.pack_propagate(False)
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.bind('1', lambda e: self.switch(0))
        self.bind('2', lambda e: self.switch(1))
        self.bind('<space>', lambda e: self.play_pause())
        self.player = None
        self.tap = None
        self.intro()

    def clear(self):
        for w in self.card.winfo_children():
            w.destroy()

    def label(self, text, font=FONT, fg=INK, pady=4):
        lab = tk.Label(self.card, text=text, font=font, bg=CARD, fg=fg, wraplength=460, justify='left')
        lab.pack(anchor='w', padx=20, pady=pady)
        return lab

    def button(self, parent, text, cmd, primary=True, **pack):
        b = tk.Button(parent, text=text, font=FONT, relief='flat', padx=12, pady=7, cursor='hand2', command=cmd,
                      bg=ACC if primary else SOFT, fg='white' if primary else INK,
                      activebackground=ACC if primary else SOFT)
        b.pack(**pack)
        return b

    def close(self):
        if self.tap is not None:
            self.e.remove_tap(self.tap)
        if self.player:
            self.player.close()
        self.destroy()

    # ---------- record ----------
    def intro(self):
        if self.player:
            self.player.playing = False
        self.clear()
        self.label(T('test_h'), HUGE, pady=(20, 6))
        self.label(T('test_intro'), MUTE)
        self.status = self.label('', BIG, INK, pady=(14, 4))
        self.btn = self.button(self.card, T('ready'), self.start_rec, anchor='w', padx=20, pady=10)

    def start_rec(self):
        if self.e.chain is None:
            self.status.config(text=T('not_running'), fg=BAD)
            return
        self.btn.destroy()
        self.tap = self.e.add_tap('both')
        self.rec = []
        self.t0 = time.time() + COUNT_IN
        self._rec_tick()

    def _rec_tick(self):
        if not self.winfo_exists():
            return
        now = time.time()
        while True:
            try:
                x = self.tap.get_nowait()
            except queue.Empty:
                break
            if now >= self.t0:
                self.rec.append(x)
        if now < self.t0:
            self.status.config(text=T('recording_in', n=int(np.ceil(self.t0 - now))), fg=INK)
        else:
            left = REC_SECONDS - (now - self.t0)
            self.status.config(text=T('recording_left', s=f'{max(left, 0):.0f}'), fg=BAD)
            if left <= 0:
                self.e.remove_tap(self.tap); self.tap = None
                raw = np.concatenate([r for r, _ in self.rec]).astype(np.float64)
                out = np.concatenate([o for _, o in self.rec]).astype(np.float64)
                self.bufs = prepare(raw, out)
                self.show_player()
                return
        self.after(50, self._rec_tick)

    # ---------- listen ----------
    def show_player(self):
        self.clear()
        self.label(T('test_h'), HUGE, pady=(18, 6))
        row = tk.Frame(self.card, bg=CARD); row.pack(pady=(6, 8))
        self.opt_btns = []
        for i, k in enumerate(('test_orig', 'test_sesli')):
            b = tk.Button(row, text='▶ ' + T(k), font=BIG, width=10, relief='flat', bg=SOFT, cursor='hand2',
                          command=lambda i=i: self.switch(i))
            b.pack(side='left', padx=8)
            self.opt_btns.append(b)
        if self.player is None:
            self.player = LoopPlayer()
        self.player.region = None
        Timeline(self.card, self.player, self.bufs[1]).pack(padx=20, pady=(6, 0))
        self.label(T('test_hint'), MUTE, pady=(2, 0))
        ctl = tk.Frame(self.card, bg=CARD); ctl.pack(pady=(14, 0))
        self.pp = self.button(ctl, T('tune_pause'), self.play_pause, primary=False, side='left')
        self.button(ctl, T('test_again'), self.intro, primary=False, side='left', padx=8)
        self.button(ctl, T('close'), self.close, side='left')
        self.player.load(list(self.bufs))
        self.switch(0)

    def switch(self, i):
        if not self.player or i >= len(self.player.bufs):
            return
        self.player.cur = i
        self.player.playing = True
        for j, b in enumerate(getattr(self, 'opt_btns', [])):
            if b.winfo_exists():
                b.config(bg='#e8f0fe' if j == i else SOFT)
        if hasattr(self, 'pp') and self.pp.winfo_exists():
            self.pp.config(text=T('tune_pause'))

    def play_pause(self):
        if not self.player:
            return
        self.player.playing = not self.player.playing
        if hasattr(self, 'pp') and self.pp.winfo_exists():
            self.pp.config(text=T('tune_pause') if self.player.playing else T('tune_play'))
