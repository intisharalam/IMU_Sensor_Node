#include "IMUReader.h"
#include <Arduino.h>

// -- Constructor --
IMUReader::IMUReader(): _bno(-1) , _dataCb(nullptr), _w(1.0f), _x(0.0f), _y(0.0f), _z(0.0f), _ready(false), _newData(false), _intervalUs(10000)
{}
// -1 = no hardware reset pin
// default 100 Hz - 10,000us interval

// -- setRate() --
void IMUReader::setRate(uint8_t hz) {
    // Clamp to a sensible range for GAME_ROTATION_VECTOR over I2C
    if (hz < 10)  hz = 10;
    if (hz > 250) hz = 250;
    _intervalUs = 1000000UL / hz; // interval = 1s/Hz (f=1/T => T = 1/f)
}

// -- begin() --
bool IMUReader::begin() {
    Wire.begin();
    Wire.setClock(400000);  // 400 kHz fast mode — keeps I2C from limiting 100 Hz

    if (!_bno.begin_I2C()) {
        Serial.println("[IMU] ERROR: BNO085 not found. Check D4/D5 wiring.");
        return false;
    }
    Serial.println("[IMU] BNO085 found.");

    if (!_enableReports()) return false;

    _ready = true;
    Serial.print("[IMU] Running at ");
    Serial.print(1000000UL / _intervalUs);
    Serial.println(" Hz (GAME_ROTATION_VECTOR, no magnetometer).");
    return true;
}

// -- update() - call every loop() --
bool IMUReader::update() {
    if (!_ready) return false;

    // Re-enable reports after any sensor reset (power glitch, I2C dropout)
    if (_bno.wasReset()) {
        Serial.println("[IMU] Sensor reset detected — re-enabling reports.");
        _enableReports();
    }

    if (!_bno.getSensorEvent(&_sensorValue)) return false;
    if (_sensorValue.sensorId != SH2_GAME_ROTATION_VECTOR) return false;

    _w = _sensorValue.un.gameRotationVector.real;
    _x = _sensorValue.un.gameRotationVector.i;
    _y = _sensorValue.un.gameRotationVector.j;
    _z = _sensorValue.un.gameRotationVector.k;

    _newData = true;

    if (_dataCb) {
        _dataCb(_w, _x, _y, _z);
    }

    return true;
}

// -- setDataCallback() --
void IMUReader::setDataCallback(IMUDataCallback cb) {
    _dataCb = cb;
}

// -- Getters --
bool  IMUReader::isReady()   const { return _ready; }
float IMUReader::getW()      const { return _w; }
float IMUReader::getX()      const { return _x; }
float IMUReader::getY()      const { return _y; }
float IMUReader::getZ()      const { return _z; }

bool IMUReader::hasNewData() {
    if (_newData) { _newData = false; return true; }
    return false;
}

// -- _enableReports() --
bool IMUReader::_enableReports() {
    if (!_bno.enableReport(SH2_GAME_ROTATION_VECTOR, _intervalUs)) {
        Serial.println("[IMU] ERROR: Could not enable GAME_ROTATION_VECTOR.");
        return false;
    }
    return true;
}