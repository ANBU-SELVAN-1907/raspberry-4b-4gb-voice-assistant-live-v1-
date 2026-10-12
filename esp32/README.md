# OLED response display

Read [PINOUT.md](PINOUT.md) before connecting. Defaults: classic ESP32-WROOM DevKit, SSD1306 128x64 I2C, address 0x3C, SDA21, SCL22, USB serial115200.

1. Close Jarvis and any Arduino Serial Monitor before flashing.
2. Connect ESP32 with a USB data cable. In Windows Device Manager → Ports, find its COM port. Install the board's manufacturer USB driver if there is no port (usually CP210x or CH340 for these boards).
3. Double-click **flash_esp32.bat**, enter that COM port, and wait for upload. First-time firmware compilation downloads the official ESP32 tools and Arduino libraries. Press and hold BOOT if the uploader stays at “Connecting”; release when writing starts. The tool writes only to the selected ESP32.

The **prepared transfer bundle** includes a compiled, checksum-verified classic-ESP32 image and a native flasher. On that bundle flash_esp32.bat flashes directly **without internet or a compiler**. Source-only copies fall back to the build script, which downloads official tools. A prebuilt image targets the confirmed SSD1306 address 0x3C/pins 21 and 22; changes require rebuilding.
4. Connect the four OLED wires, then run **start.bat**. The OLED initially says “Connect USB to laptop and start Jarvis.” It then shows state and your generated answer.

The assistant works when the OLED is unplugged. It reconnects automatically. Automatic discovery probes common ESP32 USB serial adapters and **requires a Jarvis firmware handshake** before sending answers. If multiple boards exist or your adapter is different, set `oled_port` to `COM5` (your port) in `config.laptop.json`. Stop Serial Monitor: only one program can open a COM port at a time. Set `oled_enabled` to false to disable the display link.

## Readability and scrolling

- Font is6×8 pixels, size 1: **21 characters per line**, 10 pixels line spacing, about 5 body lines visible.
- A fixed header shows Jarvis state. A separate 50 pixel-high drawing canvas clips scrolling text, so text cannot overlap the header.
- Words wrap naturally; exceptionally long words/URLs are broken across lines.
- Long responses scroll vertically at about 22 pixels/second, with a 1.6 second opening pause and 2.4 second pause at the bottom, then repeat from the top.
- Streaming replies update at most 5 times/second over serial. New tokens append without restarting the scroll. A new question replaces the old response and resets scrolling.
- Complete bounded snapshots prevent missing fragments from corrupting text. Maximum 2400 ASCII characters matches the app's response-display limit. ASCII transliteration keeps accents/smart punctuation readable; this small font does not support Tamil or other Unicode scripts.
- The OLED displays text only; the animated face remains in the laptop browser. No AI runs on the ESP32.

The header/data rate and scroll speed can be changed in `jarvis_oled.ino`. `OLED_ADDRESS` can be changed to0x3D if needed. A SH1106 controller needs a different display driver; this firmware specifically targets the confirmed SSD1306.

## Protocol

USB 115200 baud, newline-terminated ASCII JSON. Laptop sends `{"v":1,"session":"...","seq":1,"state":"speaking","text":"..."}`. Firmware acknowledges with `JARVIS_OLED_ACK <seq>`. A ping `{"ping":1}` returns `JARVIS_OLED_READY v1`. New session IDs allow clean laptop restarts. Frames exceeding 8191 bytes or invalid JSON are discarded. Serial input processing is bounded per loop to keep display drawing responsive. Replies use a single coalesced snapshot on the laptop rather than an accumulating token queue.

Firmware can be compiled without an ESP32 using `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup_esp32.ps1 -CompileOnly`. Physical wiring, display contrast and serial flashing still need to be checked on the actual hardware.
