"""Live engine: chosen mic -> Chain -> VB-Cable ("CABLE Input"). Voice apps use "CABLE Output" as their mic.
Works with any mic/interface: devices are found by role, not by brand. Each mic keeps its own setup.
Runs only while the app runs."""
import collections, ctypes, json, os, queue, threading, time
import numpy as np
import sounddevice as sd

from dsp import Chain, SR, BLOCK
import timer_res

HERE = os.path.dirname(os.path.abspath(__file__))
from paths import DATA
import i18n
PROFILES = os.path.join(DATA, 'profiles.json')
VB_CABLE_URL = 'https://vb-audio.com/Cable/'

# Devices that are virtual/loopback, never a real mic
VIRTUAL = ('cable', 'vb-audio', 'voicemeeter', 'sonar', 'stereo mix', 'nvidia broadcast', 'wave link',
           'virtual', 'steam streaming', 'what u hear')

DEFAULT_PROFILE = dict(
    # starting EQ = fitted to the Discord target on the C1 take; setup refits it for each mic
    eq=[['lowshelf', 232.1, -0.62, 0.7], ['peak', 1500.0, 0.11, 1.49], ['peak', 5885.8, -2.85, 0.7],
        ['peak', 7972.3, -3.17, 6.0], ['highshelf', 9744.9, 1.38, 0.7]],
    agc_target_db=-26.5,     # output speech level, matched to Discord's loudness
    agc_gate_db=-45.0,       # AGC adapts only while you speak (setup sets it from your voice)
    exp_thresh_db=-38.0,     # expander threshold (setup sets it 22 dB under your speech)
    nr_atten_db=100.0,       # noise removal: 100 = strong, 24 = gentle
    has_knob=None,           # True: hardware gain knob; False: gain = Windows input level
    calibrated=False,
)


# ---------- profiles ----------
def _load_all():
    try:
        return json.load(open(PROFILES))
    except Exception:
        return {'mics': {}, 'last_mic': None}


def load_profile(mic):
    p = dict(DEFAULT_PROFILE)
    p.update(_load_all()['mics'].get(mic, {}))
    return p


def save_profile(mic, p):
    os.makedirs(DATA, exist_ok=True)
    allp = _load_all()
    allp['mics'][mic] = p
    allp['last_mic'] = mic
    json.dump(allp, open(PROFILES, 'w'), indent=1)


def last_mic():
    return _load_all().get('last_mic')


# ---------- devices ----------
def _wasapi(kind):
    out = []
    for i, d in enumerate(sd.query_devices()):
        if sd.query_hostapis(d['hostapi'])['name'] != 'Windows WASAPI':
            continue
        if (kind == 'in' and d['max_input_channels'] > 0) or (kind == 'out' and d['max_output_channels'] > 0):
            out.append((i, d['name']))
    return out


def list_mics():
    return [n for _, n in _wasapi('in') if not any(v in n.lower() for v in VIRTUAL)]


def _active_capture():
    """{friendly name: pycaw AudioDevice} for CONNECTED recording devices only (fast: no full device scan)."""
    from pycaw.pycaw import AudioUtilities
    import comtypes
    comtypes.CoInitialize()
    enum = AudioUtilities.GetDeviceEnumerator()
    coll = enum.EnumAudioEndpoints(1, 1)  # eCapture, DEVICE_STATE_ACTIVE
    out = {}
    for i in range(coll.GetCount()):
        d = AudioUtilities.CreateDevice(coll.Item(i))
        out[d.FriendlyName] = d
    return out


def windows_default_mic():
    try:
        from pycaw.pycaw import AudioUtilities
        import comtypes
        comtypes.CoInitialize()
        enum = AudioUtilities.GetDeviceEnumerator()
        d = AudioUtilities.CreateDevice(enum.GetDefaultAudioEndpoint(1, 0))  # eCapture, eConsole
        if d.FriendlyName in list_mics():
            return d.FriendlyName
    except Exception:
        pass
    try:  # fallback: MME default name is truncated to 31 chars; match by prefix
        name = sd.query_devices(kind='input')['name']
        for n in list_mics():
            if n.startswith(name[:28]):
                return n
    except Exception:
        pass
    mics = list_mics()
    return mics[0] if mics else None


def pick_mic():
    mics = list_mics()
    lm = last_mic()
    if lm in mics:
        return lm
    d = windows_default_mic()
    return d if d in mics else (mics[0] if mics else None)


