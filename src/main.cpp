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
#include "ChargingMode.h"

// -- Customisable rate --
static const uint8_t IMU_RATE_HZ = 50;   // ← change this freely

// -- Instances --
BLEComms     ble;
IMUReader    imu;
HapticDriver haptic;
ChargingMode charger(ble);

// -- IMU callback - fires on every new quaternion --
// Converts to Euler angles here on the MCU so the laptop gets ready-to-use
// values, but also keeps the raw quaternion available if needed later.
void onIMUData(float w, float x, float y, float z) {
    if (!ble.connected()) return;

    // instead of float, we send data as 4 raw bytes. Solved 23B limit
    // memcpy copies memory directly
    uint8_t buf[16];
    memcpy(buf,      &w, 4);
    memcpy(buf + 4,  &x, 4);
    memcpy(buf + 8,  &y, 4);
    memcpy(buf + 12, &z, 4);
    ble.send(buf, 16);
}

// -- BLE receive callback --
// 'H' (0x48) = haptic trigger + effect ID byte, 'S' (0x53) = sync request
void onBLEReceive(const uint8_t* data, size_t len) {
    for (size_t i = 0; i < len; i++) {
        if (data[i] == 0x48 && i + 1 < len) {  // 'H' + effect ID
            haptic.setEffectID(data[i + 1]);
            haptic.trigger();
            Serial.print("[HAP] Triggered via BLE. Effect: #");
            Serial.println(data[i + 1]);
            i++;  // consume the effect byte
        }
        else if (data[i] == 0x53) {             // 'S' = sync request
            char buf[32];
            snprintf(buf, sizeof(buf), "SYNC:%lu\r\n", millis());
            ble.send(buf);
            Serial.println("[BLE] Sync reply sent.");
        }
    }
}

// -- setup() --
void setup() {
    Serial.begin(115200);
    charger.initHardware();

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
    
    ble.begin("IMU_WRIST");
    //ble.begin("IMU_ARM");
    //ble.begin("IMU_CHEST");

    Serial.print("[CHG] HICHG pin state: ");
    Serial.println(digitalRead(22));   // must print 0

    digitalWrite(LED_GREEN, LOW);   // green ON = all systems ready
    Serial.print("[SYS] Running. IMU @ ");
    Serial.print(IMU_RATE_HZ);
    Serial.println(" Hz. Waiting for BLE connection...");
}

// -- loop() --
void loop() {
    charger.update();
    if (charger.isCharging()) return;

    ble.update();   // drain RX, fire onBLEReceive if bytes waiting
    imu.update();   // read sensor, fire onIMUData if new sample ready
    // No delay — both are non-blocking, sensor rate is gated by report interval
}