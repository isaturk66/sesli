"""Where Sesli keeps its files. Per-user data (language, per-mic setup, log) lives in %APPDATA%/Sesli.
Bundled read-only files (noise-removal model, DLL, icons) live next to the code, or inside the .exe."""
import os, shutil, sys

# PyInstaller unpacks bundled files to sys._MEIPASS; otherwise they sit next to this file
RES = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get('SESLI_DATA') or os.path.join(os.environ.get('APPDATA', RES), 'Sesli')
os.makedirs(DATA, exist_ok=True)

# one-time move from the prototype's folder name
_old = os.path.join(os.environ.get('APPDATA', ''), 'MicChain')
for _f in ('profiles.json', 'settings.json'):
    if os.path.exists(os.path.join(_old, _f)) and not os.path.exists(os.path.join(DATA, _f)):
        shutil.copy(os.path.join(_old, _f), os.path.join(DATA, _f))


def res(*p):
    return os.path.join(RES, *p)
