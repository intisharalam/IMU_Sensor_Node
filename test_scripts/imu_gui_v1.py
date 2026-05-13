"""
imu_monitor.py
──────────────
DearPyGui status board for 3 IMUs over BLE.

Layout (per IMU column):
  • Status card  — name, connected indicator, packet count, sync offset
  • Haptic / Sync buttons
  • Live scrolling plot — Roll, Pitch, Yaw (last PLOT_WINDOW_S seconds)

Bottom bar: Haptic All | Sync All | Quit

Usage:
  pip install bleak dearpygui
  python imu_monitor.py
"""

import asyncio
import threading
import time
import collections
import sys

from bleak import BleakClient, BleakScanner
import dearpygui.dearpygui as dpg

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

DEVICE_NAMES = {
    "wrist": "IMU_WRIST",
    "arm":   "IMU_ARM",
    "chest": "IMU_CHEST",
}
SLOT_LABELS = {
    "wrist": "WRIST",
    "arm":   "ARM",
    "chest": "CHEST",
}

UART_TX_UUID   = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX_UUID   = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

HAPTIC_ON      = bytes([0x01])
SYNC_REQ       = bytes([0x53])

SCAN_TIMEOUT   = 15.0
RECONNECT_WAIT = 5.0

PLOT_WINDOW_S  = 8.0      # seconds of history shown in plot
PLOT_RATE_HZ   = 30       # GUI refresh rate
GUI_W, GUI_H   = 1280, 780

# ═══════════════════════════════════════════════════════════════════════════════
#  SHARED STATE
# ═══════════════════════════════════════════════════════════════════════════════

_lock = threading.Lock()

def _make_slot():
    max_pts = int(PLOT_WINDOW_S * 100)   # 100 Hz max from IMU
    return {
        "client":        None,
        "connected":     False,
        "address":       None,
        "rx_buf":        "",
        "packet_count":  0,
        "sync_offset_ms": None,
        "haptic_active": False,
        # ring buffers for plot
        "times":  collections.deque(maxlen=max_pts),
        "rolls":  collections.deque(maxlen=max_pts),
        "pitchs": collections.deque(maxlen=max_pts),
        "yaws":   collections.deque(maxlen=max_pts),
        # last values for change-threshold filtering
        "last_vals": None,
    }

_state = {k: _make_slot() for k in DEVICE_NAMES}

_loop: asyncio.AbstractEventLoop = None
_running = True

# ═══════════════════════════════════════════════════════════════════════════════
#  BLE LAYER
# ═══════════════════════════════════════════════════════════════════════════════

def _make_rx_handler(key: str):
    def handler(_, data: bytearray):
        text = data.decode("utf-8", errors="replace")
        with _lock:
            _state[key]["rx_buf"] += text
            buf = _state[key]["rx_buf"]

        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            line = line.strip()
            if not line:
                continue

            with _lock:
                _state[key]["rx_buf"] = buf
                _state[key]["packet_count"] += 1

            if line.startswith("SYNC:"):
                recv_t = time.monotonic()
                try:
                    board_ms = int(line.split("SYNC:")[1])
                    offset   = (recv_t * 1000) - board_ms
                    with _lock:
                        _state[key]["sync_offset_ms"] = offset
                except ValueError:
                    pass
            else:
                try:
                    r, p, y = (float(v) for v in line.split(","))
                except ValueError:
                    continue
                t_now = time.monotonic()
                with _lock:
                    _state[key]["times"].append(t_now)
                    _state[key]["rolls"].append(r)
                    _state[key]["pitchs"].append(p)
                    _state[key]["yaws"].append(y)
    return handler


async def _imu_task(key: str, name: str):
    global _running
    while _running:
        try:
            device = await BleakScanner.find_device_by_name(name, timeout=SCAN_TIMEOUT)
        except Exception:
            await asyncio.sleep(RECONNECT_WAIT)
            continue

        if device is None:
            await asyncio.sleep(RECONNECT_WAIT)
            continue

        with _lock:
            _state[key]["address"] = device.address

        try:
            async with BleakClient(device, timeout=10.0) as client:
                with _lock:
                    _state[key]["client"]    = client
                    _state[key]["connected"] = True

                await client.start_notify(UART_TX_UUID, _make_rx_handler(key))
                while client.is_connected and _running:
                    await asyncio.sleep(0.3)

        except Exception:
            pass
        finally:
            with _lock:
                _state[key]["client"]    = None
                _state[key]["connected"] = False

        if _running:
            await asyncio.sleep(RECONNECT_WAIT)


