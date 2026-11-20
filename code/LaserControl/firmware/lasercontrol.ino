/*
 * LaserControl bridge — прошивка контроллера-посредника.
 * Плата: Arduino Mega 2560 (два аппаратных UART) или ESP32 с HardwareSerial.
 *   Serial  (USB)  <-> mBlock 5, 115200 бод, JSON по одной строке.
 *   Serial1 (TX1/RX1) <-> ACMER S1 (GRBL), 115200 бод.
 *
 * Зависимость: ArduinoJson 6.x (https://arduinojson.org/).
 *
 * ВАЖНО: interfacing с лазером класса 4 допускается только при закрытом
 * кожухе/барьере, в очках OD>=4 для 445–455 нм, с вытяжкой и огнетушителем.
 * Проверка границ 130 x 130 мм — программная, не заменяет аппаратную кнопку.
 */

#include <ArduinoJson.h>

static const float FIELD_X = 130.0f;
static const float FIELD_Y = 130.0f;
static const unsigned long GRBL_TIMEOUT_MS = 4000;

float currentX = 0.0f;
float currentY = 0.0f;
float feedrate = 1000.0f;   // мм/мин
int laserPower = 0;        // 0..255 (GRBL S-value)
bool laserOn = false;

String inputBuffer;

// ---------------------------------------------------------------------------
// Вспомогательные функции
// ---------------------------------------------------------------------------

void reply(const char *status, const char *message) {
    StaticJsonDocument<192> doc;
    doc["status"] = status;
    doc["message"] = message;
    doc["x"] = currentX;
    doc["y"] = currentY;
    doc["feed"] = feedrate;
    doc["laser"] = laserOn ? "on" : "off";
    serializeJson(doc, Serial);
    Serial.println();
}

bool inBounds(float x, float y) {
    return x >= 0.0f && x <= FIELD_X && y >= 0.0f && y <= FIELD_Y;
}

int powerToS(int percent) {
    if (percent < 0) percent = 0;
    if (percent > 100) percent = 100;
    return static_cast<int>((percent * 255L) / 100L);
}

// Отправка одной команды в GRBL и ожидание ответа ok / error.
bool sendGrbl(const String &gcode) {
    Serial1.println(gcode);
    Serial.print(F("[GRBL] "));
    Serial.println(gcode);

    unsigned long started = millis();
    String response;
    while (millis() - started < GRBL_TIMEOUT_MS) {
        while (Serial1.available() > 0) {
            char c = static_cast<char>(Serial1.read());
            if (c == '\n' || c == '\r') {
                if (response.length() > 0) {
                    Serial.print(F("[GRBL] "));
                    Serial.println(response);
                    response.trim();
                    if (response.startsWith("ok")) return true;
                    if (response.startsWith("error")) return false;
                    response = "";
                }
            } else {
                response += c;
            }
        }
    }
    reply("error", "GRBL timeout");
    return false;
}

void laserOff() {
    if (laserOn) {
        sendGrbl(F("M5"));
        laserOn = false;
    }
}

bool moveTo(float x, float y) {
    if (!inBounds(x, y)) {
        reply("error", "Out of bounds");
        return false;
    }
    String gcode = F("G1 X");
    gcode += String(x, 2);
    gcode += F(" Y");
    gcode += String(y, 2);
    gcode += F(" F");
    gcode += String(feedrate, 0);
    if (!sendGrbl(gcode)) return false;

    currentX = x;
    currentY = y;
    reply("ok", "Move completed");
    return true;
}

// ---------------------------------------------------------------------------
// Обработчики команд верхнего уровня
// ---------------------------------------------------------------------------

void cmdConnect() {
    // Сброс состояния и запрос версии GRBL. Ответ GRBL читается как есть.
    sendGrbl(F("$I"));
    reply("info", "Ready. Field 130x130 mm. Use OD>=4 for 445-455 nm.");
}

void cmdHome() {
    laserOff();
    if (sendGrbl(F("G28"))) {
        currentX = 0.0f;
        currentY = 0.0f;
        reply("ok", "Home completed");
    }
}

void cmdMove(JsonObject params) {
    float x = params["x"] | 0.0f;
    float y = params["y"] | 0.0f;
    bool abs = params["abs"] | true;

    float targetX = abs ? x : currentX + x;
    float targetY = abs ? y : currentY + y;
    moveTo(targetX, targetY);
}

void cmdLaser(JsonObject params) {
    const char *state = params["state"] | "off";
    if (strcmp(state, "on") == 0) {
        if (!inBounds(currentX, currentY)) {
            reply("error", "Out of bounds");
            return;
        }
        String gcode = F("M3 S");
        gcode += String(laserPower);
        if (sendGrbl(gcode)) {
            laserOn = true;
            reply("ok", "Laser on");
        }
    } else {
        laserOff();
        reply("ok", "Laser off");
    }
}

