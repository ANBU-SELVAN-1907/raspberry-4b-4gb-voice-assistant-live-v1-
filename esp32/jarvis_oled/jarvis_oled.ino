// ESP32 DevKit 38-pin / ESP32-WROOM, SSD1306 I2C 128x64.
// VCC -> 3V3, GND -> GND, SDA -> GPIO21, SCL -> GPIO22.
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ArduinoJson.h>
#include "text_layout.h"

constexpr int SDA_PIN = 21, SCL_PIN = 22;
constexpr uint8_t OLED_ADDRESS = 0x3C; // Switch to 0x3D if your module uses that address.
constexpr int BODY_Y = 14, BODY_H = 50, LINE_H = 10;
constexpr size_t MAX_TEXT = 2400, RX_SIZE = 8192;
Adafruit_SSD1306 oled(128, 64, &Wire, -1);
GFXcanvas1 body(128, BODY_H); // Drawing outside this canvas is clipped, including scrolling.
char rx[RX_SIZE], currentText[MAX_TEXT + 1], lines[MAX_LINES][OLED_COLUMNS + 1];
char currentState[17] = "idle", currentSession[17] = "";
size_t rxUsed = 0, lineCount = 1;
bool discardFrame = false, hasHost = false, displayOk = false;
uint32_t sequence = 0, lastFrame = 0, lastReady = 0, scrollTick = 0, holdUntil = 0;
int scrollY = 0;

void resetScroll() { scrollY = 0; holdUntil = millis() + 1600; scrollTick = millis(); }
bool elapsed(uint32_t now, uint32_t deadline) { return int32_t(now - deadline) >= 0; }

void processFrame() {
  JsonDocument doc;
  if (deserializeJson(doc, rx)) return;
  if (doc["ping"].as<int>() == 1) {
    Serial.println(displayOk ? "JARVIS_OLED_READY v1" : "OLED_ERROR check wiring/address 0x3C"); return;
  }
  if (doc["v"].as<int>() != 1 || !doc["text"].is<const char *>() || !doc["session"].is<const char *>()) return;
  const char *session = doc["session"];
  uint32_t incoming = doc["seq"].as<uint32_t>();
  bool newSession = strcmp(session, currentSession) != 0;
  if (!newSession && incoming < sequence) return;
  const char *text = doc["text"];
  size_t length = strnlen(text, MAX_TEXT + 1);
  if (length > MAX_TEXT || strlen(session) > 16) return;
  bool changed = strcmp(text, currentText) != 0;
  bool appended = !newSession && strlen(currentText) > 0 && strncmp(text, currentText, strlen(currentText)) == 0;
  strlcpy(currentSession, session, sizeof(currentSession));
  strlcpy(currentState, doc["state"] | "idle", sizeof(currentState));
  sequence = incoming; hasHost = true;
  if (changed || newSession) {
    strlcpy(currentText, text, sizeof(currentText));
    lineCount = wrapText(*currentText ? currentText : "Please wait...", lines);
    if (!appended) resetScroll(); // Appending tokens never jumps back to the top.
  }
  Serial.print("JARVIS_OLED_ACK "); Serial.println(sequence);
}

void receiveSerial() {
  // Limit work per loop so large serial frames never freeze the animation.
  int budget = 512;
  while (Serial.available() && budget-- > 0) {
    char ch = char(Serial.read());
    if (ch == '\n') {
      if (!discardFrame && rxUsed) { rx[rxUsed] = '\0'; processFrame(); }
      rxUsed = 0; discardFrame = false;
    } else if (ch != '\r' && !discardFrame) {
      if (rxUsed + 1 < RX_SIZE) rx[rxUsed++] = ch;
      else { discardFrame = true; rxUsed = 0; }
    }
  }
}

void drawFrame(uint32_t now) {
  int bottom = max(0, int(lineCount) * LINE_H - BODY_H);
  if (bottom && elapsed(now, holdUntil) && now - scrollTick >= 45) {
    scrollTick = now;
    if (scrollY < bottom) {
      ++scrollY;
      if (scrollY == bottom) holdUntil = now + 2400;
    } else resetScroll();
  }
  body.fillScreen(0);
  body.setTextSize(1); body.setTextColor(1); body.setTextWrap(false);
  for (size_t i = 0; i < lineCount; ++i) {
    int y = int(i) * LINE_H - scrollY;
    if (y > -8 && y < BODY_H) { body.setCursor(1, y); body.print(lines[i]); }
  }
  oled.clearDisplay();
  oled.setTextSize(1); oled.setTextColor(SSD1306_WHITE); oled.setTextWrap(false);
  oled.setCursor(0, 0); oled.print("JARVIS ");
  for (const char *p = currentState; *p && oled.getCursorX() < 122; ++p) oled.write(toupper(*p));
  oled.drawLine(0, 10, 127, 10, SSD1306_WHITE);
  oled.drawBitmap(0, BODY_Y, body.getBuffer(), 128, BODY_H, SSD1306_WHITE);
  oled.display();
}

void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN); Wire.setClock(400000);
  displayOk = oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS);
  if (!displayOk) { Serial.println("OLED_ERROR check wiring/address 0x3C"); return; }
  lineCount = wrapText("Connect USB to laptop and start Jarvis.", lines);
  resetScroll();
  Serial.println("JARVIS_OLED_READY v1");
}

void loop() {
  receiveSerial();
  uint32_t now = millis();
  if (displayOk && !hasHost && now - lastReady >= 1000) { Serial.println("JARVIS_OLED_READY v1"); lastReady = now; }
  if (displayOk && now - lastFrame >= 33) { lastFrame = now; drawFrame(now); }
  delay(1);
}
