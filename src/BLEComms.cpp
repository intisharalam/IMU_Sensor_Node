#include "BLEComms.h"
#include <Arduino.h>

BLEComms* BLEComms::_instance = nullptr;

BLEComms::BLEComms()
    : _rxCb(nullptr)
    , _lastRxByte(0)
    , _newRxFlag(false)
{
    _instance = this;
}

void BLEComms::begin(const char* name) {
    Bluefruit.begin(1, 0);
    Bluefruit.setTxPower(4);
    Bluefruit.setName(name);

    Bluefruit.Periph.setConnectCallback(_onConnect);
    Bluefruit.Periph.setDisconnectCallback(_onDisconnect);

    _bledis.setManufacturer("Seeed Studio");
    _bledis.setModel("XIAO nRF52840");
    _bledis.begin();

    _bleuart.begin();
    _startAdvertising();

    Serial.print("[BLE] Advertising as '");
    Serial.print(name);
    Serial.println("'");
}

void BLEComms::update() {
    if (!_bleuart.available()) return;

    uint8_t buf[64];
    size_t  len = 0;

    while (_bleuart.available() && len < sizeof(buf)) {
        buf[len++] = (uint8_t) _bleuart.read();
    }

    if (len == 0) return;

    _lastRxByte = buf[len - 1];
    _newRxFlag  = true;

    if (_rxCb) {
        _rxCb(buf, len);
    }
}

bool BLEComms::connected() const {
    return Bluefruit.connected();
}

bool BLEComms::send(const char* str) {
    if (!connected()) return false;
    return _bleuart.print(str) > 0;
}

bool BLEComms::send(const uint8_t* buf, size_t len) {
    if (!connected()) return false;
    return _bleuart.write(buf, len) == len;
}

void BLEComms::setReceiveCallback(BLEReceiveCallback cb) {
    _rxCb = cb;
}

uint8_t BLEComms::getLastRx() const {
    return _lastRxByte;
}

bool BLEComms::hasNewRx() {
    if (_newRxFlag) {
        _newRxFlag = false;
        return true;
    }
    return false;
}

void BLEComms::_startAdvertising() {
    Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
    Bluefruit.Advertising.addTxPower();
    Bluefruit.Advertising.addService(_bleuart);
    Bluefruit.ScanResponse.addName();

    Bluefruit.Advertising.restartOnDisconnect(true);
    Bluefruit.Advertising.setInterval(32, 244);
    Bluefruit.Advertising.setFastTimeout(30);
    Bluefruit.Advertising.start(0);
}

void BLEComms::_onConnect(uint16_t conn_handle) {
    if (!_instance) return;
    BLEConnection* conn = Bluefruit.Connection(conn_handle);
    
    conn->requestMtuExchange(247);
    
    char peer[32] = {0};
    conn->getPeerName(peer, sizeof(peer));
    Serial.print("[BLE] Connected: ");
    Serial.println(peer);
    digitalWrite(LED_BLUE, LOW);    // active-LOW: ON = connected
}

void BLEComms::_onDisconnect(uint16_t conn_handle, uint8_t reason) {
    (void) conn_handle;
    if (!_instance) return;
    Serial.print("[BLE] Disconnected, reason=0x");
    Serial.println(reason, HEX);
    digitalWrite(LED_BLUE, HIGH);
}