async def _send(key: str, payload: bytes):
    with _lock:
        client = _state[key]["client"]
        conn   = _state[key]["connected"]
    if client and conn:
        try:
            await client.write_gatt_char(UART_RX_UUID, payload, response=False)
            if payload == HAPTIC_ON:
                with _lock:
                    _state[key]["haptic_active"] = True
                await asyncio.sleep(0.5)
                with _lock:
                    _state[key]["haptic_active"] = False
        except Exception:
            pass


def send_cmd(key: str, payload: bytes):
    if _loop:
        asyncio.run_coroutine_threadsafe(_send(key, payload), _loop)

def send_all(payload: bytes):
    for k in DEVICE_NAMES:
        send_cmd(k, payload)


def start_ble():
    global _loop
    _loop = asyncio.new_event_loop()
    for key, name in DEVICE_NAMES.items():
        _loop.create_task(_imu_task(key, name))
    _loop.run_forever()

# ═══════════════════════════════════════════════════════════════════════════════
#  THEME
# ═══════════════════════════════════════════════════════════════════════════════

# Colour palette — dark industrial with sharp accents
C_BG          = (13,  17,  23,  255)   # near-black
C_PANEL       = (22,  28,  36,  255)   # card background
C_BORDER      = (40,  50,  65,  255)   # subtle border
C_TEXT        = (210, 220, 230, 255)   # primary text
C_DIM         = (90,  105, 120, 255)   # secondary / dim text
C_GREEN       = (50,  220, 120, 255)   # connected
C_RED         = (220,  70,  70, 255)   # disconnected
C_AMBER       = (240, 180,  40, 255)   # haptic active
C_ACCENT      = (70,  160, 255, 255)   # button / highlight
C_ROLL        = (70,  160, 255, 255)   # plot line — roll
C_PITCH       = (50,  220, 120, 255)   # plot line — pitch
C_YAW         = (240, 180,  40, 255)   # plot line — yaw


def _build_theme():
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg,       C_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg,        C_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg,        C_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_Border,         C_BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_Text,           C_TEXT)
            dpg.add_theme_color(dpg.mvThemeCol_Button,         (40,  100, 200, 200))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,  (60,  130, 240, 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,   (30,   80, 170, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg,        C_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive,  C_PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg,    C_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab,  C_BORDER)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding,  6)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding,   6)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,   4)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding,    4)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing,     8, 6)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding,  12, 12)
    return global_theme


def _btn_theme(colour):
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button,        (*colour[:3], 180))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (*colour[:3], 255))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,  (*colour[:3], 130))
    return t


def _plot_theme():
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvPlot):
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg,      C_PANEL,  category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvPlotCol_PlotBg,        (18, 24, 32, 255), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_PlotBorder,    C_BORDER, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_AxisText,      C_DIM,    category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_AxisGrid,      (*C_BORDER[:3], 80), category=dpg.mvThemeCat_Plots)
    return t

# ═══════════════════════════════════════════════════════════════════════════════
#  GUI BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

# Tag registry — built during layout, used during updates
_tags = {}   # e.g. _tags["wrist"]["status_dot"], ["packet_text"], ["plot_roll"] …

COL_W     = (GUI_W - 60) // 3
CARD_H    = 160
PLOT_H    = GUI_H - CARD_H - 130


