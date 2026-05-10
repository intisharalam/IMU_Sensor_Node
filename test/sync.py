"""
imu_test.py
───────────
Simple console test for 3 IMUs over BLE.

Connects to IMU_WRIST, IMU_ARM, IMU_CHEST concurrently.
For each connected IMU you can:
  H  — send haptic trigger  (0x01)
  S  — send sync request    (0x53)  →  expects back  SYNC:<millis>

Usage:
  pip install bleak
  python imu_test.py

Commands (type in console, press Enter):
  h wrist      — haptic on wrist
  h arm        — haptic on arm
  h chest      — haptic on chest
  h all        — haptic on all connected
  s wrist      — sync request to wrist
  s arm        — sync request to arm
  s chest      — sync request to chest
  s all        — sync all connected
  status       — print connection status of all 3
  quit         — disconnect all and exit
"""

import asyncio
import threading
import time
import sys

from bleak import BleakClient, BleakScanner

# ── NUS UUIDs (Nordic UART Service — same on all boards) ──────────────────────
UART_TX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # board → laptop
UART_RX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # laptop → board

# ── Device names (must match what you flashed) ────────────────────────────────
DEVICE_NAMES = {
    "wrist": "IMU_WRIST",
    "arm":   "IMU_ARM",
    "chest": "IMU_CHEST",
}

# ── Protocol bytes ────────────────────────────────────────────────────────────
HAPTIC_ON  = bytes([0x01])   # trigger haptic
SYNC_REQ   = bytes([0x53])   # ASCII 'S' — request SYNC:<millis> reply

SCAN_TIMEOUT    = 15.0   # seconds to scan for each device
RECONNECT_WAIT  = 5.0    # seconds before retrying after disconnect
PRINT_THRESHOLD = 0.2    # degrees — only print if any axis changes by at least this

# ── Shared state ──────────────────────────────────────────────────────────────
# Written by BLE tasks, read by console thread.
_lock = threading.Lock()

_state = {
    key: {
        "client":      None,    # BleakClient when connected
        "connected":   False,
        "address":     None,
        "rx_buf":      "",      # partial-packet buffer
        "packet_count": 0,
        "last_sync_offset_ms": None,   # most recent computed offset
        "last_printed": None,   # (roll, pitch, yaw) of last printed packet
    }
    for key in DEVICE_NAMES
}

# asyncio event loop running in background thread
_loop: asyncio.AbstractEventLoop = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ts() -> str:
    return time.strftime("%H:%M:%S")


def _set(key: str, field: str, value):
    with _lock:
        _state[key][field] = value


def _get(key: str, field: str):
    with _lock:
        return _state[key][field]


# ── RX handler (called by bleak in BLE thread) ────────────────────────────────

def _make_rx_handler(key: str):
    """Returns a notification callback bound to a specific IMU slot."""
    def handler(_, data: bytearray):
        text = data.decode("utf-8", errors="replace")
        with _lock:
            _state[key]["rx_buf"] += text
            buf = _state[key]["rx_buf"]

        # Process all complete lines
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            line = line.strip()
            if not line:
                continue

            with _lock:
                _state[key]["rx_buf"] = buf
                _state[key]["packet_count"] += 1
                count = _state[key]["packet_count"]

            if line.startswith("SYNC:"):
                # Compute offset against laptop monotonic clock
                recv_time = time.monotonic()
                try:
                    board_ms = int(line.split("SYNC:")[1])
                    # Rough offset (no RTT correction at this stage)
                    offset_ms = (recv_time * 1000) - board_ms
                    with _lock:
                        _state[key]["last_sync_offset_ms"] = offset_ms
                    print(f"\n[{_ts()}] [{key.upper()}] SYNC reply: "
                          f"board={board_ms} ms  |  "
                          f"offset={offset_ms:+.1f} ms")
                except ValueError:
                    print(f"\n[{_ts()}] [{key.upper()}] Malformed SYNC: '{line}'")
            else:
                # Regular IMU data packet (roll,pitch,yaw)
                # Only print if at least one axis changed by >= PRINT_THRESHOLD
                try:
                    vals = tuple(float(v) for v in line.split(","))
                    if len(vals) != 3:
                        raise ValueError
                except ValueError:
                    print(f"[{_ts()}] [{key.upper()}] Unexpected: '{line}'")
                    continue

                with _lock:
                    prev = _state[key]["last_printed"]
                    changed = (
                        prev is None or
                        any(abs(vals[i] - prev[i]) >= PRINT_THRESHOLD for i in range(3))
                    )
                    if changed:
                        _state[key]["last_printed"] = vals

                if changed:
                    print(f"[{_ts()}] [{key.upper()}] #{count:>5}  "
                          f"R={vals[0]:+7.2f}  P={vals[1]:+7.2f}  Y={vals[2]:+7.2f}")

    return handler


# ── BLE task for one IMU ──────────────────────────────────────────────────────

