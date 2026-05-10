"""
laptop.py  —  Full integration host
=====================================
Connects to XIAO_IMU via BLE UART (NUS).

RX : Receives "roll,pitch,yaw\n" from board, prints with timestamp.
TX : Type 'h' + Enter at any time to send 0x01 and trigger haptic.
     Type 'q' + Enter to quit cleanly.
"""

import asyncio
import sys
import threading
import time
from bleak import BleakClient, BleakScanner

UART_TX_CHAR = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # board → laptop
UART_RX_CHAR = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # laptop → board
DEVICE_NAME  = "XIAO_IMU"

# ── Shared state ──────────────────────────────────────────────────────────────
_client:      BleakClient | None = None
_client_lock  = threading.Lock()
_stop_event   = threading.Event()
_partial      = ""
_packet_count = 0

# ── BLE receive handler ───────────────────────────────────────────────────────
def handle_rx(characteristic, data: bytearray):
    global _partial, _packet_count
    _partial += data.decode("utf-8", errors="replace")
    while "\n" in _partial:
        line, _partial = _partial.split("\n", 1)
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) != 3:
            continue
        try:
            roll  = float(parts[0])
            pitch = float(parts[1])
            yaw   = float(parts[2])
        except ValueError:
            continue
        _packet_count += 1
        ts = time.strftime("%H:%M:%S")
        print(
            f"\r[{ts}] #{_packet_count:>6} | "
            f"Roll: {roll:>8.2f}°  "
            f"Pitch: {pitch:>8.2f}°  "
            f"Yaw: {yaw:>8.2f}°",
            end="",
            flush=True
        )

# ── Haptic send ───────────────────────────────────────────────────────────────
async def send_haptic():
    with _client_lock:
        c = _client
    if c is None or not c.is_connected:
        print("\n[TX] Not connected — haptic not sent.")
        return
    await c.write_gatt_char(UART_RX_CHAR, bytes([0x01]), response=False)
    print("\n[TX] Haptic triggered.")

# ── BLE connection loop ───────────────────────────────────────────────────────
async def ble_loop():
    global _client
    while not _stop_event.is_set():
        print(f"\nScanning for '{DEVICE_NAME}'...")
        device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=15.0)
        if device is None:
            print("  Not found, retrying...")
            continue

        print(f"  Found: {device.name} [{device.address}]")
        try:
            async with BleakClient(device) as client:
                with _client_lock:
                    _client = client
                print(f"  Connected. MTU={client.mtu_size}  |  "
                      f"Type 'h' + Enter to trigger haptic, 'q' to quit.\n")
                await client.start_notify(UART_TX_CHAR, handle_rx)
                while client.is_connected and not _stop_event.is_set():
                    await asyncio.sleep(0.05)
        except Exception as e:
            print(f"\n  BLE error: {e}")
        finally:
            with _client_lock:
                _client = None

        if not _stop_event.is_set():
            print("\n  Disconnected. Retrying in 3 s...")
            await asyncio.sleep(3.0)

# ── Input loop (runs in its own thread) ───────────────────────────────────────
def input_loop(loop: asyncio.AbstractEventLoop):
    """Blocking readline in a background thread; schedules coroutines on the BLE loop."""
    while not _stop_event.is_set():
        try:
            cmd = input()          # blocks until Enter
        except EOFError:
            break
        cmd = cmd.strip().lower()
        if cmd == "h":
            asyncio.run_coroutine_threadsafe(send_haptic(), loop)
        elif cmd == "q":
            print("Quitting...")
            _stop_event.set()
            break
        elif cmd:
            print("  Commands: 'h' = haptic, 'q' = quit")

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    t = threading.Thread(target=input_loop, args=(loop,), daemon=True)
    t.start()

    try:
        loop.run_until_complete(ble_loop())
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        _stop_event.set()
        loop.close()