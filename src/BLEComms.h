#pragma once
/*
 * BLEComms.h
 *
 * Design:
 *  RX  — callback-based. Register handler with setReceiveCallback() before begin().
 *         hasNewRx() / getLastRx() also available for simple single-byte polling.
 *  TX  — caller owns buffer. ble.send(const char*) or ble.send(buf, len).
 *  Instance — single global in main.cpp, passed as BLEComms* to other classes.
 */

#include <bluefruit.h>

using BLEReceiveCallback = void (*)(const uint8_t* data, size_t len);

class BLEComms {
public:
    BLEComms();

    // Call before anything else. Inits stack and starts advertising.
    void begin(const char* name);

    // Must be called every loop(). Drains RX FIFO, fires callbacks.
    void update();

    bool connected() const;

    // TX — returns false if not connected
    bool send(const char* str);
    bool send(const uint8_t* buf, size_t len);

    // RX — register before begin()
    void    setReceiveCallback(BLEReceiveCallback cb);
    uint8_t getLastRx() const;
    bool    hasNewRx();          // one-shot, clears on read

    // --- Charging mode interface (ChargingMode use only) ---
    void stopBLE();     // gracefully disconnect peer and stop advertising
    void resumeBLE();   // restart advertising; stack stays initialised

private:
    BLEDis  _bledis;
    BLEUart _bleuart;

    BLEReceiveCallback _rxCb;
    uint8_t _lastRxByte;
    bool    _newRxFlag;

    void _startAdvertising();

    // Bluefruit needs static C-style callbacks.
    // _instance lets them reach back into the live object.
    static BLEComms* _instance;
    static void _onConnect(uint16_t conn_handle);
    static void _onDisconnect(uint16_t conn_handle, uint8_t reason);
};