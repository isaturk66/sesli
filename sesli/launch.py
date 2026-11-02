"""Start Sesli: show a small "Starting…" window instantly (before the heavy audio libraries load),
and make sure only one copy runs — a second click just brings the open window to the front."""
import ctypes
import sys
import tkinter as tk

try:  # own taskbar identity, so Windows shows Sesli's icon instead of Python's
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Sesli.App')
except Exception:
    pass

k32 = ctypes.windll.kernel32
u32 = ctypes.windll.user32
_mutex = k32.CreateMutexW(None, False, 'Sesli.SingleInstance')
if k32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS -> already running
    h = u32.FindWindowW(None, 'Sesli')
    if h:
        u32.ShowWindow(h, 9)  # SW_RESTORE
        u32.SetForegroundWindow(h)
    sys.exit(0)

QUIET = '--minimized' in sys.argv  # started with Windows: no splash

splash = tk.Tk()
splash.overrideredirect(True)
splash.configure(bg='#ffffff', highlightbackground='#dcdad5', highlightthickness=1)
w, h = 300, 140
splash.geometry(f'{w}x{h}+{(splash.winfo_screenwidth() - w) // 2}+{(splash.winfo_screenheight() - h) // 2}')
try:
    from paths import res
    _logo = tk.PhotoImage(file=res('assets', 'icon64.png')).subsample(2, 2)
    tk.Label(splash, image=_logo, bg='#ffffff').pack(pady=(18, 0))
except Exception:
    pass
tk.Label(splash, text='Sesli', font=('Segoe UI Semibold', 15), bg='#ffffff', fg='#1d1d1f').pack()
msg = tk.Label(splash, text='Starting…', font=('Segoe UI', 10), bg='#ffffff', fg='#6b6b70')
msg.pack()
splash.attributes('-topmost', True)
if QUIET:
    splash.withdraw()
else:
    splash.update()

msg.config(text='Loading audio engine…')
if not QUIET:
    splash.update()
try:  # the .exe shows a native splash while unpacking; close it now that ours is up
    import pyi_splash
    pyi_splash.close()
except ImportError:
    pass
import gui  # noqa: E402  (heavy: numpy, scipy, sounddevice, noise remover)

splash.destroy()
gui.App().mainloop()
