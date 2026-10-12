# Jarvis — fully offline Windows laptop companion + ESP32 OLED

This is now a **Windows 10/11 x64 laptop project** for your **12th-generation Intel i7 / 16 GB RAM** laptop and similar Intel/AMD laptops. The Pi is unnecessary. Voice input, language model, speech output, local knowledge and animated face all run on the laptop. Your **38-pin ESP32** displays the generated answer on a **0.96-inch SSD1306 I2C 128x64 OLED** through a USB cable.

## Start on your friend's laptop

1. Transfer the **complete prepared folder** to a writable local directory, for example `C:\Jarvis`. Keep `runtime`, `models`, `vendor`, `jarvis`, `scripts`, and `web` together. Do not launch from inside a ZIP or a read-only USB drive.
2. Plug the headset and ESP32 into the laptop. In Windows Sound settings, make the headset your default input and output. Alternatively run **configure_audio.bat** to choose devices explicitly. Enable Windows microphone access for desktop apps.
3. Double-click **start.bat**. It starts Jarvis and opens its browser face at `http://127.0.0.1:8765`. Keep the terminal open. Say **Hey Jarvis**, pause, then ask a question. No SSH, Pi, Docker, Ollama, installed Python, or AI service account is needed.

The prepared bundle includes portable Python and the downloaded models/binaries. If you download **source only from GitHub**, run **setup.bat** once with internet before starting. All normal use is offline afterward. Firmware flashing also needs the ESP32 connected and may require its USB driver on the new laptop.

## First-time OLED setup

Use the ESP32's printed labels, not a guessed physical pin number:

| OLED label | ESP32 label |
|---|---|
| **VCC** | **3V3** |
| **GND** | **GND** |
| **SDA** | **GPIO21 / IO21 / 21** |
| **SCL** | **GPIO22 / IO22 / 22** |

Connect ESP32 USB to the laptop with a **USB data cable**. Unplug it while wiring. See the full [38-pin reference and wiring diagram](esp32/PINOUT.md).

Close Jarvis and Serial Monitor. Double-click **flash_esp32.bat**, enter the COM port shown by Device Manager, and wait. If uploading stays at “Connecting”, hold the board's BOOT button until writing begins. This firmware is for **classic ESP32-WROOM DevKit**, not ESP32-S3/C3, and **SSD1306**, not SH1106. The pin count alone does not establish the exact board model.

Then run **start.bat**. Answers appear both in the browser and on the OLED. Text wraps at 21 characters per line and scrolls automatically when longer than the visible body. The header stays fixed. Missing OLED hardware does not stop voice assistance. [OLED details](esp32/README.md)

## Double-click entry points

| File | Purpose |
|---|---|
| **start.bat** | Start offline Jarvis and open the face |
| **setup.bat** | Install/repair portable Windows dependencies and models; internet needed |
| **configure_audio.bat** | Select microphone and speaker on this laptop |
| **flash_esp32.bat** | Flash the display firmware to the selected COM port |
| **diagnostics.bat** | Check models, dependencies and checksums without network |
| **test_oled.bat** | Send a long text sample to the flashed OLED without running AI |

## Speech and useful commands

- **Hey Jarvis**: wake, then pause briefly and ask. Each new spoken question starts with the wake phrase.
- **Okay stop / stop talking**: cancel speech and generation; browser Stop and Escape also work.
- **Exit**: close Jarvis and its AI/audio workers. It does not shut down Windows or the ESP32.
- Ask questions, request brief explanations, or chat. Replies normally use one or two short sentences.
- “Remember that my name is Anbu.” / “What do you remember about me?” / “Forget my memory.”
- “Set a timer for two minutes.” / “What time is it?” / “What is the date?”

Place UTF-8 `.txt` / `.md` notes in `data/knowledge`. Index them with `runtime\python\python.exe scripts\index_knowledge.py` while Jarvis is stopped. Search uses SQLite keyword retrieval and shows source filenames in the GUI. Saved facts and notes stay local. Timers are not retained after exit/reboot.

## Laptop defaults

| Component | Default |
|---|---|
| Offline LLM | **LiquidAI LFM2.5-1.2B-Instruct Q4_K_M**, 731 MB official GGUF |
| Runtime | **llama.cpp native Windows x64 CPU build** |
| Speech recognition | sherpa-onnx streaming English Zipformer, ~73MB inference files |
| Wake / interrupt / exit | sherpa-onnx 3M int8 keyword detector |
| Voice | Piper Lessac-low English, 16 kHz; hardware-rate conversion when required |
| CPU threads / context |6 LLM threads / 4096 context |
| Idle LLM residency |300 seconds to reduce repeated cold-load delays |
| Idle Piper residency | Retained for the same warm window; preload begins on wake |
| Face | Browser SVG animation at 30 fps; scales to 4K |
| OLED | Separate reconnecting USB serial worker; no inference on ESP32 |

The compact LLM is retained for fast conversation. A laptop can run larger GGUFs, but larger does not automatically improve response latency. No dedicated GPU is assumed. Model quality remains that of a small offline model; it can make factual mistakes and cannot obtain current internet facts. The default language is English.

On Windows, `config.laptop.json` is separate from the legacy Pi settings. Set `idle_unload_seconds` to0 for minimum idle LLM residency or keep 300 for faster repeat conversations. Stop always terminates inference. You can adjust `threads` between 1 and 12, `context` up to 8192, and `max_tokens` up to 256. Longer replies increase time and OLED scrolling duration. Run benchmarks before asserting a particular latency.

The former 3.2 GB Pi system budget is not applied to this 16 GB laptop profile. Windows memory telemetry and a 14 GB estimated-system-use guard are enabled by default. This is an application guard, not a Windows hard job-object memory limit. Keep other programs under control. No measured performance claim is made for your friend's laptop until it is tested there.

## Transfer and privacy

The runtime uses **relative paths**, so it moves with this folder. The full prepared transfer ZIP excludes your personal saved facts, recordings and local configuration, while including the portable runtime, models, CPU binaries, code, firmware and guides. A source-only GitHub ZIP excludes downloaded binaries/models and requires setup.bat.

Default audio follows the new laptop's Windows defaults. If explicit saved device names differ, run configure_audio.bat there. COM port numbers can also change; OLED auto mode performs a firmware handshake, or set `oled_port` to the correct COM name in config.laptop.json.

No API key, cloud service, runtime download, remote font or CDN is used. GUI and llama.cpp bind only to loopback. Do not expose them publicly. USB display traffic contains the answer text and status only. The OLED uses an ASCII font; accents are transliterated and unsupported scripts become `?`.

## Checks and limitations

Run **diagnostics.bat** for integrity checks. Model smoke: `runtime\python\python.exe scripts\model_smoke.py --llama-binary vendor/windows/llama-server.exe`. Run it with Jarvis stopped because it uses the same server port. Run `runtime\python\python.exe scripts\benchmark.py` to measure actual model loading and generation on the target laptop.

Voice latency and headset accuracy depend on the actual CPU, thermal/power mode, microphone and background programs. OLED firmware compilation and serial protocol tests can be checked without a board; the physical display, flashing, address and wiring must be confirmed on your ESP32. Refer to [Windows setup](docs/WINDOWS_SETUP.md), [OLED wiring](esp32/PINOUT.md), [laptop validation](docs/WINDOWS_VALIDATION.md) and [licenses](THIRD_PARTY.md).

The earlier Pi implementation is retained for reference in [PI_LEGACY.md](docs/PI_LEGACY.md). Use the Windows entry points above for this version.
