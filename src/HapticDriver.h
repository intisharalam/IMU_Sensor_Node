#pragma once
/*
 * HapticDriver.h
 *
 * Wraps the Adafruit DRV2605L for clean single-call haptic triggering.
 *
 * Motor  : ERM (coin vibration motor)
 * Effect : #15 — 750ms Alert 100% (fixed, chosen from test)
 *
 * Public API
 * ----------
 *   bool begin()     Init I2C and driver. Returns false on failure.
 *   void trigger()   Fire the 750ms alert once. Non-blocking — returns
 *                    immediately; the DRV2605L handles timing internally.
 *   bool isReady()   True after begin() succeeds.
 */

#include <Wire.h>
#include <Adafruit_DRV2605.h>

class HapticDriver {
public:
    HapticDriver();

    void setEffectID(uint8_t id);
    uint8_t getEffectID() const;

    // Initialise I2C and DRV2605L. Returns true on success.
    // Wire.begin() + Wire.setClock() should already have been called
    // by IMUReader::begin() since they share the bus — this is safe
    // to call regardless, Wire.begin() on nRF52 is idempotent.
    bool begin();

    // Fire effect #15 (750ms Alert 100%) once.
    // Non-blocking — DRV2605L sequences internally.
    void trigger();

    bool isReady() const;

    static constexpr uint8_t EFFECT_DEFAULT = 15;  // 750ms Alert 100%

private:
    Adafruit_DRV2605 _drv;
    bool             _ready;

    uint8_t _effectID = 15;  // default 750ms Alert 100%
};