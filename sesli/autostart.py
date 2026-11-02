"""Start Sesli with Windows: a value under HKCU\\...\\Run (per user, no admin rights needed).
Started this way, Sesli opens minimized (``--minimized``)."""
import os
import sys
import winreg

KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
NAME = 'Sesli'
FLAG = '--minimized'


def command():
    if getattr(sys, 'frozen', False):  # the PyInstaller exe
        return f'"{sys.executable}" {FLAG}'
    exe = sys.executable
    w = os.path.join(os.path.dirname(exe), 'pythonw.exe')  # no console window
    launch = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'launch.py')
    return f'"{w if os.path.exists(w) else exe}" "{launch}" {FLAG}'


def _get():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as k:
            return winreg.QueryValueEx(k, NAME)[0]
    except OSError:
        return None


def enabled():
    return _get() is not None


def set_enabled(on):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, NAME, 0, winreg.REG_SZ, command())
        else:
            try:
                winreg.DeleteValue(k, NAME)
            except FileNotFoundError:
                pass


def refresh():
    """If autostart is on but points somewhere else (the exe was moved or replaced), point it here."""
    try:
        cur = _get()
        if cur is not None and cur != command():
            set_enabled(True)
    except OSError:
        pass


def started_minimized():
    return FLAG in sys.argv