def _build_imu_column(key: str, col_index: int):
    label = SLOT_LABELS[key]
    x     = 20 + col_index * (COL_W + 10)

    tags = {}
    _tags[key] = tags

    # ── Status card ───────────────────────────────────────────────────────────
    with dpg.child_window(tag=f"card_{key}", pos=(x, 50),
                          width=COL_W, height=CARD_H, border=True):

        # Header row: coloured dot + name
        with dpg.group(horizontal=True):
            tags["dot"] = dpg.add_text("●", color=C_RED)
            dpg.add_text(f"  {label}", color=C_TEXT)

        dpg.add_spacer(height=4)
        tags["status_text"] = dpg.add_text("Searching...", color=C_DIM)
        tags["address_text"] = dpg.add_text("", color=C_DIM)

        dpg.add_spacer(height=6)

        with dpg.group(horizontal=True):
            dpg.add_text("Packets:", color=C_DIM)
            tags["packet_text"] = dpg.add_text("—", color=C_TEXT)

        with dpg.group(horizontal=True):
            dpg.add_text("Sync offset:", color=C_DIM)
            tags["sync_text"] = dpg.add_text("—", color=C_TEXT)

        dpg.add_spacer(height=8)

        # Buttons
        haptic_theme = _btn_theme(C_AMBER)
        sync_theme   = _btn_theme(C_ACCENT)

        with dpg.group(horizontal=True):
            hb = dpg.add_button(
                label="  Haptic  ",
                callback=lambda: send_cmd(key, HAPTIC_ON),
                width=int(COL_W * 0.47)
            )
            dpg.bind_item_theme(hb, haptic_theme)
            tags["haptic_btn"] = hb

            dpg.add_spacer(width=6)

            sb = dpg.add_button(
                label="  Sync  ",
                callback=lambda: send_cmd(key, SYNC_REQ),
                width=int(COL_W * 0.40)
            )
            dpg.bind_item_theme(sb, sync_theme)
            tags["sync_btn"] = sb

    # ── Live plot ─────────────────────────────────────────────────────────────
    plot_y = 50 + CARD_H + 10

    with dpg.child_window(tag=f"plot_win_{key}", pos=(x, plot_y),
                          width=COL_W, height=PLOT_H, border=True):

        dpg.add_text(f"  {label} — Roll / Pitch / Yaw", color=C_DIM)

        with dpg.plot(tag=f"plot_{key}", height=PLOT_H - 36,
                      width=COL_W - 16, no_title=True,
                      no_mouse_pos=True):

            dpg.add_plot_legend()

            ax = dpg.add_plot_axis(dpg.mvXAxis, label="", no_tick_labels=True)
            tags["x_axis"] = ax

            with dpg.plot_axis(dpg.mvYAxis, label="deg"):
                tags["roll_series"]  = dpg.add_line_series(
                    [], [], label="Roll",
                    tag=f"series_roll_{key}")
                dpg.bind_item_theme(f"series_roll_{key}",  _series_theme(C_ROLL))

                tags["pitch_series"] = dpg.add_line_series(
                    [], [], label="Pitch",
                    tag=f"series_pitch_{key}")
                dpg.bind_item_theme(f"series_pitch_{key}", _series_theme(C_PITCH))

                tags["yaw_series"]   = dpg.add_line_series(
                    [], [], label="Yaw",
                    tag=f"series_yaw_{key}")
                dpg.bind_item_theme(f"series_yaw_{key}",   _series_theme(C_YAW))

        # Legend labels
        with dpg.group(horizontal=True):
            dpg.add_text("●", color=C_ROLL);  dpg.add_text(" Roll  ", color=C_DIM)
            dpg.add_text("●", color=C_PITCH); dpg.add_text(" Pitch  ", color=C_DIM)
            dpg.add_text("●", color=C_YAW);   dpg.add_text(" Yaw", color=C_DIM)

    dpg.bind_item_theme(f"plot_{key}", _plot_theme())


def _series_theme(colour):
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvLineSeries):
            dpg.add_theme_color(dpg.mvPlotCol_Line, colour,
                                category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 1.8,
                                category=dpg.mvThemeCat_Plots)
    return t


def _build_bottom_bar():
    y = GUI_H - 56
    haptic_t = _btn_theme(C_AMBER)
    sync_t   = _btn_theme(C_ACCENT)
    quit_t   = _btn_theme(C_RED)

    with dpg.child_window(pos=(20, y), width=GUI_W - 40, height=46, border=False):
        with dpg.group(horizontal=True):
            hb = dpg.add_button(label="  ⚡  Haptic All  ",
                                callback=lambda: send_all(HAPTIC_ON), width=180)
            dpg.bind_item_theme(hb, haptic_t)

            dpg.add_spacer(width=10)

            sb = dpg.add_button(label="  ⟳  Sync All  ",
                                callback=lambda: send_all(SYNC_REQ), width=160)
            dpg.bind_item_theme(sb, sync_t)

            dpg.add_spacer(width=GUI_W - 480)

            qb = dpg.add_button(label="  Quit  ",
                                callback=_quit, width=90)
            dpg.bind_item_theme(qb, quit_t)


def _build_title():
    with dpg.child_window(pos=(20, 10), width=GUI_W - 40, height=34, border=False):
        with dpg.group(horizontal=True):
            dpg.add_text("IMU MONITOR", color=C_ACCENT)
            dpg.add_text("  —  3× XIAO nRF52840  |  BNO085  |  NUS BLE", color=C_DIM)

