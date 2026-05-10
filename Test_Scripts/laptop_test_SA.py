"""
laptop_test.py  —  Step 1 BLE Comms Test (host side)
=====================================================
Connects to the XIAO nRF52840 advertising as "XIAO_TEST" via BLE UART (NUS).

What it does
------------
  RX  : Receives "COUNT:<n>\\n" packets and prints them with a timestamp.
  TX  : Every BLINK_INTERVAL seconds sends 0x01 (LED on/blink) to the board,
        then 2 seconds later sends 0x00 (LED off).
        This gives you a clear visual confirmation that the TX path works.

Usage
-----
  pip install bleak
  python laptop_test.py

Press Ctrl-C to exit cleanly.
"""

import asyncio
import time
from bleak import BleakClient, BleakScanner

# ── NUS UUIDs (standard Nordic UART Service) ──────────────────────────────────
UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # board → laptop
UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # laptop → board

DEVICE_NAME     = "XIAO_TEST"
BLINK_INTERVAL  = 5.0   # send a blink command every N seconds
RECONNECT_DELAY = 3.0   # seconds to wait before retrying after disconnect

# ── Receive buffer (handles partial BLE packets) ──────────────────────────────
_partial = ""
_packet_count = 0

def handle_rx(characteristic, data: bytearray):
    """Called by bleak on every notification from the board."""
    global _partial, _packet_count
    _partial += data.decode("utf-8", errors="replace")
    while "\n" in _partial:
        line, _partial = _partial.split("\n", 1)
        line = line.strip()
        if not line:
            continue
        _packet_count += 1
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] RX #{_packet_count:>5}  →  {line}")

# ── Main BLE loop ─────────────────────────────────────────────────────────────
async def run():
    while True:
        # ── Scan ──────────────────────────────────────────────────────────────
        print(f"\nScanning for '{DEVICE_NAME}'...")
        device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=15.0)
        if device is None:
            print("  Not found, retrying in 3 s...")
            await asyncio.sleep(RECONNECT_DELAY)
            continue

        print(f"  Found: {device.name}  [{device.address}]")
        print("  Connecting...")

        try:
            async with BleakClient(device) as client:
                print(f"  Connected!  MTU = {client.mtu_size} bytes")
                print("─" * 55)
                print("  Receiving counter packets from board.")
                print(f"  Will send blink command every {BLINK_INTERVAL:.0f} s.")
                print("  Press Ctrl-C to quit.")
                print("─" * 55)

                # Subscribe to TX notifications (board → laptop)
                await client.start_notify(UART_TX_CHAR_UUID, handle_rx)

                last_blink = time.monotonic()

                while client.is_connected:
                    await asyncio.sleep(0.1)

                    now = time.monotonic()
                    if now - last_blink >= BLINK_INTERVAL:
                        last_blink = now

                        # ── Send 0x01: LED ON / blink ─────────────────────────
                        print("\n  [TX] → 0x01  (blink command)")
                        await client.write_gatt_char(
                            UART_RX_CHAR_UUID,
                            bytes([0x01]),
                            response=False   # Write Without Response — matches bleuart
                        )

                        # Wait 2 s then send 0x00: LED OFF
                        await asyncio.sleep(2.0)
                        print("  [TX] → 0x00  (LED off command)")
                        await client.write_gatt_char(
                            UART_RX_CHAR_UUID,
                            bytes([0x00]),
                            response=False
                        )

        except Exception as exc:
            print(f"\n  BLE error: {exc}")

        print(f"\n  Disconnected. Retrying in {RECONNECT_DELAY:.0f} s...")
        await asyncio.sleep(RECONNECT_DELAY)

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nExiting.")