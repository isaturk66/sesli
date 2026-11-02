"""Tune-by-ear window: record 10 s, then blind choices (tonesearch.py) find the voice character you like.
Includes a loop bar: drag over the waveform to loop a part (e.g. 2-4 s) on every option."""
import queue, time
import tkinter as tk
import numpy as np
import sounddevice as sd
from scipy import signal

from biquad import eq_sos
from i18n import T
import tonesearch as TS

SR = 48000
REC_SECONDS = 10
COUNT_IN = 3
BG, CARD, INK, MUTE, LINE, ACC, OK, WARN, BAD, SOFT = ('#f4f3ef', '#ffffff', '#1d1d1f', '#6b6b70', '#dcdad5',
                                                      '#2f6fe4', '#2e9d5b', '#d98b19', '#d64545', '#ecebe6')
FONT, BIG, HUGE = ('Segoe UI', 10), ('Segoe UI Semibold', 14), ('Segoe UI Semibold', 20)
LETTERS = 'ABCD'
MATCH_DB = -22.0  # every option is played at this speech level, so loudness never decides


def render(x, pos):
    eq = TS.character_eq(pos)
    y = signal.sosfilt(eq_sos([tuple(e) for e in eq], SR), x) if eq else x.copy()
    fr = y[:len(y) // 480 * 480].reshape(-1, 480)
    lv = (fr ** 2).mean(1)
    sp = lv > np.percentile(lv, 40)
    g = np.sqrt(10 ** (MATCH_DB / 10) / (lv[sp].mean() + 1e-12))
    return np.clip(y * g, -1, 1).astype(np.float32)


class LoopPlayer:
    """Plays one of several equal-length buffers from a shared position, looping the whole clip or a
    selected region. Switching options keeps the position, so differences are heard instantly."""

    def __init__(self):
        self.bufs = []
        self.cur = 0
        self.pos = 0
        self.region = None
        self.playing = False
        self.stream = sd.OutputStream(samplerate=SR, channels=1, dtype='float32', blocksize=480, callback=self._cb)
        self.stream.start()

    def _cb(self, out, frames, t, status):
        if not self.playing or not self.bufs:
            out[:] = 0
            return
        b = self.bufs[self.cur]
        lo, hi = self.region or (0, len(b))
        o = 0
        while o < frames:
            if self.pos >= hi or self.pos < lo:
                self.pos = lo
            n = min(frames - o, hi - self.pos)
            out[o:o + n, 0] = b[self.pos:self.pos + n]
            self.pos += n
            o += n

    def load(self, bufs):
        self.bufs = bufs
        self.cur = 0
        lo = self.region[0] if self.region else 0
        self.pos = lo
        self.playing = True

    def close(self):
        try:
            self.stream.stop(); self.stream.close()
        except Exception:
            pass


class Timeline(tk.Canvas):
    """Waveform with playhead. Drag = select a loop region, click = jump, double-click = clear."""

    def __init__(self, master, player, audio, w=440, h=46):
        super().__init__(master, width=w, height=h, bg=CARD, highlightthickness=0, cursor='hand2')
        self.p, self.w, self.h = player, w, h
        n = len(audio) // w
        env = np.abs(audio[:n * w]).reshape(w, n).max(1)
        self.env = env / (env.max() + 1e-9)
        self.total = len(audio)
        self.drag0 = None
        self.bind('<ButtonPress-1>', self._down)
        self.bind('<B1-Motion>', self._move)
        self.bind('<ButtonRelease-1>', self._up)
        self.bind('<Double-Button-1>', lambda e: self._clear())
        self._tick()

    def _x2s(self, x):
        return int(np.clip(x / self.w, 0, 1) * self.total)

    def _down(self, e):
        self.drag0 = e.x

    def _move(self, e):
        if self.drag0 is not None and abs(e.x - self.drag0) > 4:
            a, b = sorted((self.drag0, e.x))
            self.p.region = (self._x2s(a), max(self._x2s(b), self._x2s(a) + SR // 4))

    def _up(self, e):
        if self.drag0 is not None and abs(e.x - self.drag0) <= 4:  # a click: jump there
            s = self._x2s(e.x)
            if self.p.region and not (self.p.region[0] <= s < self.p.region[1]):
                self.p.region = None
            self.p.pos = s
            self.p.playing = True
        elif self.p.region:
            self.p.pos = self.p.region[0]
            self.p.playing = True
        self.drag0 = None

    def _clear(self):
        self.p.region = None

    def _tick(self):
        if not self.winfo_exists():
            return
        self.delete('all')
        if self.p.region:
            a, b = (r / self.total * self.w for r in self.p.region)
            self.create_rectangle(a, 0, b, self.h, fill='#dbe6fb', outline='')
        mid = self.h / 2
        for x, v in enumerate(self.env):
            hh = max(1, v * (self.h / 2 - 3))
            self.create_line(x, mid - hh, x, mid + hh, fill='#b9b7b0')
        px = self.p.pos / self.total * self.w
        self.create_line(px, 0, px, self.h, fill=ACC, width=2)
        self.after(40, self._tick)


class Tuner(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app, self.e = app, app.engine
        self.title(T('tune_title'))
        self.configure(bg=BG)
        self.resizable(False, False)
        try:
            from paths import res
            self.iconbitmap(res('assets', 'icon.ico'))
        except Exception:
            pass
        self.card = tk.Frame(self, bg=CARD, highlightbackground=LINE, highlightthickness=1, width=500, height=440)
        self.card.pack(padx=14, pady=14)
        self.card.pack_propagate(False)
        self.protocol('WM_DELETE_WINDOW', self.close)
        for i in range(4):
            self.bind(str(i + 1), lambda e, i=i: self.switch(i))
        self.bind('<space>', lambda e: self.play_pause())
        self.player = None
        self.tap = None
        self.intro()

    # ---------- helpers ----------
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
        if self.e.chain is not None:
            self.e.chain.char_bypass = False
        if self.player:
            self.player.close()
        self.destroy()

    # ---------- 1. record ----------
    def intro(self):
        self.clear()
        self.label(T('tune_h'), HUGE, pady=(20, 6))
        self.label(T('tune_intro'), MUTE)
        self.status = self.label('', BIG, INK, pady=(14, 4))
        self.btn = self.button(self.card, T('ready'), self.start_rec, anchor='w', padx=20, pady=10)

    def start_rec(self):
        if self.e.chain is None:
            self.status.config(text=T('not_running'), fg=BAD)
            return
        self.btn.destroy()
        self.e.chain.char_bypass = True  # record the voice without the current character
        self.tap = self.e.add_tap('out')
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
                self.e.chain.char_bypass = False
                self.voice = np.concatenate(self.rec).astype(np.float64)
                self.player = LoopPlayer()
                self.search = TS.ToneSearch()
                self.n = 0
                self.show_next()
                return
        self.after(50, self._rec_tick)

    # ---------- 2. blind choices ----------
    def show_next(self):
        t = self.search.next()
        if t is None:
            return self.finish()
        self.n += 1
        self.clear()
        k = len(t['options'])
        title = {'multi': T('tune_pick'), 'pair': T('tune_pair'), 'check': T('tune_check')}[t['kind']]
        self.label(f"{title}", HUGE, pady=(18, 0))
        self.label(T('tune_step', n=self.n, m=self.search.max_trials()), MUTE, pady=(0, 6))
        bufs = [render(self.voice, o) for o in t['options']]
        row = tk.Frame(self.card, bg=CARD); row.pack(pady=(4, 8))
        self.opt_btns = []
        for i in range(k):
            b = tk.Button(row, text='▶ ' + LETTERS[i], font=BIG, width=4 if k > 2 else 6, relief='flat', bg=SOFT,
                          cursor='hand2', command=lambda i=i: self.switch(i))
            b.pack(side='left', padx=6)
            self.opt_btns.append(b)
        self.timeline = Timeline(self.card, self.player, self.voice)
        self.timeline.pack(padx=20, pady=(6, 0))
        self.label(T('tune_loop_hint'), MUTE, pady=(2, 0))
        pick = tk.Frame(self.card, bg=CARD); pick.pack(pady=(14, 4))
        tk.Label(pick, text=T('tune_mypick'), font=FONT, bg=CARD, fg=INK).pack(side='left', padx=(0, 6))
        for i in range(k):
            self.button(pick, T('tune_choose', l=LETTERS[i]), lambda i=i: self.answer(i), side='left', padx=3)
        self.button(pick, T('tune_cant'), lambda: self.answer(None), primary=False, side='left', padx=3)
        ctl = tk.Frame(self.card, bg=CARD); ctl.pack()
        self.pp = self.button(ctl, T('tune_pause'), self.play_pause, primary=False, side='left')
        if self.search.same_side_streak():
            self.label(T('tune_habit'), WARN, pady=(8, 0))
        self.player.load(bufs)
        self.switch(0)

    def switch(self, i):
        if not self.player or i >= len(self.player.bufs):
            return
        self.player.cur = i
        if not self.player.playing:
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

    def answer(self, choice):
        self.search.answer(choice)
        self.show_next()

    # ---------- 3. result ----------
    def finish(self):
        self.player.playing = False
        s = self.search
        self.clear()
        self.label(T('tune_done_h'), HUGE, pady=(20, 6))
        words = {'clarity': ('tw_clear', 'tw_soft'), 'warmth': ('tw_warm', 'tw_light'), 'air': ('tw_airy', 'tw_dark')}
        desc = [T(words[a][0] if v > 0 else words[a][1]) for a, v in s.pos.items() if abs(v) >= 0.15]
        sound = ', '.join(desc) if desc else T('tw_none')
        row = tk.Frame(self.card, bg=CARD)
        if s.result == 'tuned':
            self.label(T('tune_res_tuned', sound=sound), INK)
            self.apply(s.pos)
            self.label(T('tune_applied'), OK)
        elif s.result == 'original':
            self.label(T('tune_res_original'), INK)
            self.apply(None)
        else:
            self.label(T('tune_res_mixed', sound=sound), INK)
            row.pack(anchor='w', padx=20, pady=10)
            self.button(row, T('tune_use'), lambda: (self.apply(s.pos), self.close()), side='left')
            self.button(row, T('tune_keep'), lambda: (self.apply(None), self.close()), primary=False, side='left', padx=8)
            return
        self.button(self.card, T('close'), self.close, anchor='w', padx=20, pady=12)

    def apply(self, pos):
        self.e.apply_profile(dict(character=pos or {}, character_eq=TS.character_eq(pos) if pos else [],
                                  character_history=[{k: v for k, v in h.items() if k != 'options'}
                                                     for h in self.search.history]))
