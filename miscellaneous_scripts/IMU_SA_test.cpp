// /*
//  * main.cpp  —  Step 1b: IMU standalone test
//  * Board: Seeed Studio XIAO nRF52840 (non-Sense)
//  * Sensor: Adafruit BNO085, SDA=D4, SCL=D5
//  *
//  * Prints quaternion w,x,y,z to Serial at 100 Hz.
//  * No BLE. Pure sensor validation.
//  *
//  * Step 2 preview — combining with BLEComms will look like:
//  *     BLEComms  ble;
//  *     IMUReader imu;
//  *     void onIMUData(float w, float x, float y, float z) {
//  *         char buf[48];
//  *         snprintf(buf, sizeof(buf), "%.4f,%.4f,%.4f,%.4f\n", w, x, y, z);
//  *         ble.send(buf);
//  *     }
//  */

// #include <Arduino.h>
// #include "IMUReader.h"

// IMUReader imu;

// // ── IMU data callback ─────────────────────────────────────────────────────────
// void onIMUData(float w, float x, float y, float z) {
//     // 4 decimal places — plenty of precision over BLE later, light on Serial now
//     Serial.print(w, 4); Serial.print(',');
//     Serial.print(x, 4); Serial.print(',');
//     Serial.print(y, 4); Serial.print(',');
//     Serial.println(z, 4);
// }

// // ── setup() ──────────────────────────────────────────────────────────────────
// void setup() {
//     Serial.begin(115200);

//     Serial.println("=== IMU Standalone Test ===");

//     imu.setRate(100);                   // 100 Hz — change to 50 if I2C struggles
//     imu.setDataCallback(onIMUData);

//     if (!imu.begin()) {
//         Serial.println("FATAL: IMU init failed. Halting.");
//         while (1) delay(10);
//     }
// }

// // ── loop() ───────────────────────────────────────────────────────────────────
// void loop() {
//     imu.update();
//     // No delay() — update() is non-blocking, returns immediately if no new data.
//     // The sensor itself gates the rate via the report interval set in begin().
//     delay(30000);
// }