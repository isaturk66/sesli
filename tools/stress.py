"""Run the real live engine (mic -> chain -> VB-Cable) for N seconds and report timing health."""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sesli"))
import engine  # noqa: E402

secs = int(sys.argv[1]) if len(sys.argv) > 1 else 180
e = engine.Engine()
assert e.start(), e.error
time.sleep(0.5); print(f'mic: {e.mic} | est. delay {e.latency_ms:.0f} ms | pro-audio scheduling: {e.mmcss}', flush=True)
t0 = time.time(); last = (0, 0, 0)
while time.time() - t0 < secs:
    time.sleep(10)
    b = np.array(e.block_ms)
    print(f'{time.time() - t0:5.0f}s blocks {len(b)} median {np.median(b):.2f} ms  p99 {np.percentile(b, 99):.2f}  max {b.max():.1f}  '
          f'slow>8ms {e.slow_blocks}  output gaps {e.underruns}  input drops {e.qdrops}  ring {e.ring_n / 48:.0f} ms', flush=True)
e.stop()
b = np.array(e.block_ms)
print(f'TOTAL {len(b)} blocks ({len(b) / 100:.0f} s audio): median {np.median(b):.2f} ms, p99.9 {np.percentile(b, 99.9):.2f}, '
      f'max {b.max():.1f}; over 10 ms: {(b > 10).sum()}; output gaps {e.underruns}; input drops {e.qdrops}')
