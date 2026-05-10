/*
 * main.cpp  —  Full integration
 * Board  : Seeed Studio XIAO nRF52840
 *
 * - IMUReader   reads GAME_ROTATION_VECTOR at IMU_RATE_HZ
 * - BLEComms    sends "roll,pitch,yaw\n" to laptop on every sample
 * - HapticDriver fires effect #15 when 0x01 arrives from laptop
 *
 * Adjust IMU_RATE_HZ freely — valid range 10–250 Hz.
 */

#include <Arduino.h>
#include "BLEComms.h"
#include "IMUReader.h"
#include "HapticDriver.h"

// ── Customisable rate ─────────────────────────────────────────────────────────
static const uint8_t IMU_RATE_HZ = 50;   // ← change this freely

// ── Instances ─────────────────────────────────────────────────────────────────
BLEComms     ble;
IMUReader    imu;
HapticDriver haptic;

// ── IMU callback — fires on every new quaternion ──────────────────────────────
// Converts to Euler angles here on the MCU so the laptop gets ready-to-use
// values, but also keeps the raw quaternion available if needed later.
void onIMUData(float w, float x, float y, float z) {
    if (!ble.connected()) return;

    // Quaternion → Euler (radians → degrees)
    // Roll  (X), Pitch (Y), Yaw (Z)
    float roll  = atan2f(2.0f*(w*x + y*z), 1.0f - 2.0f*(x*x + y*y)) * 57.2958f;
    float pitch = asinf (2.0f*(w*y - z*x))                            * 57.2958f;
    float yaw   = atan2f(2.0f*(w*z + x*y), 1.0f - 2.0f*(y*y + z*z)) * 57.2958f;

    char buf[48];
    snprintf(buf, sizeof(buf), "%.2f,%.2f,%.2f\n", roll, pitch, yaw);
    ble.send(buf);
}

// ── BLE receive callback — 0x01 triggers haptic ───────────────────────────────
void onBLEReceive(const uint8_t* data, size_t len) {
    for (size_t i = 0; i < len; i++) {
        if (data[i] == 0x01) {
            haptic.trigger();
            Serial.println("[HAP] Triggered via BLE.");
        }
        else if (data[i] == 0x53) {          // 'S' = sync request
            char buf[32];
            snprintf(buf, sizeof(buf), "SYNC:%lu\n", millis());
            ble.send(buf);
            Serial.println("[BLE] Sync reply sent.");
        }
    }
}

// ── setup() ──────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);

    pinMode(LED_RED,   OUTPUT); digitalWrite(LED_RED,   HIGH);
    pinMode(LED_GREEN, OUTPUT); digitalWrite(LED_GREEN, HIGH);
    pinMode(LED_BLUE,  OUTPUT); digitalWrite(LED_BLUE,  HIGH);

    Serial.println("=== XIAO nRF52840 — Full Integration ===");

    // IMU
    imu.setRate(IMU_RATE_HZ);
    imu.setDataCallback(onIMUData);
    if (!imu.begin()) {
        Serial.println("FATAL: IMU init failed.");
        while (1) { digitalWrite(LED_RED, LOW); delay(100);
                    digitalWrite(LED_RED, HIGH); delay(100); }
    }

    // Haptic — Wire already up from IMU init
    if (!haptic.begin()) {
        Serial.println("FATAL: Haptic init failed.");
        while (1) { digitalWrite(LED_RED, LOW); delay(200);
                    digitalWrite(LED_RED, HIGH); delay(200); }
    }

    // BLE
    ble.setReceiveCallback(onBLEReceive);
    
    // ble.begin("IMU_WRIST");
    ble.begin("IMU_ARM");
    // ble.begin("IMU_CHEST");

    digitalWrite(LED_GREEN, LOW);   // green ON = all systems ready
    Serial.print("[SYS] Running. IMU @ ");
    Serial.print(IMU_RATE_HZ);
    Serial.println(" Hz. Waiting for BLE connection...");
}

// ── loop() ───────────────────────────────────────────────────────────────────
void loop() {
    ble.update();   // drain RX, fire onBLEReceive if bytes waiting
    imu.update();   // read sensor, fire onIMUData if new sample ready
    // No delay — both are non-blocking, sensor rate is gated by report interval
}