# ═══════════════════════════════════════════════════════════════════════════════
#  UPDATE LOOP  (runs every frame via dpg render callback)
# ═══════════════════════════════════════════════════════════════════════════════

def _update_gui():
    now = time.monotonic()

    for key in DEVICE_NAMES:
        tags = _tags[key]

        with _lock:
            connected   = _state[key]["connected"]
            address     = _state[key]["address"]
            packets     = _state[key]["packet_count"]
            sync_off    = _state[key]["sync_offset_ms"]
            haptic_act  = _state[key]["haptic_active"]
            times_raw   = list(_state[key]["times"])
            rolls_raw   = list(_state[key]["rolls"])
            pitchs_raw  = list(_state[key]["pitchs"])
            yaws_raw    = list(_state[key]["yaws"])

        # ── Status card ───────────────────────────────────────────────────────
        if connected:
            dpg.configure_item(tags["dot"],         color=C_GREEN)
            dpg.configure_item(tags["status_text"], default_value="Connected",
                               color=C_GREEN)
            dpg.configure_item(tags["address_text"],
                               default_value=address or "", color=C_DIM)
        else:
            dpg.configure_item(tags["dot"],         color=C_RED)
            dpg.configure_item(tags["status_text"], default_value="Searching...",
                               color=C_RED)
            dpg.configure_item(tags["address_text"], default_value="")

        dpg.configure_item(tags["packet_text"],
                           default_value=str(packets) if packets else "—")

        if sync_off is not None:
            dpg.configure_item(tags["sync_text"],
                               default_value=f"{sync_off:+.1f} ms", color=C_TEXT)
        else:
            dpg.configure_item(tags["sync_text"], default_value="—", color=C_DIM)

        # Haptic button flashes amber while active
        haptic_col = C_AMBER if haptic_act else (60, 70, 85, 200)
        dpg.configure_item(tags["haptic_btn"])  # keep enabled

        # ── Plot ─────────────────────────────────────────────────────────────
        if times_raw:
            # Trim to window
            cutoff = now - PLOT_WINDOW_S
            i0 = 0
            for i, t in enumerate(times_raw):
                if t >= cutoff:
                    i0 = i
                    break

            xs = [t - now for t in times_raw[i0:]]   # seconds relative to now
            rs = rolls_raw[i0:]
            ps = pitchs_raw[i0:]
            ys = yaws_raw[i0:]

            dpg.set_value(tags["roll_series"],  [xs, rs])
            dpg.set_value(tags["pitch_series"], [xs, ps])
            dpg.set_value(tags["yaw_series"],   [xs, ys])

            dpg.set_axis_limits(tags["x_axis"], -PLOT_WINDOW_S, 0)
        else:
            dpg.set_value(tags["roll_series"],  [[], []])
            dpg.set_value(tags["pitch_series"], [[], []])
            dpg.set_value(tags["yaw_series"],   [[], []])
            dpg.set_axis_limits(tags["x_axis"], -PLOT_WINDOW_S, 0)


def _quit():
    global _running
    _running = False
    if _loop:
        _loop.call_soon_threadsafe(_loop.stop)
    dpg.stop_dearpygui()

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    # Start BLE in background thread
    ble_thread = threading.Thread(target=start_ble, daemon=True)
    ble_thread.start()

    # ── DearPyGui setup ───────────────────────────────────────────────────────
    dpg.create_context()
    dpg.create_viewport(title="IMU Monitor", width=GUI_W, height=GUI_H,
                        resizable=False)
    dpg.setup_dearpygui()

    global_theme = _build_theme()
    dpg.bind_theme(global_theme)

    with dpg.window(tag="main", no_title_bar=True, no_resize=True,
                    no_move=True, no_scrollbar=True,
                    width=GUI_W, height=GUI_H):

        _build_title()

        for i, key in enumerate(DEVICE_NAMES):
            _build_imu_column(key, i)

        _build_bottom_bar()

    dpg.set_primary_window("main", True)
    dpg.show_viewport()

    # Render loop
    while dpg.is_dearpygui_running():
        _update_gui()
        dpg.render_dearpygui_frame()

    dpg.destroy_context()
    _running_flag_cleanup()


def _running_flag_cleanup():
    global _running
    _running = False
    if _loop and _loop.is_running():
        _loop.call_soon_threadsafe(_loop.stop)


if __name__ == "__main__":
    main()