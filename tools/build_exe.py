"""Build dist/Sesli.exe: one file you can send to a friend. Requires `pip install -r requirements-dev.txt`."""
import os
import PyInstaller.__main__

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(ROOT, 'sesli')
sep = os.pathsep


def data(src, dest):
    return f'--add-data={os.path.join(SRC, src)}{sep}{dest}'


PyInstaller.__main__.run([
    os.path.join(SRC, 'launch.py'),
    '--name=Sesli',
    '--onefile',
    '--windowed',
    '--noconfirm',
    f'--icon={os.path.join(ROOT, "assets", "icon.ico")}',
    f'--splash={os.path.join(ROOT, "assets", "splash.png")}',
    f'--paths={SRC}',
    data('bin', 'bin'),
    data('models', 'models'),
    data('assets', 'assets'),
    data('target.json', '.'),
    '--hidden-import=gui',
    '--hidden-import=comtypes.stream',
    '--hidden-import=pystray._win32',
    '--collect-submodules=pycaw',
    f'--distpath={os.path.join(ROOT, "dist")}',
    f'--workpath={os.path.join(ROOT, "build")}',
    f'--specpath={os.path.join(ROOT, "build")}',
])
