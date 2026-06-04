#include "ChargingMode.h"

ChargingMode::ChargingMode(BLEComms& ble)
    : _ble(ble), _charging(false), _lastVbus(false), _debounceStart(0) {
    _initHardware(); // <-- Force set hardware configurations upon instantiation
}

void ChargingMode::_initHardware() {
    // Configure charge current selection pin
    pinMode(CHG_SPEED_PIN, OUTPUT);
    
    // LOW sets charge current limit to 100mA (Perfect for 250mAh cell)
    // HIGH sets charge current limit to 50mA
    digitalWrite(CHG_SPEED_PIN, LOW); 
}

void ChargingMode::update() {
    bool vbus = _vbusPresent();

    if (vbus != _lastVbus) {
        _lastVbus      = vbus;
        _debounceStart = millis();
        return;
    }

    if ((millis() - _debounceStart) < DEBOUNCE_MS) return;

    if (vbus  && !_charging) _enterCharging();
    if (!vbus &&  _charging) _exitCharging();
}

bool ChargingMode::isCharging() const { return _charging; }

bool ChargingMode::_vbusPresent() {
    return (NRF_POWER->USBREGSTATUS & POWER_USBREGSTATUS_VBUSDETECT_Msk) != 0;
}

void ChargingMode::_enterCharging() {
    _charging = true;
    _ble.stopBLE();

    // Solid red — active-LOW on扬XIAO nRF52840
    digitalWrite(LED_RED,   LOW);
    digitalWrite(LED_GREEN, HIGH);
    digitalWrite(LED_BLUE,  HIGH);

    Serial.println("[CHG] USB detected — Charging at 100mA Max. BLE Stopped.");
}

void ChargingMode::_exitCharging() {
    _charging = false;
    _ble.resumeBLE();

    digitalWrite(LED_RED,   HIGH);
    digitalWrite(LED_GREEN, LOW);   // green = normal ready state

    Serial.println("[CHG] USB removed — Resuming normal operation.");
}