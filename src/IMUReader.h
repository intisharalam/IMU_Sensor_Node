#pragma once
/*
 * IMUReader.h
 *
 * Wraps the Adafruit BNO085 for clean quaternion reads at a fixed rate.
 *
 * Report: SH2_GAME_ROTATION_VECTOR
 *   - Fused from accelerometer + gyro only.
 *   - Magnetometer excluded — no heading jumps, no compass dependency.
 *   - Good for relative motion tracking at 50–100 Hz.
 *
 * Public API
 * ----------
 *   bool begin()              Init sensor on Wire (D4=SDA, D5=SCL). Returns false on failure.
 *   void update()             Call every loop(). Drains sensor FIFO, fires callback if new data.
 *   void setRate(uint8_t hz)  Set report rate before begin(). Default: 100 Hz.
 *   void setDataCallback(void (*cb)(float w, float x, float y, float z))
 *   bool isReady()            True after begin() succeeds.
 *
 *   // Polling alternative to callback:
 *   bool    hasNewData()      One-shot flag, clears on read.
 *   float   getW() / getX() / getY() / getZ()
 */

#include <Wire.h>
#include <Adafruit_BNO08x.h>

// Defining the shape of a callback function. This class will send any
// new data to a function of this shape set as callback function.
using IMUDataCallback = void (*)(float w, float x, float y, float z);

class IMUReader {
public:
    IMUReader();

    // Set report rate in Hz (call before begin). Clamped to 10–250 Hz.
    void setRate(uint8_t hz);

    // Initialise I2C and sensor. Returns true on success.
    bool begin();

    // Call every loop(). Returns true if a new quaternion was received this call.
    bool update();

    // Register a callback: fired from update() on every new quaternion.
    void setDataCallback(IMUDataCallback cb);

    bool  isReady()   const;
    bool  hasNewData();       // one-shot, clears on read

    float getW() const;
    float getX() const;
    float getY() const;
    float getZ() const;

private:
    Adafruit_BNO08x   _bno;
    // stores our game rotation vector values. Refer to BNO085 datasheet.
    sh2_SensorValue_t _sensorValue; 

    IMUDataCallback _dataCb;

    float   _w, _x, _y, _z;
    bool    _ready;
    bool    _newData;
    uint32_t _intervalUs;   // report interval in microseconds

    // Called once at boot and again after any sensor reset.
    bool _enableReports();
};

// Waffle added here:
/*
 * sh2_SensorValue_t — Adafruit BNO08x sensor report container
 *
 * The BNO085 supports many report types simultaneously (rotation vectors,
 * accelerometer, gyroscope, step counter, etc.). Rather than having a separate
 * struct for each, the Adafruit library uses a single sh2_SensorValue_t which
 * holds any one report at a time.
 *
 * Key fields:
 *   .sensorId          — identifies which report type this packet contains
 *                        (e.g. SH2_GAME_ROTATION_VECTOR, SH2_ACCELEROMETER)
 *
 *   .un                — a union of all possible report structs. You must
 *                        check .sensorId first, then access the correct member:
 *
 *                        .un.gameRotationVector.real  → quaternion w
 *                        .un.gameRotationVector.i     → quaternion x
 *                        .un.gameRotationVector.j     → quaternion y
 *                        .un.gameRotationVector.k     → quaternion z
 *
 * Accessing the wrong union member (e.g. reading .accelerometer when the
 * packet is actually a rotation vector) gives garbage data silently —
 * always validate .sensorId before reading .un. (Definitely didnt make this mistake)
 */