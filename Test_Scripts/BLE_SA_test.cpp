// /*
//  * main.cpp  —  Step 1 BLE OOP Test
//  * Board: Seeed Studio XIAO nRF52840 (non-Sense)
//  *
//  * TX: sends "COUNT:<n>\n" at 5 Hz
//  * RX: 0x01 = blink red LED 200 ms,  0x00 = LED off
//  *
//  * Step 2 preview — adding IMU will look like:
//  *     BLEComms  ble;
//  *     IMUReader imu(&ble);
//  *     void setup() { ble.setReceiveCallback(onRx); ble.begin("XIAO"); imu.begin(); }
//  *     void loop()  { ble.update(); imu.update(); }
//  */

// #include <Arduino.h>
// #include "BLEComms.h"

// BLEComms ble;

// // ── Counter TX ────────────────────────────────────────────────────────────────
// static uint32_t counter    = 0;
// static uint32_t lastSendMs = 0;
// static const uint32_t SEND_MS = 200;   // 5 Hz

// // ── Non-blocking LED blink ────────────────────────────────────────────────────
// static bool     blinkActive  = false;
// static uint32_t blinkStartMs = 0;
// static const uint32_t BLINK_MS = 200;

// // XIAO LEDs are active-LOW
// inline void ledOn()  { digitalWrite(LED_RED, LOW);  }
// inline void ledOff() { digitalWrite(LED_RED, HIGH); }

// void requestBlink() {
//     ledOn();
//     blinkActive  = true;
//     blinkStartMs = millis();
// }

// void updateBlink() {
//     if (blinkActive && (millis() - blinkStartMs >= BLINK_MS)) {
//         ledOff();
//         blinkActive = false;
//     }
// }

// // ── BLE receive callback ──────────────────────────────────────────────────────
// // In Step 3 this expands to trigger the HapticDriver instead of the LED.
// void onBLEReceive(const uint8_t* data, size_t len) {
//     for (size_t i = 0; i < len; i++) {
//         uint8_t b = data[i];
//         Serial.print("[RX] 0x");
//         Serial.println(b, HEX);

//         if (b == 0x01) {
//             Serial.println("  -> Blink ON");
//             requestBlink();
//         } else if (b == 0x00) {
//             Serial.println("  -> LED OFF");
//             blinkActive = false;
//             ledOff();
//         }
//     }
// }

// // ── setup() ──────────────────────────────────────────────────────────────────
// void setup() {
//     Serial.begin(115200);

//     pinMode(LED_RED,   OUTPUT); ledOff();
//     pinMode(LED_GREEN, OUTPUT); digitalWrite(LED_GREEN, HIGH);
//     pinMode(LED_BLUE,  OUTPUT); digitalWrite(LED_BLUE,  HIGH);

//     Serial.println("=== Step 1 BLE OOP Test ===");

//     ble.setReceiveCallback(onBLEReceive);   // register BEFORE begin()
//     ble.begin("XIAO_TEST");

//     Serial.println("Ready.");
// }

// // ── loop() ───────────────────────────────────────────────────────────────────
// void loop() {
//     ble.update();       // always call — drains RX, fires callbacks
//     updateBlink();

//     if (!ble.connected()) return;

//     uint32_t now = millis();
//     if (now - lastSendMs < SEND_MS) return;
//     lastSendMs = now;

//     char buf[32];
//     snprintf(buf, sizeof(buf), "COUNT:%lu\n", (unsigned long) counter++);
//     ble.send(buf);
//     Serial.print("[TX] "); Serial.print(buf);
// }