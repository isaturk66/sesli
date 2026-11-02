<p align="center"><img src="assets/icon.png" width="96" alt="Sesli logo"></p>

<h1 align="center">Sesli</h1>

<p align="center">Clean, studio-style voice from any microphone, live, on Windows.</p>

Sesli processes your mic live and sends the result to a virtual microphone. It does:

- **Neural noise removal** with [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet): fans, keyboards, room hiss.
- **Tone matching**: an EQ that's fitted to your voice and mic once, during setup.
- **Automatic level**: a slow automatic gain control, a soft expander for the pauses, and a peak limiter.
- **A setup assistant** that tells you where to put the mic (closer or further) and how to set the gain (knob up or down, or automatic for USB mics). It measures this instead of guessing.

The app has an English and a Turkish interface.

## How it works

```
your mic ──► Sesli ──► VB-Cable ("CABLE Input") ──► your app picks "CABLE Output" as its mic
```

Open Sesli and processing starts. Close it and it stops. There's nothing to configure beyond the
setup assistant.

## Download

Get **`Sesli.exe`** from the [latest release](https://github.com/isaturk66/sesli/releases/latest). It's one
file with nothing else to install, except VB-Cable (Sesli shows you how). Windows may say "unknown
publisher" because the file isn't code-signed: click **More info → Run anyway**.

## Install (from source)

1. Install **Windows 10/11** and **Python 3.11+**.
2. Run `pip install -r requirements.txt`.
3. Install **[VB-Cable](https://vb-audio.com/Cable/)**, the free virtual audio cable. If it's missing, Sesli shows the steps.
4. Double-click **`Sesli.bat`**.

To build a single `.exe` you can send to someone, see [docs/BUILDING.md](docs/BUILDING.md).

## Using it

1. **First start:** pick your language, then run the setup assistant. It takes about a minute. Each
   recording step waits until you click **I'm ready**.
2. **In your voice or streaming app:** set the microphone to **CABLE Output (VB-Audio Virtual Cable)**.
   Turn **off** the app's own Noise Suppression, Echo Cancellation and Automatic Gain Control, because
   Sesli does those.
3. **To hear yourself:** click **Test my mic**. It records 8 seconds of exactly what others will hear and
   plays it back.
4. **To change your tone:** click **Tune by ear**. You record 10 seconds, then make up to 14 blind
   choices. It starts with a few clearly different options, then fine-tunes with pairs, and finishes
   with a blind check against your original sound. **Reset tone** undoes it.
5. **To start with Windows:** tick **Start Sesli when Windows starts**. It then opens minimized at login.

Very quiet mics (cheap earbuds, for example) are fine: if your mic is still too quiet at its maximum
level, the setup assistant adds a digital boost.

Each microphone keeps its own setup. Settings and logs are in `%APPDATA%\Sesli`.

## How good is it?

Sesli was developed against a measured reference, a popular voice app's built-in processing of the
same voice, and checked with blind A/B listening tests:

| Comparison | Blind result |
|---|---|
| Sesli (live) vs the reference | Sesli preferred 4/4 (the reference had hiss) |
| Sesli live vs offline render | indistinguishable (1–1, 2 ties) |

The details are in [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md).

## License

MIT, see [LICENSE](LICENSE). Bundled DeepFilterNet components keep their own MIT / Apache-2.0
licenses (see `native/`).

## Credits

- Noise removal: **DeepFilterNet** by Hendrik Schröter (MIT / Apache-2.0). `sesli/bin/deepfilter.dll`
  is built from its `libDF` C API, and `sesli/models/DeepFilterNet3_onnx.tar.gz` is its published
  model. See [native/README.md](native/README.md).
- Virtual cable: **VB-Cable** by VB-Audio. It isn't bundled; users install it themselves.
