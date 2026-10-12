#pragma once
#include <stddef.h>
#include <string.h>

static constexpr size_t OLED_COLUMNS = 21;
static constexpr size_t MAX_LINES = 256;

// Monospaced font: 6px per character. 21 * 6 = 126px on a 128px display.
inline size_t wrapText(const char *text, char lines[MAX_LINES][OLED_COLUMNS + 1]) {
  size_t count = 1, used = 0;
  memset(lines, 0, MAX_LINES * (OLED_COLUMNS + 1));
  const char *p = text;
  while (*p && count <= MAX_LINES) {
    while (*p == ' ' || *p == '\n' || *p == '\r' || *p == '\t') ++p;
    if (!*p) break;
    const char *word = p;
    while (*p && *p != ' ' && *p != '\n' && *p != '\r' && *p != '\t') ++p;
    size_t length = size_t(p - word);
    if (used && used + 1 + length > OLED_COLUMNS) {
      if (count >= MAX_LINES) break;
      ++count; used = 0;
    }
    if (used) lines[count - 1][used++] = ' ';
    for (size_t i = 0; i < length; ++i) {
      if (used == OLED_COLUMNS) {
        if (count >= MAX_LINES) return count;
        ++count; used = 0;
      }
      unsigned char ch = static_cast<unsigned char>(word[i]);
      lines[count - 1][used++] = (ch >= 32 && ch <= 126) ? char(ch) : '?';
    }
    lines[count - 1][used] = '\0';
  }
  return count;
}
