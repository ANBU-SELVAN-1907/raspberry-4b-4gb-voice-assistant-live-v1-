# Windows setup and transfer

## Prepared folder

Copy the entire project into a writable local folder. `start.bat` uses `runtime/python/python.exe` directly, without an installed Python, virtualenv activation, registry entry, PATH change, Git, or administrator account. All AI models and native binaries stay under this folder. The first source-only setup needs internet; a completed transfer bundle starts offline.

The Python runtime is the official Python 3.13.16 embedded Windows x64 distribution with project-managed dependencies. Its `_pth` file contains relative runtime/site-packages/project paths. Package installation is only performed during setup; runtime use never runs pip. Do not move the runtime separately from the project.

The laptop profile also keeps Piper warm for the LLM idle window. Set `retain_voice` to false to unload it after each reply. On wake its loading overlaps the spoken question; a typed first query can still experience a cold voice load. Stop and Exit always unload both engines.

Downloaded llama.cpp DLLs must stay beside `vendor/windows/llama-server.exe`. Do not copy only that one EXE. The installer verifies expected flags and a real offline model reply. It resolves an official stable release when downloading missing binaries, following the stable release's nightly binary pointer when necessary. Existing prepared binaries are reused. Version records are in runtime/llama-version.json when downloaded by the installer.

## Audio

Use the Plantronics Blackwire 3210 as Windows default recording/playback devices before launching. A different microphone/speaker is supported. Start with headphones to avoid the assistant's voice leaking back into the mic. Windows Settings → Privacy & security → Microphone must allow desktop apps.

For explicit selection run configure_audio.bat. It lists devices and host APIs; prefer Windows WASAPI entries if the device supports the capture format. Names plus host API are saved so changed numeric device indices do not silently select another microphone. On your friend's laptop rerun selection if names differ. Enter on both prompts follows Windows defaults.

Capture is 48 kHz mono by default. If a device does not accept that rate, set `input_rate` to its supported rate in config.laptop.json. sherpa resamples internally. Piper generates 16 kHz mono; the speaker converts to the device's default output rate when 16 kHz is unsupported. The face mouth follows actual audio energy, not phoneme-perfect lip sync.

## ESP32

See esp32/PINOUT.md. Flash once, then the same board can move between laptops without reflashing. Close Arduino Serial Monitor and Jarvis before upload. Device Manager must show a COM port; use official manufacturer drivers for the actual USB bridge if needed. Changing computers may require a fresh USB driver even with the fully prepared project.

Auto discovery probes known USB-serial IDs and confirms `JARVIS_OLED_READY v1`; it sends no answers to an unidentified device. For a specific board, set `oled_port` to its COM port. Serial access is optional and reconnects; USB unplugging does not stop AI or voice. If testing/flashing, close Jarvis first so it releases the COM port.

## Troubleshooting

| Problem | Action |
|---|---|
| start.bat says setup incomplete | Run setup.bat; it preserves existing models and settings |
| Cannot find DLL / Python module | Restore the whole prepared folder, including runtime and vendor; run diagnostics |
| Windows download warning | Use this prepared project from its trusted source; inspect it before launching |
| Port 8765 already used | Close the previous Jarvis terminal using Exit, or change both settings/GUI URL deliberately |
| Saved audio device missing | Run configure_audio.bat on the current laptop |
| Mic access denied | Enable Windows microphone access for desktop apps and unmute the headset |
| No voice output | Set headset as output, check volume and run configure_audio.bat |
| Wake inaccurate | Close-talk headset, brief pause after wake; use browser Wake if needed |
| OLED blank | Check SSD1306 address 0x3C, 3V3/GND, SDA21/SCL22 and board power |
| OLED does not receive replies | Close Serial Monitor; check COM port/USB data cable; run test_oled.bat |
| Upload stuck connecting | Hold BOOT until flashing begins; check selected COM port |
| Friend is offline | Use the completed transfer bundle, not a source-only archive; USB driver must already be available |
| Memory pressure / heavy workers stopped | Close Jarvis, run repair_memory.bat, restart. It reports actual used/free RAM, corrects laptop limits and preserves audio/OLED settings. If less than 1.5 GB remains free, close large apps. Updated Jarvis returns to idle automatically when headroom recovers. |

Logs: run/llama.log, run/speech.log, run/tts.log; terminal logs show OLED connection. Say Exit for clean shutdown. Closing the console abruptly can bypass graceful cleanup; prefer the Exit button/command or Ctrl+C.
