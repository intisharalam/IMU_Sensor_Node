#pragma once
#include <Arduino.h>
#include "BLEComms.h"

/*
 * ChargingMode.h
 *
 * Detects USB VBUS presence via nRF52840 power register.
 * On USB connect  → stops BLE, silences IMU loop, shows solid red LED.
 * On USB disconnect → resumes BLE advertising, green LED, normal loop.
 *
 * Call update() every loop(). Gate imu.update() / ble.update() behind isCharging().
 */

class ChargingMode {
public:
    explicit ChargingMode(BLEComms& ble);

    // Call every loop(). Polls VBUS and drives state transitions.
    void update();
    bool isCharging() const;
    void initHardware();

private:
    BLEComms& _ble;
    bool      _charging;
    bool      _lastVbus;
    uint32_t  _debounceStart;

    static constexpr uint32_t DEBOUNCE_MS = 100;

    // Charging current setting pin for adafruit-variant core mapping
    #if defined(PIN_HICHG)
      static constexpr uint8_t CHG_SPEED_PIN = PIN_HICHG;
    #else
      static constexpr uint8_t CHG_SPEED_PIN = 22; 
    #endif

    static bool _vbusPresent();
    // void _initHardware();
    void _enterCharging();
    void _exitCharging();
};
