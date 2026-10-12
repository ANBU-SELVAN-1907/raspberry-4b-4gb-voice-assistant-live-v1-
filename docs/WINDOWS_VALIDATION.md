# Windows validation

Verified on 12 October 2026 with the project's **portable Python 3.13.16 x64 runtime**, not a system Python installation.

| Check | Result |
|---|---|
| Python unit/integration suite |22 tests passed, including 20 turns, cancellation, memory guards, OLED framing, Unicode normalization, stable device names and continuous resampling |
| Real offline speech-model smoke | Hey Jarvis / Okay stop / Exit detected; France question transcribed |
| Real llama.cpp/LFM2.5 model | “The capital of France is Paris.” |
| Real Piper subprocess |16kHz PCM generated and streamed |
| Windows audio | Default microphone stream opened; actual spoken answer sent through current speaker |
| Two complete voice turns | Passed; normal worker shutdown verified |
| Portable relocation | Copied runtime imported NumPy, ONNX speech modules, aiohttp and serial under a different directory with spaces |
| ESP32 firmware | Compiled for classic esp32:esp32:esp32; 300,489 bytes flash, 38,240 bytes static RAM |
| PowerShell / Python / JS | Syntax and dependency checks performed |
| Physical ESP32/OLED upload and scrolling | Pending your connected hardware |
| Friend's laptop headset/latency | Pending that laptop |

One local test measured a cold typed-query first audio at 5.89 seconds and a warm second turn at 1.68 seconds. These figures exclude utterance duration and measure audio submission rather than sound at the ear. They are **not a promise for a different laptop**, and firmware compilation was also running on the machine. Voice preload overlaps a spoken question; the warm mode avoids repeated model loading.

A real Windows startup test exposed a native library load-order hang: NumPy is now imported before sherpa creates inference threads, which resolved it. The test suite deliberately injects a speaker failure in one case to verify recovery; its expected error log is not a deployment failure.

The firmware uses a pinned classic-ESP32 Arduino 2.0.17 core and current downloaded OLED/JSON libraries. The local SDK extractor skips other chip families to reduce disk use; official archive checksums remain verified. Windows short-path compiler overrides avoid exceeding GCC's command-line length limit in long paths. The prepared bundle contains the compiled image and native flasher, so the receiving laptop does not need the SDK or compiler.

Check the physical hardware using test_oled.bat and the ESP32 wiring guide. A successful build proves source compatibility, not your panel's address, wiring or visible scroll smoothness. Close Jarvis before flashing or testing OLED serial access. The USB bridge driver must be available on the receiving Windows machine.
