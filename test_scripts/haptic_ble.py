"""
haptic_test.py
--------------
Loops through all 123 named DRV2605L effects over BLE, one by one.
Press Enter to advance, 'q' to quit, or type a number to jump to it.

Usage:
    python haptic_test.py              # defaults to IMU_WRIST
    python haptic_test.py IMU_ARM
"""

import sys
import asyncio
from bleak import BleakClient, BleakScanner

UART_RX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
SCAN_TIMEOUT = 15.0
DEVICE_NAME  = sys.argv[1] if len(sys.argv) > 1 else "IMU_WRIST"

EFFECTS = {
    1:   "Strong Click 100%",
    2:   "Strong Click 60%",
    3:   "Strong Click 30%",
    4:   "Sharp Click 100%",
    5:   "Sharp Click 60%",
    6:   "Sharp Click 30%",
    7:   "Soft Bump 100%",
    8:   "Soft Bump 60%",
    9:   "Soft Bump 30%",
    10:  "Double Click 100%",
    11:  "Double Click 60%",
    12:  "Triple Click 100%",
    13:  "Soft Fuzz 60%",
    14:  "Strong Buzz 100%",
    15:  "750ms Alert 100%",
    16:  "1000ms Alert 100%",
    17:  "Strong Click 1 100%",
    18:  "Strong Click 2 80%",
    19:  "Strong Click 3 60%",
    20:  "Strong Click 4 30%",
    21:  "Medium Click 1 100%",
    22:  "Medium Click 2 80%",
    23:  "Medium Click 3 60%",
    24:  "Sharp Tick 1 100%",
    25:  "Sharp Tick 2 80%",
    26:  "Sharp Tick 3 60%",
    27:  "Short Double Click Strong 1 100%",
    28:  "Short Double Click Strong 2 80%",
    29:  "Short Double Click Strong 3 60%",
    30:  "Short Double Click Strong 4 30%",
    31:  "Short Double Click Medium 1 100%",
    32:  "Short Double Click Medium 2 80%",
    33:  "Short Double Click Medium 3 60%",
    34:  "Short Double Sharp Tick 1 100%",
    35:  "Short Double Sharp Tick 2 80%",
    36:  "Short Double Sharp Tick 3 60%",
    37:  "Long Double Sharp Click Strong 1 100%",
    38:  "Long Double Sharp Click Strong 2 80%",
    39:  "Long Double Sharp Click Strong 3 60%",
    40:  "Long Double Sharp Click Strong 4 30%",
    41:  "Long Double Sharp Click Medium 1 100%",
    42:  "Long Double Sharp Click Medium 2 80%",
    43:  "Long Double Sharp Click Medium 3 60%",
    44:  "Long Double Sharp Tick 1 100%",
    45:  "Long Double Sharp Tick 2 80%",
    46:  "Long Double Sharp Tick 3 60%",
    47:  "Buzz 1 100%",
    48:  "Buzz 2 80%",
    49:  "Buzz 3 60%",
    50:  "Buzz 4 40%",
    51:  "Buzz 5 20%",
    52:  "Pulsing Strong 1 100%",
    53:  "Pulsing Strong 2 60%",
    54:  "Pulsing Medium 1 100%",
    55:  "Pulsing Medium 2 60%",
    56:  "Pulsing Sharp 1 100%",
    57:  "Pulsing Sharp 2 60%",
    58:  "Transition Click 1 100%",
    59:  "Transition Click 2 80%",
    60:  "Transition Click 3 60%",
    61:  "Transition Click 4 40%",
    62:  "Transition Click 5 20%",
    63:  "Transition Click 6 10%",
    64:  "Transition Hum 1 100%",
    65:  "Transition Hum 2 80%",
    66:  "Transition Hum 3 60%",
    67:  "Transition Hum 4 40%",
    68:  "Transition Hum 5 20%",
    69:  "Transition Hum 6 10%",
    70:  "Ramp Down Long Smooth 1 100-0%",
    71:  "Ramp Down Long Smooth 2 100-0%",
    72:  "Ramp Down Medium Smooth 1 100-0%",
    73:  "Ramp Down Medium Smooth 2 100-0%",
    74:  "Ramp Down Short Smooth 1 100-0%",
    75:  "Ramp Down Short Smooth 2 100-0%",
    76:  "Ramp Down Long Sharp 1 100-0%",
    77:  "Ramp Down Long Sharp 2 100-0%",
    78:  "Ramp Down Medium Sharp 1 100-0%",
    79:  "Ramp Down Medium Sharp 2 100-0%",
    80:  "Ramp Down Short Sharp 1 100-0%",
    81:  "Ramp Down Short Sharp 2 100-0%",
    82:  "Ramp Up Long Smooth 1 0-100%",
    83:  "Ramp Up Long Smooth 2 0-100%",
    84:  "Ramp Up Medium Smooth 1 0-100%",
    85:  "Ramp Up Medium Smooth 2 0-100%",
    86:  "Ramp Up Short Smooth 1 0-100%",
    87:  "Ramp Up Short Smooth 2 0-100%",
    88:  "Ramp Up Long Sharp 1 0-100%",
    89:  "Ramp Up Long Sharp 2 0-100%",
    90:  "Ramp Up Medium Sharp 1 0-100%",
    91:  "Ramp Up Medium Sharp 2 0-100%",
    92:  "Ramp Up Short Sharp 1 0-100%",
    93:  "Ramp Up Short Sharp 2 0-100%",
    94:  "Ramp Down Long Smooth 1 50-0%",
    95:  "Ramp Down Long Smooth 2 50-0%",
    96:  "Ramp Down Medium Smooth 1 50-0%",
    97:  "Ramp Down Medium Smooth 2 50-0%",
    98:  "Ramp Down Short Smooth 1 50-0%",
    99:  "Ramp Down Short Smooth 2 50-0%",
    100: "Ramp Down Long Sharp 1 50-0%",
    101: "Ramp Down Long Sharp 2 50-0%",
    102: "Ramp Down Medium Sharp 1 50-0%",
    103: "Ramp Down Medium Sharp 2 50-0%",
    104: "Ramp Down Short Sharp 1 50-0%",
    105: "Ramp Down Short Sharp 2 50-0%",
    106: "Ramp Up Long Smooth 1 0-50%",
    107: "Ramp Up Long Smooth 2 0-50%",
    108: "Ramp Up Medium Smooth 1 0-50%",
    109: "Ramp Up Medium Smooth 2 0-50%",
    110: "Ramp Up Short Smooth 1 0-50%",
    111: "Ramp Up Short Smooth 2 0-50%",
    112: "Ramp Up Long Sharp 1 0-50%",
    113: "Ramp Up Long Sharp 2 0-50%",
    114: "Ramp Up Medium Sharp 1 0-50%",
    115: "Ramp Up Medium Sharp 2 0-50%",
    116: "Ramp Up Short Sharp 1 0-50%",
    117: "Ramp Up Short Sharp 2 0-50%",
    118: "Long Buzz (programmatic stop) 100%",
    119: "Smooth Hum 1 50%",
    120: "Smooth Hum 2 40%",
    121: "Smooth Hum 3 30%",
    122: "Smooth Hum 4 20%",
    123: "Smooth Hum 5 10%",
}


async def run():
    print(f"Scanning for '{DEVICE_NAME}'...")
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=SCAN_TIMEOUT)
    if device is None:
        print(f"'{DEVICE_NAME}' not found.")
        return

    print(f"Connected to {device.address}")
    print("Enter to play next | number to jump | 'r' to repeat | 'q' to quit\n")

    async with BleakClient(device) as client:
        current = 1

        while True:
            name = EFFECTS.get(current, "???")
            raw = input(f"[{current:3}/123] {name} > ").strip().lower()

            if raw == "q":
                break
            elif raw == "r":
                pass  # replay current, don't advance
            elif raw == "":
                effect = current
                await client.write_gatt_char(UART_RX_UUID, bytes([0x48, effect]), response=False)
                current = current + 1 if current < 123 else 1
                continue
            else:
                try:
                    current = int(raw)
                    if not 1 <= current <= 123:
                        print("  Must be 1–123.")
                        continue
                except ValueError:
                    print("  Invalid input.")
                    continue

            await client.write_gatt_char(UART_RX_UUID, bytes([0x48, current]), response=False)


if __name__ == "__main__":
    asyncio.run(run())