def find_cable():
    for i, n in _wasapi('out'):
        if n.lower().startswith('cable input'):
            return i
    return None


def device_index(name, kind='in'):
    for i, n in _wasapi(kind):
        if n == name:
            return i
    return None


# ---------- Windows input level (the "gain" for mics without a knob) ----------
def _endpoint(name):
    d = _active_capture().get(name)
    return d.EndpointVolume if d is not None else None


def get_input_level_db(name):
    try:
        ep = _endpoint(name)
        return ep.GetMasterVolumeLevel(), ep.GetVolumeRange()[:2]
    except Exception:
        return None, None


def set_input_level_db(name, db):
    try:
        ep = _endpoint(name)
        lo, hi = ep.GetVolumeRange()[:2]
        ep.SetMasterVolumeLevel(float(np.clip(db, lo, hi)), None)
        return True
    except Exception:
        return False


def set_input_level_full(name):
    """With a hardware knob, Windows' slider must stay at 100: below that it hides clipping."""
    try:
        ep = _endpoint(name)
        if ep.GetMasterVolumeLevelScalar() < 0.999:
            ep.SetMasterVolumeLevelScalar(1.0, None)
        return True
    except Exception:
        return False


# ---------- engine ----------
class Engine:
    def __init__(self, mic=None):
        timer_res.enable_1ms_timer()
        try:
            ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00008000)  # above normal
        except Exception:
            pass
        self.mic = mic or pick_mic()
        self.profile = load_profile(self.mic) if self.mic else dict(DEFAULT_PROFILE)
        self.chain = None
        self.inq = queue.Queue(maxsize=200)
        self.ring = collections.deque()
        self.ring_n = 0
        self.lock = threading.Lock()
        self.taps = []
        self.in_db = self.out_db = self.in_peak_db = -120.0
        self.clip_until = 0.0
        self.status = 'stopped'
        self.error = None
        self.running = False
        self.slow_blocks = 0
        self.underruns = 0
        self.channel = 0
        self.nch = 1
        self.ch_energy = np.zeros(2)
        self.latency_ms = 0.0
        self.block_ms = collections.deque(maxlen=200000)
        self.buffer_target = int(0.025 * SR)  # 25 ms safety margin (tunable)
        self.buffer_max = int(0.05 * SR)     # trim back to keep delay low
        self.refilling = True
        self.mmcss = False
        self.qdrops = 0

    def _in_cb(self, indata, frames, t, status):
        try:
            self.inq.put_nowait(indata.copy())
        except queue.Full:
            self.qdrops += 1

    def _out_cb(self, outdata, frames, t, status):
        with self.lock:
            buf = np.zeros(frames, np.float32)
            if self.refilling:  # build a safety margin back up before playing (avoids rapid-fire gaps)
                if self.ring_n < self.buffer_target:
                    outdata[:] = 0
                    return
                self.refilling = False
            got = 0
            while got < frames and self.ring:
                blk = self.ring[0]
                take = min(len(blk), frames - got)
                buf[got:got + take] = blk[:take]
                if take < len(blk):
                    self.ring[0] = blk[take:]
                else:
                    self.ring.popleft()
                got += take
            self.ring_n -= got
            if got < frames and self.running:
                self.underruns += 1
                self.refilling = True
        outdata[:] = buf[:, None]

    def _pick_channel(self, x):
        """Interfaces with 2 inputs: follow the input that actually has the mic (sticky)."""
        if x.shape[1] < 2:
            return x[:, 0]
        e = (x ** 2).mean(0)
        self.ch_energy = 0.995 * self.ch_energy + 0.005 * e[:2]
        other = 1 - self.channel
        if self.ch_energy[other] > 10 * self.ch_energy[self.channel] + 1e-10:
            self.channel = other
        return x[:, self.channel]

    def _boost_thread(self):
        """Ask Windows to schedule this thread like pro-audio software (MMCSS), ahead of games."""
        try:
            avrt = ctypes.WinDLL('avrt')
            idx = ctypes.c_ulong(0)
            avrt.AvSetMmThreadCharacteristicsW.restype = ctypes.c_void_p
            h = avrt.AvSetMmThreadCharacteristicsW('Pro Audio', ctypes.byref(idx))
            if h:
                avrt.AvSetMmThreadPriority(ctypes.c_void_p(h), 2)  # AVRT_PRIORITY_HIGH
            self.mmcss = bool(h)
        except Exception:
            self.mmcss = False
        try:
            k = ctypes.windll.kernel32
            k.GetCurrentThread.restype = ctypes.c_void_p
            k.SetThreadPriority(ctypes.c_void_p(k.GetCurrentThread()), 2)  # THREAD_PRIORITY_HIGHEST
        except Exception:
            pass

    def _worker(self):
        self._boost_thread()
        pend = np.zeros(0, np.float32)
        while self.running:
            try:
                x = self.inq.get(timeout=0.2)
            except queue.Empty:
                continue
            pend = np.concatenate([pend, self._pick_channel(x).astype(np.float32)])
            while len(pend) >= BLOCK:
                blk, pend = pend[:BLOCK], pend[BLOCK:]
                t0 = time.perf_counter()
                pk = float(np.abs(blk).max())
                self.in_peak_db = 20 * np.log10(pk + 1e-9)
                if pk > 0.98:
                    self.clip_until = time.time() + 1.5
                out, post = self.chain.process(blk)
                self.out_db = 0.8 * self.out_db + 0.2 * (10 * np.log10((out ** 2).mean() + 1e-12))
                for q, kind in list(self.taps):
                    try:
                        q.put_nowait(blk if kind == 'raw' else post if kind == 'post_nr' else
                                     (blk, out) if kind == 'both' else out)
                    except queue.Full:
                        pass
                with self.lock:
                    self.ring.append(out)
                    self.ring_n += len(out)
                    while self.ring_n > self.buffer_max:  # clock drift between the two devices
                        d = self.ring.popleft()
                        self.ring_n -= len(d)
                dt = time.perf_counter() - t0
                self.block_ms.append(dt * 1000)
                if dt > 0.008:
                    self.slow_blocks += 1

    def start(self):
        self.error = None
        if not self.mic:
            self.status, self.error = 'error', 'No microphone found.'
            return False
        out = find_cable()
        if out is None:
            self.status, self.error = 'no_cable', 'VB-Cable is not installed.'
            return False
        inp = device_index(self.mic, 'in')
        if inp is None:
            self.status, self.error = 'error', f'"{self.mic}" is not connected.'
            return False
        if self.profile.get('has_knob'):
            set_input_level_full(self.mic)
        try:
            self.chain = Chain(self.profile)
            self.chain.set_loudness(i18n.load_settings().get('loudness_db', 0.0))
        except Exception as ex:
            self.status, self.error = 'error', f'Noise remover failed to load: {ex}'
            return False
        self.nch = min(2, sd.query_devices(inp)['max_input_channels'])
        self.running = True
        threading.Thread(target=self._worker, daemon=True).start()
        ws = sd.WasapiSettings(auto_convert=True)
        try:
            self.sin = sd.InputStream(device=inp, channels=self.nch, samplerate=SR, blocksize=BLOCK, dtype='float32',
                                      latency='low', callback=self._in_cb, extra_settings=ws)
            self.sout = sd.OutputStream(device=out, channels=2, samplerate=SR, blocksize=BLOCK, dtype='float32',
                                        latency='low', callback=self._out_cb, extra_settings=ws)
            self.sin.start()
            self.sout.start()
        except Exception as ex:
            self.running = False
            self.status, self.error = 'error', f'Could not open audio: {ex}'
            return False
        self.latency_ms = 1000 * (self.sin.latency + self.sout.latency + self.buffer_target / SR) + 10 + 30
        self.status = 'running'
        return True

    def stop(self):
        self.running = False
        for s in ('sin', 'sout'):
            if hasattr(self, s):
                try:
                    getattr(self, s).stop(); getattr(self, s).close()
                except Exception:
                    pass
        self.status = 'stopped'

    def switch_mic(self, mic):
        self.stop()
        self.__init__(mic)
        return self.start()

    def add_tap(self, kind='raw'):
        q = queue.Queue(maxsize=3000)
        self.taps.append((q, kind))
        return q

    def remove_tap(self, q):
        self.taps = [t for t in self.taps if t[0] is not q]

    def apply_profile(self, p):
        self.profile.update(p)
        if self.chain is not None:
            self.chain.p = self.profile
            self.chain.set_eq(self.profile['eq'])
            self.chain.set_strength(self.profile['nr_atten_db'])
            self.chain.set_character(self.profile.get('character_eq') or [])
        save_profile(self.mic, self.profile)