void cmdPower(JsonObject params) {
    int value = params["value"] | 0;
    laserPower = powerToS(value);
    if (laserOn) {
        String gcode = F("M3 S");
        gcode += String(laserPower);
        sendGrbl(gcode);
    }
    reply("ok", "Power updated");
}

void cmdFeedrate(JsonObject params) {
    float value = params["value"] | 1000.0f;
    if (value < 1.0f) value = 1.0f;
    if (value > 10000.0f) value = 10000.0f;
    feedrate = value;
    reply("ok", "Feedrate updated");
}

void cmdDelay(JsonObject params) {
    unsigned long ms = params["ms"] | 0UL;
    if (ms > 60000UL) ms = 60000UL;
    delay(ms);
    reply("ok", "Delay completed");
}

void cmdLine(JsonObject params) {
    float x1 = params["x1"] | currentX;
    float y1 = params["y1"] | currentY;
    float x2 = params["x2"] | currentX;
    float y2 = params["y2"] | currentY;

    if (moveTo(x1, y1) && moveTo(x2, y2)) {
        reply("ok", "Line completed");
    }
}

void cmdRect(JsonObject params) {
    float x = params["x"] | currentX;
    float y = params["y"] | currentY;
    float w = params["w"] | 0.0f;
    float h = params["h"] | 0.0f;
    if (w <= 0.0f || h <= 0.0f) {
        reply("error", "Invalid rectangle size");
        return;
    }
    if (!inBounds(x, y) || !inBounds(x + w, y + h)) {
        reply("error", "Out of bounds");
        return;
    }
    if (moveTo(x, y) && moveTo(x + w, y) && moveTo(x + w, y + h) &&
        moveTo(x, y + h) && moveTo(x, y)) {
        reply("ok", "Rectangle completed");
    }
}

void cmdCircle(JsonObject params) {
    float cx = params["x"] | currentX;
    float cy = params["y"] | currentY;
    float r = params["r"] | 0.0f;
    if (r <= 0.0f) {
        reply("error", "Invalid radius");
        return;
    }
    if (!inBounds(cx - r, cy - r) || !inBounds(cx + r, cy + r)) {
        reply("error", "Out of bounds");
        return;
    }

    const int steps = 24;
    float firstX = cx + r;
    float firstY = cy;
    if (!moveTo(firstX, firstY)) return;

    for (int i = 1; i <= steps; ++i) {
        float angle = 2.0f * PI * i / steps;
        float x = cx + r * cos(angle);
        float y = cy + r * sin(angle);
        if (!moveTo(x, y)) return;
    }
    reply("ok", "Circle completed");
}

void cmdEmergencyStop() {
    // GRBL: '!' — быстрый останов, '~' — снятие паузы НЕ выполняем,
    // 0x18 (Ctrl+X) — software reset. Лазер выключается в любом случае.
    Serial1.print('!');
    delay(30);
    Serial1.write(0x18);
    laserOn = false;
    reply("info", "Emergency stop: laser off, GRBL reset");
}

void processJson(const String &line) {
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, line);
    if (error) {
        reply("error", "Invalid JSON");
        return;
    }

    const char *cmd = doc["cmd"] | "";
    JsonObject params = doc["params"].as<JsonObject>();

    if (strcmp(cmd, "connect") == 0) cmdConnect();
    else if (strcmp(cmd, "home") == 0) cmdHome();
    else if (strcmp(cmd, "move") == 0) cmdMove(params);
    else if (strcmp(cmd, "laser") == 0) cmdLaser(params);
    else if (strcmp(cmd, "power") == 0) cmdPower(params);
    else if (strcmp(cmd, "feedrate") == 0) cmdFeedrate(params);
    else if (strcmp(cmd, "delay") == 0) cmdDelay(params);
    else if (strcmp(cmd, "line") == 0) cmdLine(params);
    else if (strcmp(cmd, "rect") == 0) cmdRect(params);
    else if (strcmp(cmd, "circle") == 0) cmdCircle(params);
    else if (strcmp(cmd, "emergency_stop") == 0) cmdEmergencyStop();
    else if (strcmp(cmd, "status") == 0) reply("info", "LaserControl bridge active");
    else reply("error", "Unknown command");
}

void setup() {
    Serial.begin(115200);
    Serial1.begin(115200);
    while (!Serial) { }
    inputBuffer.reserve(256);
    reply("info", "LaserControl bridge ready");
}

void loop() {
    while (Serial.available() > 0) {
        char c = static_cast<char>(Serial.read());
        if (c == '\n') {
            inputBuffer.trim();
            if (inputBuffer.length() > 0) {
                processJson(inputBuffer);
            }
            inputBuffer = "";
        } else if (inputBuffer.length() < 512) {
            inputBuffer += c;
        }
    }
}
