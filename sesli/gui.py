"""Sesli — open the app and your processed voice goes to Discord via VB-Cable. Close it and it stops.
In Discord: Input device = "CABLE Output (VB-Audio Virtual Cable)"; turn OFF noise suppression,
echo cancellation and automatic gain control (this app does those)."""
import os, queue, sys, time, traceback
import tkinter as tk
from tkinter import ttk
import webbrowser
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Started without a console (pythonw / double-click): send output and errors to a log file instead of nowhere
from paths import DATA as _LOGDIR, res  # noqa: E402
LOG = os.path.join(_LOGDIR, 'log.txt')
if sys.stderr is None or sys.stdout is None:
    _f = open(LOG, 'a', buffering=1, encoding='utf-8')
    sys.stdout = sys.stderr = _f
    print(f'--- start {time.strftime("%Y-%m-%d %H:%M:%S")} ---')

import engine as eng  # noqa: E402
import assistant as A  # noqa: E402
import eqfit  # noqa: E402
import i18n  # noqa: E402
from i18n import T  # noqa: E402

BG, CARD, INK, MUTE, LINE = '#f4f3ef', '#ffffff', '#1d1d1f', '#6b6b70', '#dcdad5'
ACC, OK, WARN, BAD = '#2f6fe4', '#2e9d5b', '#d98b19', '#d64545'
SOFT = '#ecebe6'
FONT = ('Segoe UI', 10)
BIG = ('Segoe UI Semibold', 15)
HUGE = ('Segoe UI Semibold', 20)
COUNT_IN = 3       # seconds of countdown after "I'm ready"


def dist_hint(move_db):
    r = 10 ** (-move_db / 20)
    return T('dist_hint', pct=f'{r * 100:.0f}', cm=f'{20 * r:.0f}')


class Meter(tk.Canvas):
    """Horizontal level bar, -60..0 dBFS, with an optional target zone."""

    def __init__(self, master, w=380, h=26):
        super().__init__(master, width=w, height=h, bg=CARD, highlightthickness=0)
        self.w, self.h = w, h

    def x(self, db):
        return int(np.clip((db + 60) / 60, 0, 1) * self.w)

    def draw(self, level_db, zone=None, color=ACC):
        self.delete('all')
        self.create_rectangle(0, 0, self.w, self.h, fill=SOFT, outline='')
        if zone:
            self.create_rectangle(self.x(zone[0]), 0, self.x(zone[1]), self.h, fill='#cfe8d6', outline='')
        if level_db is not None:
            self.create_rectangle(0, 4, self.x(level_db), self.h - 4, fill=color, outline='')


def set_icon(win):
    try:
        win.iconbitmap(res('assets', 'icon.ico'))
    except tk.TclError:
        pass