async def _imu_task(key: str, name: str):
    """Persistent task: scan → connect → stream. Retries on disconnect."""
    while True:
        # ── Scan ──────────────────────────────────────────────────────────────
        print(f"[{_ts()}] [{key.upper()}] Scanning for '{name}'...")
        try:
            device = await BleakScanner.find_device_by_name(name, timeout=SCAN_TIMEOUT)
        except Exception as e:
            print(f"[{_ts()}] [{key.upper()}] Scan error: {e}")
            await asyncio.sleep(RECONNECT_WAIT)
            continue

        if device is None:
            print(f"[{_ts()}] [{key.upper()}] '{name}' not found. Retrying...")
            await asyncio.sleep(RECONNECT_WAIT)
            continue

        print(f"[{_ts()}] [{key.upper()}] Found {name} [{device.address}]. Connecting...")
        _set(key, "address", device.address)

        # ── Connect ───────────────────────────────────────────────────────────
        try:
            async with BleakClient(device, timeout=10.0) as client:
                _set(key, "client",    client)
                _set(key, "connected", True)
                print(f"[{_ts()}] [{key.upper()}] Connected! MTU={client.mtu_size}B")

                await client.start_notify(UART_TX_UUID, _make_rx_handler(key))

                # Keep alive — exit inner loop when client disconnects
                while client.is_connected:
                    await asyncio.sleep(0.5)

        except Exception as e:
            print(f"[{_ts()}] [{key.upper()}] Connection error: {e}")
        finally:
            _set(key, "client",    None)
            _set(key, "connected", False)
            print(f"[{_ts()}] [{key.upper()}] Disconnected. Retrying in {RECONNECT_WAIT}s...")
            await asyncio.sleep(RECONNECT_WAIT)


# ── Send helpers (called from console thread via run_coroutine_threadsafe) ─────

async def _send(key: str, payload: bytes, label: str):
    client = _get(key, "client")
    if client is None or not _get(key, "connected"):
        print(f"  [{key.upper()}] Not connected — skipping.")
        return
    try:
        await client.write_gatt_char(UART_RX_UUID, payload, response=False)
        print(f"[{_ts()}] [{key.upper()}] Sent {label}")
    except Exception as e:
        print(f"[{_ts()}] [{key.upper()}] Send failed: {e}")


def _send_to(key: str, payload: bytes, label: str):
    """Thread-safe fire-and-forget send from console thread."""
    asyncio.run_coroutine_threadsafe(_send(key, payload, label), _loop)


def _send_all(payload: bytes, label: str):
    for key in DEVICE_NAMES:
        _send_to(key, payload, label)


# ── Console command loop ──────────────────────────────────────────────────────

def _console_loop():
    print("\nCommands: h/s <wrist|arm|chest|all>  |  status  |  quit\n")
    while True:
        try:
            raw = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            raw = "quit"

        if not raw:
            continue

        parts = raw.split()

        # ── quit ──────────────────────────────────────────────────────────────
        if parts[0] == "quit":
            print("Shutting down...")
            _loop.call_soon_threadsafe(_loop.stop)
            break

        # ── status ────────────────────────────────────────────────────────────
        elif parts[0] == "status":
            print(f"\n{'IMU':<10} {'Connected':<12} {'Address':<20} {'Packets':<10} {'Last sync offset'}")
            print("─" * 70)
            with _lock:
                for key in DEVICE_NAMES:
                    s = _state[key]
                    conn    = "YES" if s["connected"] else "NO"
                    addr    = s["address"] or "—"
                    packets = s["packet_count"]
                    offset  = f"{s['last_sync_offset_ms']:+.1f} ms" if s["last_sync_offset_ms"] is not None else "—"
                    print(f"{key:<10} {conn:<12} {addr:<20} {packets:<10} {offset}")
            print()

        # ── h / s commands ────────────────────────────────────────────────────
        elif parts[0] in ("h", "s") and len(parts) == 2:
            cmd, target = parts
            payload = HAPTIC_ON if cmd == "h" else SYNC_REQ
            label   = "HAPTIC (0x01)" if cmd == "h" else "SYNC (0x53)"

            if target == "all":
                _send_all(payload, label)
            elif target in DEVICE_NAMES:
                _send_to(target, payload, label)
            else:
                print(f"  Unknown target '{target}'. Use: wrist / arm / chest / all")

        else:
            print("  Unknown command. Try: h wrist | s all | status | quit")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    global _loop

    _loop = asyncio.new_event_loop()

    # Start BLE tasks
    for key, name in DEVICE_NAMES.items():
        _loop.create_task(_imu_task(key, name))

    # Run event loop in background thread
    ble_thread = threading.Thread(target=_loop.run_forever, daemon=True)
    ble_thread.start()

    print("=" * 55)
    print("  IMU BLE Test — 3x XIAO nRF52840")
    print("  Connecting to: IMU_WRIST, IMU_ARM, IMU_CHEST")
    print("=" * 55)

    # Console runs on main thread (blocking)
    _console_loop()

    ble_thread.join(timeout=3.0)
    print("Done.")


if __name__ == "__main__":
    main()