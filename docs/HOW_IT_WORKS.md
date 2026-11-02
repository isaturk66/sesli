# How Sesli works

## Signal chain

All processing happens in 10 ms blocks at 48 kHz. Every stage is causal and keeps its state between
blocks (`sesli/dsp.py`).

```
mic ─► high-pass 80 Hz ─► DeepFilterNet ─► 5-band EQ ─► expander ─► AGC ─► limiter ─► VB-Cable
```

| Stage | What it does | Notes |
|---|---|---|
| High-pass | Removes desk rumble and handling noise | 4th-order Butterworth, 80 Hz |
| DeepFilterNet 3 | Neural noise removal | Synchronous C API, about 30 ms delay; "Strong" = no attenuation limit, "Gentle" = 24 dB |
| EQ | Low shelf, 3 peaks, high shelf | Fitted per mic during setup (`eqfit.py`) |
| Expander | Pushes leftover noise down in the pauses | Threshold 22 dB under your speech level, ratio 3, 40 dB range |
| AGC | Keeps loudness steady | Adapts only while you speak; 1.5 dB/s max |
| Limiter | Stops peaks above -1 dBFS | Instant attack, 80 ms release |

## The target

Development started with the original author's Behringer C1 on a Focusrite Scarlett. The same
sentences were recorded twice at once: the raw mic, and Discord's processed output (via the Craig
recording bot). Discord's version became the reference.

`sesli/target.json` holds Discord's long-term tonal balance (1/3-octave bands). Setup fits the EQ so
your voice, after noise removal, matches that shape. That's why it works with other mics too: each
mic gets its own EQ that brings it to the same target.

What the measurements showed Discord was doing:

- Almost no tonal change below 2 kHz.
- A 2–3 dB cut at 2–6 kHz and about 5 dB at 8 kHz, which softens harshness.
- A slow AGC.
- Hard gating of the pauses.
- No compression.

## Setup assistant (`assistant.py`)

It never needs to know centimetres, because it works in level changes:

- Moving the mic changes how loud your voice is at the mic. The room noise stays the same. So the
  **voice-over-room ratio (SNR) depends only on distance**: half the distance gives +6 dB.
- The gain knob moves voice and noise together. It only decides where your loudest moments land.

So the assistant measures silence, normal talk and a loud moment, then:

1. **Distance:**
   - SNR below 30 dB: move closer.
   - SNR above 40 dB, proximity boom, or clipping while already very clean: the mic is too close, so
     move back to about 34 dB.
   - Live guidance: at a fixed gain, "moved X dB closer" is simply "your voice got X dB louder".
   - "Lock my distance" skips this step and accepts a small quality cost.
2. **Gain:** loud peaks should land near -10 dBFS. Normal speech is guided into the matching window
   while you turn the knob. For mics without a knob, Sesli sets the Windows input level itself.
3. **Check:** measures again. If it still clips, it lowers the gain target by 3 dB and retries.
4. **Calibrate:** 20 s of reading, then the EQ is fitted to the target and the expander and AGC
   thresholds are set from your speech level.

With a hardware knob, the Windows input slider is forced to 100. A lower slider hides converter
clipping: the clipped peaks appear below 0 dBFS, so the clipping looks like a normal level.

## Real-time robustness

What we found while making it live:

- **DeepFilterNet's LADSPA plugin is unusable live on Windows.** Its worker thread sleeps on the
  15.6 ms system timer, falls behind, inserts silence, and finally aborts on purpose. Sesli uses the
  synchronous `libDF` C API instead, built with CLI-equivalent thresholds (see `native/`).
- **Games take CPU from the audio thread.** The processing thread registers with Windows MMCSS as
  "Pro Audio" at high priority, and a 25 ms jitter buffer absorbs short stalls. Under Battlefield 6
  plus YouTube that gave 0–2 short gaps per 90 s, at a median of 3.6 ms of work per 10 ms block.
- **Total delay** from mic to VB-Cable is about 110 ms.

`tools/stress.py` runs the real engine and prints these timing figures.
