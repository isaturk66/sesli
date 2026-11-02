# Building `Sesli.exe`

Build in a **clean virtual environment**. PyInstaller bundles whatever it finds importable, and a
global Python with PyTorch or Transformers turned a 70 MB exe into 386 MB.

```bat
python -m venv .venv-build
.venv-build\Scripts\python -m pip install -r requirements.txt pyinstaller
.venv-build\Scripts\python tools\build_exe.py
```

The result is `dist\Sesli.exe`: a single file with Python, the noise remover, the model and the icon
inside. Send that one file to a friend. On their side:

1. They run `Sesli.exe`. Windows SmartScreen may warn because the file isn't signed: they click
   **More info → Run anyway**.
2. If VB-Cable is missing, Sesli shows a download button and three install steps.
3. They pick a language and run the setup assistant.

Notes:

- **Startup:** each start unpacks itself to a temp folder, which takes about 10–15 s, a bit more the
  first time while Windows Defender scans it. A splash window shows during that time.
- **Sending:** the exe is about 70 MB, which is too big for a normal Discord upload. Send it through
  Google Drive, WeTransfer or similar.
- **Data:** user data still lives in `%APPDATA%\Sesli`, so updating the exe keeps everyone's setup.
- **Releases (automatic):** run `git tag v0.2.0 && git push --tags`. GitHub Actions
  (`.github/workflows/release.yml`) builds the exe on a clean Windows runner and publishes it as a
  Release. **Actions → Release → Run workflow** builds without releasing, and you download the result
  as an artifact. Never commit the exe itself.