def button(parent, text, cmd, primary=True, **pack):
    b = tk.Button(parent, text=text, font=FONT, relief='flat', padx=14, pady=6, command=cmd, cursor='hand2',
                  bg=ACC if primary else SOFT, fg='white' if primary else INK,
                  activebackground=ACC if primary else SOFT)
    b.pack(**pack)
    return b


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Sesli')
        set_icon(self)
        self.configure(bg=BG)
        self.resizable(False, False)
        self.protocol('WM_DELETE_WINDOW', self.quit_app)
        self.engine = eng.Engine()
        self.ok = self.engine.start()
        self.setup_win = None
        self.after(150, self.bring_to_front)
        if i18n.lang() is None:
            self.show_language_picker()
        else:
            self.build_ui()

    # ---------- language ----------
    def show_language_picker(self):
        f = self.lang_card = tk.Frame(self, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        f.pack(padx=14, pady=14)
        self.logo_big = tk.PhotoImage(file=res('assets', 'icon64.png'))
        tk.Label(f, image=self.logo_big, bg=CARD).pack(pady=(28, 4))
        tk.Label(f, text='Sesli', font=('Segoe UI Semibold', 20), bg=CARD, fg=INK).pack()
        tk.Label(f, text='Choose your language  ·  Dilini seç', font=FONT, bg=CARD, fg=MUTE).pack(padx=40, pady=(6, 16))
        row = tk.Frame(f, bg=CARD); row.pack(pady=(0, 28))
        for code, name in i18n.LANGS:
            tk.Button(row, text=name, font=BIG, relief='flat', bg=ACC, fg='white', activebackground=ACC, padx=24,
                      pady=10, cursor='hand2', command=lambda c=code: self.pick_language(c)).pack(side='left', padx=8)

    def pick_language(self, code):
        i18n.set_lang(code)
        self.lang_card.destroy()
        self.build_ui()

    def change_language(self, _=None):
        code = dict((n, c) for c, n in i18n.LANGS)[self.lang_var.get()]
        if code == i18n.lang():
            return
        i18n.set_lang(code)
        reopen = self.setup_win is not None and self.setup_win.winfo_exists()
        if reopen:
            self.setup_win.close()
        for w in (self.main_card, self.cable_card):
            w.destroy()
        self.build_ui(start_setup=False)
        if reopen:
            self.open_setup()

    # ---------- main window ----------
    def build_ui(self, start_setup=True):
        self._build()
        if not getattr(self, '_ticking', False):
            self._ticking = True
            self.after(60, self.tick)
        if start_setup:
            self.after(300, self.maybe_setup)

    def bring_to_front(self):
        """Windows often opens apps started from a .bat behind other windows; pull ours to the front once."""
        self.deiconify(); self.lift(); self.attributes('-topmost', True); self.focus_force()
        self.after(800, lambda: self.attributes('-topmost', False))

    def maybe_setup(self):
        if self.ok and not self.engine.profile.get('calibrated'):
            self.open_setup()

    def _build(self):
        pad = dict(padx=18)
        self.cable_card = self._build_cable_help()
        c = self.main_card = tk.Frame(self, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        c.pack(padx=14, pady=14, fill='both')
        head = tk.Frame(c, bg=CARD); head.pack(fill='x', pady=(16, 10), **pad)
        self.logo_img = tk.PhotoImage(file=res('assets', 'icon64.png')).subsample(2, 2)
        tk.Label(head, image=self.logo_img, bg=CARD).pack(side='left')
        tk.Label(head, text='Sesli', font=('Segoe UI Semibold', 18), bg=CARD, fg=INK).pack(side='left', padx=10)
        tk.Frame(c, bg=LINE, height=1).pack(fill='x', **pad)
        top = tk.Frame(c, bg=CARD); top.pack(fill='x', pady=(12, 4), **pad)
        self.dot = tk.Canvas(top, width=14, height=14, bg=CARD, highlightthickness=0); self.dot.pack(side='left')
        self.status = tk.Label(top, text='', font=BIG, bg=CARD, fg=INK); self.status.pack(side='left', padx=8)
        self.lang_var = tk.StringVar(value=dict(i18n.LANGS)[i18n.lang()])
        lb = ttk.Combobox(head, textvariable=self.lang_var, values=[n for _, n in i18n.LANGS], state='readonly', width=8)
        lb.pack(side='right')
        lb.bind('<<ComboboxSelected>>', self.change_language)
        tk.Label(head, text=T('language'), font=FONT, bg=CARD, fg=MUTE).pack(side='right', padx=6)
        self.sub = tk.Label(c, text='', font=FONT, bg=CARD, fg=MUTE, justify='left', wraplength=400)
        self.sub.pack(anchor='w', **pad)
        mrow = tk.Frame(c, bg=CARD); mrow.pack(fill='x', pady=(12, 0), **pad)
        tk.Label(mrow, text=T('microphone'), font=FONT, bg=CARD, fg=INK).pack(side='left')
        self.mic_var = tk.StringVar(value=self.engine.mic or '')
        self.mic_box = ttk.Combobox(mrow, textvariable=self.mic_var, values=eng.list_mics(), state='readonly', width=40)
        self.mic_box.pack(side='left', padx=8)
        self.mic_box.bind('<<ComboboxSelected>>', self.change_mic)
        self.mic_box.bind('<Button-1>', lambda e: self.mic_box.config(values=eng.list_mics()))
        tk.Label(c, text=T('your_mic'), font=FONT, bg=CARD, fg=MUTE).pack(anchor='w', pady=(10, 2), **pad)
        self.m_in = Meter(c, 400); self.m_in.pack(**pad)
        self.clip = tk.Label(c, text='', font=FONT, bg=CARD, fg=BAD); self.clip.pack(anchor='w', **pad)
        tk.Label(c, text=T('discord_hears'), font=FONT, bg=CARD, fg=MUTE).pack(anchor='w', pady=(6, 2), **pad)
        self.m_out = Meter(c, 400); self.m_out.pack(**pad)

        row = tk.Frame(c, bg=CARD); row.pack(fill='x', pady=(16, 6), **pad)
        on = self.engine.chain is None or self.engine.chain.enabled
        self.btn_on = button(row, T('proc_on') if on else T('proc_off'), self.toggle, side='left')
        if not on:
            self.btn_on.config(bg='#9a9aa0')
        button(row, T('run_setup'), self.open_setup, primary=False, side='left', padx=8)
        self.btn_test = button(row, T('test_mic'), self.test_mic, primary=False, side='left')
        row2 = tk.Frame(c, bg=CARD); row2.pack(fill='x', pady=(2, 4), **pad)
        button(row2, T('tune_btn'), self.open_tuner, primary=False, side='left')
        self.tone_lbl = tk.Label(row2, text='', font=FONT, bg=CARD, fg=MUTE); self.tone_lbl.pack(side='left', padx=10)
        self.tone_reset = tk.Label(row2, text=T('tone_reset'), font=('Segoe UI', 9, 'underline'), bg=CARD, fg=ACC,
                                   cursor='hand2')
        self.tone_reset.bind('<Button-1>', lambda e: self.reset_tone())
        self.test_msg = tk.Label(c, text='', font=FONT, bg=CARD, fg=MUTE, wraplength=400, justify='left')
        self.test_msg.pack(anchor='w', **pad)

        srow = tk.Frame(c, bg=CARD); srow.pack(fill='x', pady=(4, 4), **pad)
        tk.Label(srow, text=T('noise_removal'), font=FONT, bg=CARD, fg=INK).pack(side='left')
        self.strength = tk.StringVar(value='strong' if self.engine.profile['nr_atten_db'] >= 50 else 'gentle')
        for v in ('strong', 'gentle'):
            tk.Radiobutton(srow, text=T(v), value=v, variable=self.strength, bg=CARD, font=FONT,
                           command=self.set_strength, activebackground=CARD).pack(side='left', padx=6)

        tk.Label(c, font=('Segoe UI', 9), bg=CARD, fg=MUTE, justify='left', wraplength=400,
                 text=T('discord_help')).pack(anchor='w', pady=(10, 16), **pad)

    def _build_cable_help(self):
        f = tk.Frame(self, bg=CARD, highlightbackground=LINE, highlightthickness=1)

        def L(t, font=FONT, fg=INK):
            tk.Label(f, text=t, font=font, bg=CARD, fg=fg, justify='left', wraplength=400).pack(anchor='w', padx=20, pady=3)
        L(T('cable_title'), BIG)
        L(T('cable_why'), fg=MUTE)
        L(T('cable_1')); L(T('cable_2')); L(T('cable_3'))
        row = tk.Frame(f, bg=CARD); row.pack(anchor='w', padx=20, pady=(12, 18))
        button(row, T('cable_dl'), lambda: webbrowser.open(eng.VB_CABLE_URL), side='left')
        button(row, T('check_again'), self.retry, primary=False, side='left', padx=8)
        return f

    def retry(self):
        self.engine = eng.Engine(self.engine.mic)
        self.ok = self.engine.start()
        if self.ok:
            self.maybe_setup()

    def change_mic(self, _=None):
        mic = self.mic_var.get()
        if mic and mic != self.engine.mic:
            if self.setup_win is not None and self.setup_win.winfo_exists():
                self.setup_win.close()
            self.ok = self.engine.switch_mic(mic)
            self.strength.set('strong' if self.engine.profile['nr_atten_db'] >= 50 else 'gentle')
            self.maybe_setup()

    # ---------- test recording: hear exactly what Discord hears ----------
    TEST_SECONDS = 8

    def test_mic(self):
        if not self.ok or getattr(self, 'testing', False):
            return
        self.testing = True
        self.test_q = self.engine.add_tap('out')
        self.test_buf = []
        self.test_t0 = time.time()
        self.btn_test.config(state='disabled')
        self._test_tick()

    def _test_tick(self):
        while True:
            try:
                self.test_buf.append(self.test_q.get_nowait())
            except queue.Empty:
                break
        left = self.TEST_SECONDS - (time.time() - self.test_t0)
        if left > 0:
            self.test_msg.config(text=T('recording_test', s=f'{left:.0f}'), fg=BAD)
            self.after(100, self._test_tick)
            return
        self.engine.remove_tap(self.test_q)
        audio = np.concatenate(self.test_buf) if self.test_buf else np.zeros(480, np.float32)
        self.test_msg.config(text=T('playing_back'), fg=INK)
        try:
            import sounddevice as sd
            sd.play(audio, eng.SR)
            self.after(int(len(audio) / eng.SR * 1000) + 300, self._test_done)
        except Exception as ex:
            self.test_msg.config(text=T('cant_play', err=ex), fg=BAD)
            self._test_done(keep_msg=True)

    def _test_done(self, keep_msg=False):
        self.testing = False
        if self.btn_test.winfo_exists():
            self.btn_test.config(state='normal')
            if not keep_msg:
                self.test_msg.config(text=T('test_done'), fg=MUTE)

    def open_tuner(self):
        if not self.ok:
            return
        import tuner
        if getattr(self, 'tuner_win', None) is None or not self.tuner_win.winfo_exists():
            self.tuner_win = tuner.Tuner(self)
        w = self.tuner_win
        w.lift(); w.attributes('-topmost', True); w.focus_force()
        w.after(800, lambda: w.winfo_exists() and w.attributes('-topmost', False))

    def reset_tone(self):
        self.engine.apply_profile(dict(character={}, character_eq=[]))

    def _tone_text(self):
        pos = self.engine.profile.get('character') or {}
        words = {'clarity': ('tw_clear', 'tw_soft'), 'warmth': ('tw_warm', 'tw_light'), 'air': ('tw_airy', 'tw_dark')}
        d = [T(words[a][0] if v > 0 else words[a][1]) for a, v in pos.items() if abs(v) >= 0.15]
        tuned = any(abs(v) > 1e-3 for v in pos.values())
        return T('tone_label', t=', '.join(d) if d else T('tone_default')), tuned

    def toggle(self):
        ch = self.engine.chain
        if ch is None:
            return
        ch.enabled = not ch.enabled
        self.btn_on.config(text=T('proc_on') if ch.enabled else T('proc_off'),
                           bg=ACC if ch.enabled else '#9a9aa0')

    def set_strength(self):
        self.engine.apply_profile(dict(nr_atten_db=100.0 if self.strength.get() == 'strong' else 24.0))

    def tick(self):
        e = self.engine
        try:
            nocable = e.status == 'no_cable'
            if nocable and not self.cable_card.winfo_ismapped():
                self.main_card.pack_forget(); self.cable_card.pack(padx=14, pady=14, fill='both')
            elif not nocable and self.cable_card.winfo_ismapped():
                self.cable_card.pack_forget(); self.main_card.pack(padx=14, pady=14, fill='both')
            if not self.ok:
                self.dot.delete('all'); self.dot.create_oval(2, 2, 12, 12, fill=BAD, outline='')
                self.status.config(text=T('not_running')); self.sub.config(text=e.error or '')
            else:
                on = e.chain.enabled
                self.dot.delete('all'); self.dot.create_oval(2, 2, 12, 12, fill=OK if on else WARN, outline='')
                self.status.config(text=T('live') if on else T('live_off'))
                cal = T('set_up') if e.profile.get('calibrated') else T('not_set_up')
                busy = T('busy') if e.slow_blocks > 50 else ''
                self.sub.config(text=T('delay', cal=cal, ms=f'{e.latency_ms:.0f}', busy=busy))
                self.m_in.draw(e.in_peak_db, color='#9a9aa0' if e.in_peak_db < -3 else BAD)
                self.m_out.draw(e.out_db + 10, color=ACC)
                txt, tuned = self._tone_text()
                if self.tone_lbl.cget('text') != txt:
                    self.tone_lbl.config(text=txt)
                if tuned and not self.tone_reset.winfo_ismapped():
                    self.tone_reset.pack(side='left')
                elif not tuned and self.tone_reset.winfo_ismapped():
                    self.tone_reset.pack_forget()
                knob = e.profile.get('has_knob') is not False
                self.clip.config(text=(T('clip_knob') if knob else T('clip_auto')) if time.time() < e.clip_until else '')
        except tk.TclError:
            pass  # widgets being rebuilt (language change)
        self.after(60, self.tick)

    def open_setup(self):
        if self.setup_win is None or not self.setup_win.winfo_exists():
            self.setup_win = Setup(self)
        w = self.setup_win
        w.lift(); w.attributes('-topmost', True); w.focus_force()
        w.after(800, lambda: w.winfo_exists() and w.attributes('-topmost', False))

    def quit_app(self):
        self.engine.stop()
        self.destroy()


class Setup(tk.Toplevel):
    """Step-by-step: measure -> plan -> move -> gain -> verify -> calibrate -> done.
    Every recording step waits for "I'm ready", then counts down, then records."""

    def __init__(self, app):
        super().__init__(app)
        self.app, self.e = app, app.engine
        self.title(T('setup_title'))
        set_icon(self)
        self.configure(bg=BG)
        self.resizable(False, False)
        self.locked = tk.BooleanVar(value=self.e.profile.get('distance_locked', False))
        self.card = tk.Frame(self, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        self.card.pack(padx=14, pady=14)
        self.card.configure(width=480, height=470); self.card.pack_propagate(False)
        self.tap = None
        self.tap_post = None
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.bind('<Return>', lambda e: self._enter())
        self.step_intro()

    # ---------- helpers ----------
    def clear(self):
        for w in self.card.winfo_children():
            w.destroy()
        self.on_enter = None

    def _enter(self):
        if self.on_enter:
            self.on_enter()

    def h(self, text, size=BIG):
        lab = tk.Label(self.card, text=text, font=size, bg=CARD, fg=INK, wraplength=440, justify='left')
        lab.pack(anchor='w', padx=20, pady=(18, 6))
        return lab

    def p(self, text, color=MUTE, font=FONT):
        lab = tk.Label(self.card, text=text, font=font, bg=CARD, fg=color, wraplength=440, justify='left')
        lab.pack(anchor='w', padx=20, pady=3)
        return lab

    def btn(self, text, cmd, primary=True):
        b = button(self.card, text, cmd, primary=primary, anchor='w', padx=20, pady=(12, 0))
        if primary:
            self.on_enter = cmd
        return b

    def lock_box(self):
        tk.Checkbutton(self.card, text=T('lock'), variable=self.locked, bg=CARD, font=FONT, activebackground=CARD,
                       wraplength=420, justify='left', command=self.on_lock).pack(anchor='w', padx=16, pady=(10, 0))

    def on_lock(self):
        self.e.profile['distance_locked'] = bool(self.locked.get())
        if hasattr(self, 'meas') and getattr(self, 'on_plan', False):
            self.step_plan()

    def start_tap(self):
        if self.tap is None:
            self.tap = self.e.add_tap('raw')
            self.an = A.Analyzer()

    def drain(self, keep_raw=None):
        out = []
        while True:
            try:
                x = self.tap.get_nowait()
            except queue.Empty:
                break
            out.append(self.an.block(x))
            if keep_raw is not None:
                keep_raw.append(x)
        return out

    def close(self):
        for t in (self.tap, self.tap_post):
            if t is not None:
                self.e.remove_tap(t)
        self.destroy()

    # ---------- steps ----------
    def step_intro(self):
        self.clear()
        self.h(T('intro_h'), HUGE)
        self.p(T('intro_p1'))
        self.p(T('intro_p2'))
        self.lock_box()
        tk.Label(self.card, text=T('knob_q'), font=FONT, bg=CARD, fg=INK).pack(anchor='w', padx=20, pady=(12, 0))
        hk = self.e.profile.get('has_knob')
        self.knob = tk.StringVar(value='no' if hk is False else 'yes')
        for v in ('yes', 'no'):
            tk.Radiobutton(self.card, text=T('knob_' + v), value=v, variable=self.knob, bg=CARD, font=FONT,
                           wraplength=420, justify='left', activebackground=CARD).pack(anchor='w', padx=16)
        self.btn(T('start'), self.start_measure)

    def start_measure(self):
        has = self.knob.get() == 'yes'
        self.e.apply_profile(dict(has_knob=has))
        if has:
            eng.set_input_level_full(self.e.mic)
        self.verifying = False
        self.step_measure()

    def step_measure(self):
        """Three phases; each waits for "I'm ready", counts down, then records."""
        self.start_tap()
        self.phases = [('silence', 4.0, T('ph_silence'), T('ph_silence_i')),
                       ('talk', 10.0, T('ph_talk'), T('ph_talk_i') + '\n\n' + T('read_text')),
                       ('loud', 5.0, T('ph_loud'), T('ph_loud_i'))]
        self.buf = {'silence': [], 'talk': [], 'loud': []}
        self.raw_tl = []
        self.pi = 0
        self._phase_screen()

    def _phase_screen(self):
        """Show the instruction for the current phase and wait for "I'm ready"."""
        self.clear()
        name, dur, title, inst = self.phases[self.pi]
        if getattr(self, 'verifying', False):
            self.p(T('check_h'), MUTE, BIG)
        self.h(title, HUGE)
        self.p(inst, INK, ('Segoe UI', 11) if name == 'talk' else FONT)
        self.meter = Meter(self.card, 440); self.meter.pack(padx=20, pady=10)
        self.count = tk.Label(self.card, text=T('ready_hint'), font=BIG, bg=CARD, fg=MUTE)
        self.count.pack(anchor='w', padx=20)
        self.ready_btn = self.btn(T('ready'), self._ready)
        self.phase_state = 'waiting'
        self.drain()
        self._measure_tick()

    def _ready(self):
        if self.phase_state != 'waiting':
            return
        self.phase_state = 'countin'
        self.on_enter = None
        self.ready_btn.destroy()
        self.t0 = time.time() + COUNT_IN

    def _measure_tick(self):
        if not self.winfo_exists() or not self.meter.winfo_exists():
            return
        name, dur, _, _ = self.phases[self.pi]
        now = time.time()
        raws = []
        blocks = self.drain(raws)
        if blocks:
            self.meter.draw(20 * np.log10(max(b['peak'] for b in blocks) + 1e-9),
                            color=BAD if self.phase_state == 'recording' else ACC)
        if self.phase_state == 'countin':
            if now < self.t0:
                self.count.config(text=T('recording_in', n=int(np.ceil(self.t0 - now))), fg=INK)
            else:
                self.phase_state = 'recording'
        if self.phase_state == 'recording':
            self.buf[name].extend(blocks)
            if name != 'silence':
                self.raw_tl.extend(raws)
            left = dur - (now - self.t0)
            self.count.config(text=T('recording_left', s=f'{max(left, 0):.0f}'), fg=BAD)
            if left <= 0:
                self.pi += 1
                if self.pi >= len(self.phases):
                    raw = np.concatenate(self.raw_tl) if self.raw_tl else np.zeros(10)
                    self.meas = A.summarize(self.buf['silence'], self.buf['talk'], self.buf['loud'], raw)
                    self.after_measure()
                else:
                    self._phase_screen()
                return
        self.after(50, self._measure_tick)

    def after_measure(self):
        if getattr(self, 'verifying', False):
            self.verifying = False
            self.step_verify_result()
        else:
            self.step_plan()

    def step_plan(self):
        self.clear()
        self.on_plan = True
        m = self.meas
        self.pl = A.plan(m, bool(self.locked.get()))
        pl = self.pl
        self.h(T('plan_h'))
        word = T('snr_great') if m['snr'] >= A.SNR_GREAT else T('snr_ok') if m['snr'] >= A.SNR_OK else T('snr_bad')
        self.p(T('plan_now', snr=f'{m["snr"]:.0f}', word=word) + (T('plan_clip') if m['clipped'] else ''), INK)
        if pl['move'] > 0:
            self.p(T('plan_closer', hint=dist_hint(pl['move'])), INK)
        elif pl['move'] < 0:
            self.p(T('plan_back', hint=dist_hint(pl['move'])), INK)
        else:
            self.p(T('plan_keep'), INK)
        self.p(T('plan_gain'), INK)
        self.p(T('plan_cal'), INK)
        self.p(T('q_' + pl['quality']), OK if pl['quality'] != 'ok' else WARN)
        self.lock_box()
        self.btn(T('go'), self.step_move if pl['move'] != 0 else self.step_gain)

    def _live_step(self, title, target, tol, msg_fn, on_done, extra_btn=None):
        self.clear()
        self.on_plan = False
        self.h(title, HUGE)
        self.inst = tk.Label(self.card, font=BIG, bg=CARD, fg=INK, wraplength=440, justify='left')
        self.inst.pack(anchor='w', padx=20, pady=(4, 2))
        self.p(T('keep_talking'))
        self.meter = Meter(self.card, 440, 34); self.meter.pack(padx=20, pady=14)
        self.hint = tk.Label(self.card, font=FONT, bg=CARD, fg=MUTE, wraplength=440, justify='left')
        self.hint.pack(anchor='w', padx=20)
        if extra_btn:
            self.btn(*extra_btn, primary=False)
        self.live = A.LiveLevel(self.meas['noise'])
        self.drain()
        self.hold_since = None
        self._live_args = (target, tol, msg_fn, on_done)
        self._live_tick()

    def _live_tick(self):
        if not self.winfo_exists() or not hasattr(self, 'meter') or not self.meter.winfo_exists():
            return
        target, tol, msg_fn, on_done = self._live_args
        for b in self.drain():
            self.live.push(b)
            if b['peak'] > 0.98:
                self.e.clip_until = time.time() + 1.5
        v = self.live.value()
        if v is not None and getattr(self, 'auto_gain', False) and getattr(self, 'in_gain_step', False) \
                and time.time() - getattr(self, 'last_adj', 0) > 0.6:
            cur, rng = eng.get_input_level_db(self.e.mic)
            d = v - target
            if cur is not None and abs(d) > A.LEVEL_TOL * 0.7:
                new = float(np.clip(cur - np.clip(d * 0.7, -6, 6), rng[0], rng[1]))
                if abs(new - cur) > 0.2:
                    eng.set_input_level_db(self.e.mic, new)
                    self.live.buf = []  # measure again at the new level
                elif d < 0:
                    self.hint.config(text=T('mic_max'))
            self.last_adj = time.time()
        if v is None:
            self.inst.config(text=T('start_talking'), fg=INK)
            self.meter.draw(None, (target - tol, target + tol))
        else:
            d = v - target
            inside = abs(d) <= tol
            self.inst.config(text=msg_fn(d), fg=OK if inside else INK)
            self.meter.draw(v, (target - tol, target + tol), OK if inside else ACC)
            if inside:
                self.hold_since = self.hold_since or time.time()
                self.hint.config(text=T('hold'))
                if time.time() - self.hold_since > 2.0:
                    on_done(v)
                    return
            else:
                self.hold_since = None
                if self.hint.cget('text') == T('hold'):
                    self.hint.config(text='')
        self.after(60, self._live_tick)

    def step_move(self):
        self.in_gain_step = False
        base = self.meas['speech']
        target = base + self.pl['move']
        closer = self.pl['move'] > 0

        def msg(d):
            if d < -A.LEVEL_TOL:
                return T('m_closer') if closer else T('m_too_far_back')
            if d > A.LEVEL_TOL:
                return T('m_too_close') if closer else T('m_further')
            return T('m_spot')

        def done(v):
            self.meas = dict(self.meas, speech=v, snr=self.meas['snr'] + (v - base))
            self.step_gain()

        def lock_here():
            self.locked.set(True); self.e.profile['distance_locked'] = True
            v = self.live.value()
            done(v) if v is not None else self.step_gain()

        self._live_step(T('move_h'), target, A.LEVEL_TOL, msg, done, extra_btn=(T('m_lock_here'), lock_here))
        self.p(T('m_aim', hint=dist_hint(self.pl['move'])))

    def step_gain(self):
        self.in_gain_step = True
        target = self.pl['target_speech']
        self.gain_target = target

        def msg(d):
            if d < -A.LEVEL_TOL:
                return T('g_up') if d > -6 else T('g_up_lot')
            if d > A.LEVEL_TOL:
                return T('g_down') if d < 6 else T('g_down_lot')
            return T('g_perfect')

        def done(v):
            self.in_gain_step = False
            self.verifying = True
            self.step_measure()

        if self.e.profile.get('has_knob') is False:
            self.auto_gain = True
            self._live_step(T('auto_h'), target, A.LEVEL_TOL,
                            lambda d: T('auto_adj') if abs(d) > A.LEVEL_TOL else T('auto_ok'), done)
            self.p(T('auto_note'))
            return
        self.auto_gain = False
        self._live_step(T('gain_h'), target, A.LEVEL_TOL, msg, done)
        self.p(T('g_where'))

    def step_verify_result(self):
        m = self.meas
        self.tries = getattr(self, 'tries', 0) + 1
        if m['clipped'] and self.tries < 3:
            self.pl = dict(self.pl, target_speech=self.gain_target - 3.0)
            self.clear(); self.h(T('still_clip_h')); self.p(T('still_clip_p'))
            self.btn(T('ok'), self.step_gain)
            return
        self.e.profile['input_speech_db'] = m['speech']
        self.e.profile['input_noise_db'] = m['noise']
        self.step_calibrate()

    def step_calibrate(self):
        self.clear()
        self.h(T('cal_h'), HUGE)
        self.p(T('cal_p'), INK)
        self.p(T('read_text'), INK, ('Segoe UI', 11))
        self.count = tk.Label(self.card, text=T('ready_hint'), font=BIG, bg=CARD, fg=MUTE)
        self.count.pack(anchor='w', padx=20, pady=8)
        self.cal_state = 'waiting'
        self.ready_btn = self.btn(T('ready'), self._cal_ready)

    def _cal_ready(self):
        if self.cal_state != 'waiting':
            return
        self.cal_state = 'countin'
        self.on_enter = None
        self.ready_btn.destroy()
        self.tap_post = self.e.add_tap('post_nr')
        self.post = []
        self.t0 = time.time() + COUNT_IN
        self._cal_tick()

    def _cal_tick(self):
        if not self.winfo_exists():
            return
        now = time.time()
        while True:
            try:
                x = self.tap_post.get_nowait()
            except queue.Empty:
                break
            if now >= self.t0:
                self.post.append(x)
        self.drain()
        if now < self.t0:
            self.count.config(text=T('recording_in', n=int(np.ceil(self.t0 - now))), fg=INK)
        else:
            left = 20 - (now - self.t0)
            self.count.config(text=T('recording_left', s=f'{max(left, 0):.0f}'), fg=BAD)
            if left <= 0:
                self.e.remove_tap(self.tap_post); self.tap_post = None
                self.finish(np.concatenate(self.post) if self.post else np.zeros(10))
                return
        self.after(60, self._cal_tick)

    def finish(self, post):
        self.clear()
        try:
            n = 480
            k = len(post) // n
            lv = 10 * np.log10((post[:k * n].reshape(k, n) ** 2).mean(1) + 1e-14)
            speech_p90 = float(np.percentile(lv, 90))
            eq, fit_err, before = eqfit.fit(eqfit.ltas(post, speech_p90 - 25))
            self.e.apply_profile(dict(
                eq=eq,
                exp_thresh_db=speech_p90 - 22.0,
                agc_gate_db=speech_p90 - 25.0,
                agc_start_db=float(np.clip(-26.5 - (speech_p90 - 2.0), -12, 12)),
                calibrated=True,
                distance_locked=bool(self.locked.get()),
                setup_time=time.strftime('%Y-%m-%d %H:%M'),
            ))
            self.h(T('done_h'), HUGE)
            self.p(T('done_p', snr=f'{self.meas["snr"]:.0f}', err=f'{fit_err:.1f}', before=f'{before:.1f}'), INK)
            self.p(T('done_p2'))
        except Exception as ex:
            self.h(T('fail_h'))
            self.p(T('fail_p', err=ex), BAD)
            traceback.print_exc()
        self.btn(T('close'), self.close)


if __name__ == '__main__':
    App().mainloop()
