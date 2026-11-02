# Sesli: notes for Claude

Sesli is a Windows live voice processor: mic → HPF → DeepFilterNet → EQ → expander → AGC → limiter
→ VB-Cable. It has a Tk GUI and a setup assistant, and its UI is in English and Turkish. Read
`docs/HOW_IT_WORKS.md` first.

## Layout

- `sesli/launch.py` is the entry point. It handles the single-instance mutex and the instant
  splash, then imports `gui`.
- `sesli/gui.py` holds the main window (`App`) and the setup wizard (`Setup`). All UI text goes
  through `i18n.T(key)`. Add every key in **both** `en` and `tr`.
- `sesli/engine.py` handles devices (WASAPI, found by role, never by brand), per-mic profiles, the
  live engine, MMCSS, and the jitter buffer.
- `sesli/dsp.py` is the streaming chain. `df_native.py` wraps `bin/deepfilter.dll`.
- `sesli/tonesearch.py` holds the Tune-by-ear search (explore, then refine, then a blind check against the original; hard capped at 14 choices). `tuner.py` is its window, with a loop bar. The result is a `character_eq` per mic, applied in `dsp.py` after the EQ.
- `sesli/assistant.py` holds the placement and gain logic (see the model in its docstring).
  `eqfit.py` fits the EQ to `target.json`.
- `sesli/paths.py` resolves file locations. Bundled resources go through `res()`, which works from
  source and from the PyInstaller exe. User data lives in `%APPDATA%\Sesli` (override with `SESLI_DATA`).
- `tools/stress.py` runs the real engine and reports timing. `native/` has the DLL build.

## Rules

- **Never hardcode the original author's hardware** (Focusrite, C1, an installed VB-Cable). Sesli
  is shared with non-technical friends, so detect, guide, and show help screens instead.
- **Keep tunables as named constants or profile fields,** not magic numbers inside DSP code.
- **Judge audio changes by measurement and blind A/B listening,** never by description alone.
- **The audio thread budget is 10 ms per block.** Anything heavier than numpy and the DLL call
  belongs outside `Engine._worker`.
- **Don't run the engine or `tools/stress.py` while the user is in a call.** It opens the mic and
  writes into VB-Cable alongside the running app.

## Build the exe

Run `python tools/build_exe.py`. It uses PyInstaller in onefile mode, with a splash and the icon.
See `docs/BUILDING.md`.
