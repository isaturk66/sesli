# Native noise remover (`sesli/bin/deepfilter.dll`)

This is DeepFilterNet's `libDF`, version **v0.5.6**, built as a C library (the `capi` feature). It
exposes `df_create`, `df_process_frame` and the other `df_*` functions. Each call processes one
10 ms frame synchronously, with no threads and no timers.

## Why not the official LADSPA plugin

On Windows its worker thread falls behind real time under load. It then inserts silence, and after
a second of delay it panics on purpose. The synchronous C API avoids that.

## Patch

`capi-thresholds.patch` makes `df_create` use the same frame-skipping thresholds as the `deep-filter`
command-line tool: `-15 / 35 / 35` dB. The C API's defaults (`-10 / 30 / 20`) skip much more
processing, and quality dropped from DNSMOS OVRL 3.37 to 2.36.

## Build

You need Rust and Visual Studio's C++ build tools.

```bat
git clone --depth 1 --branch v0.5.6 https://github.com/Rikorose/DeepFilterNet.git
cd DeepFilterNet
git apply path\to\sesli\native\capi-thresholds.patch
cargo update -p time
:: run inside "x64 Native Tools Command Prompt" (or after calling vcvars64.bat)
:: remap-path-prefix keeps your local paths (and Windows username) out of the DLL
set RUSTFLAGS=--remap-path-prefix=%USERPROFILE%\.cargo\registry\src=crates --remap-path-prefix=%USERPROFILE%\.cargo=cargo --remap-path-prefix=%CD%=DeepFilterNet
cargo rustc -p deep_filter --lib --release --features capi --crate-type cdylib
copy target\release\df.dll path\to\sesli\sesli\bin\deepfilter.dll
```

Two build notes:

- **`cargo update -p time`:** the `time` 0.3.28 in the lockfile doesn't compile with current Rust.
- **Git Bash's `link.exe`:** it shadows the MSVC linker, so build from a VS developer prompt.

The model `sesli/models/DeepFilterNet3_onnx.tar.gz` is copied from the repository's `models/` folder.
DeepFilterNet is dual-licensed MIT / Apache-2.0.
