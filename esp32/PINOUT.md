# 38-pin ESP32 and 0.96-inch OLED

This project targets a **classic ESP32-WROOM / ESP32 DevKitC-style 38-pin board** and a **4-pin SSD1306 I2C 128x64 OLED**. The number of pins alone does not identify a board model: match its printed labels. ESP32-S3/C3 boards use different layouts.

## Connect these four wires

| OLED printed label | ESP32 printed label | Purpose |
|---|---|---|
| VCC / VDD | **3V3** | 3.3 V power |
| GND | **GND** | Common ground |
| SDA | **21 / IO21 / GPIO21** | I2C data |
| SCL / SCK | **22 / IO22 / GPIO22** | I2C clock |

Unplug USB while wiring. Power this OLED from **3V3**, not VIN/5V. OLED connector order varies; do not assume the first pin is ground. The confirmed display is I2C, not the 7-pin SPI version.

![OLED wiring by label](oled-wiring.svg)

Connect the ESP32's USB connector to the laptop with a **data-capable USB cable**. There is no laptop-to-ESP32 RX/TX jumper wiring: the board's onboard USB serial bridge handles communication. The headset also connects to the laptop, in a different USB port.

## Reference: common DevKitC 38-pin header labels

The following is the **official DevKitC V4 reference**, not a guarantee of the physical arrangement of every 38-pin clone. It gives both 19-pin headers in Espressif's numbering. For this project only 3V3, GND, IO21 and IO22 are needed. Confirm your board labels before connecting.

| Header position | J2 label | J3 label |
|---:|---|---|
| 1 | 3V3 | GND |
| 2 | EN | IO23 |
| 3 | VP / GPIO36 | **IO22 — OLED SCL** |
| 4 | VN / GPIO39 | TX / GPIO1 |
| 5 | IO34 | RX / GPIO3 |
| 6 | IO35 | **IO21 — OLED SDA** |
| 7 | IO32 | GND |
| 8 | IO33 | IO19 |
| 9 | IO25 | IO18 |
| 10 | IO26 | IO5 |
| 11 | IO27 | IO17 |
| 12 | IO14 | IO16 |
| 13 | IO12 | IO4 |
| 14 | GND | IO0 / BOOT |
| 15 | IO13 | IO2 |
| 16 | D2 / GPIO9 | IO15 |
| 17 | D3 / GPIO10 | D1 / GPIO8 |
| 18 | CMD / GPIO11 | D0 / GPIO7 |
| 19 | 5V | CLK / GPIO6 |

EN is reset. VP/VN and GPIO34/35 are input-only. D0/D1/D2/D3/CMD/CLK are flash connections on this module; leave them alone. IO0 is used by BOOT during flashing. GPIO21/22 are set explicitly by this firmware, so there is no dependence on an Arduino default-pin setting.

Source: [Espressif ESP32-DevKitC V4 user guide and pin layout](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32/esp32-devkitc/user_guide.html).
