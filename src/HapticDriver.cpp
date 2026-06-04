#include "HapticDriver.h"
#include <Arduino.h>

HapticDriver::HapticDriver()
    : _ready(false)
{}

bool HapticDriver::begin() {
    // Wire already started by IMUReader — safe to call again, no-op on nRF52
    Wire.begin();
    Wire.setClock(400000);

    if (!_drv.begin()) {
        Serial.println("[HAP] ERROR: DRV2605L not found. Check D4/D5 wiring.");
        return false;
    }

    _drv.useERM();
    _drv.selectLibrary(1);                  // ERM library 1 (TS2200 set A)
    _drv.setMode(DRV2605_MODE_INTTRIG);     // fire on go() call

    // Pre-load the waveform once — no need to reload on every trigger()
    _drv.setWaveform(0, _effectID );         // slot 0: effect #15
    _drv.setWaveform(1, 0);                 // slot 1: end of sequence

    _ready = true;
    Serial.print("[HAP] DRV2605L ready. Default effect: #");
    Serial.println(_effectID);
    return true;
}

void HapticDriver::trigger() {
    _drv.setWaveform(0, _effectID);
    _drv.setWaveform(1, 0);  // end-of-sequence terminator
    _drv.go();
}

bool HapticDriver::isReady() const {
    return _ready;
}

void HapticDriver::setEffectID(uint8_t id) {
    _effectID = id;
}

uint8_t HapticDriver::getEffectID() const {
    return _effectID;
}