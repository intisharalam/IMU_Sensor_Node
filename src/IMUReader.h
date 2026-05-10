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
 * ──────────
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
    sh2_SensorValue_t _sensorValue;

    IMUDataCallback _dataCb;

    float   _w, _x, _y, _z;
    bool    _ready;
    bool    _newData;
    uint32_t _intervalUs;   // report interval in microseconds

    // Called once at boot and again after any sensor reset.
    bool _enableReports();
};