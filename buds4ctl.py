#!/usr/bin/env python3
"""
buds4ctl — Command-Line Controller for Samsung Galaxy Buds4 Pro (SM-R640).
Uses the active Studio daemon at http://127.0.0.1:8765 if running, or connects
directly via BlueZ RFCOMM if the daemon is not running.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from typing import Any, Dict, Optional

from gi.repository import GLib

from buds4pro_protocol import Buds4ProController

API_BASE = "http://127.0.0.1:8765"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def try_http_api(endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    url = f"{API_BASE}{endpoint}"
    try:
        if payload is None:
            req = urllib.request.Request(url, method="GET")
        else:
            raw = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=raw, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def run_direct(fn):
    loop = GLib.MainLoop()
    ctrl = Buds4ProController()
    result = {"done": False}

    def on_update(state, pkt):
        if state.connected and pkt is not None and not result["done"]:
            result["done"] = True
            GLib.timeout_add(350, do_action)

    def do_action():
        fn(ctrl)
        GLib.timeout_add(500, lambda: (ctrl.disconnect(bluetooth=False), loop.quit(), False)[2])
        return False

    ctrl.add_listener(on_update)
    ctrl.connect(lambda ok, msg: None if ok else (print(msg), loop.quit()))
    GLib.timeout_add(4500, lambda: (loop.quit(), False)[1])
    loop.run()
    return ctrl.to_dict()


def execute_action(action: str, body: Dict[str, Any], direct_fn) -> Dict[str, Any]:
    res = try_http_api(f"/api/{action}", body)
    if res and res.get("state"):
        return res["state"]
    return run_direct(direct_fn)


def print_status(s: Dict[str, Any]):
    print(f"Device:        {s.get('device_name')} ({s.get('device_mac')}) — {s.get('model_name')}")
    print(f"Connected:     {s.get('connected')} | Firmware: {s.get('fw_version_left') or 'R640XXU0AZD2'} (Case: {s.get('fw_version_cradle') or 'R640XXUZD1'})")
    print(f"Battery:       Left {s.get('battery_left')}% ({s.get('placement_left_name')}) | Right {s.get('battery_right')}% ({s.get('placement_right_name')}) | Case {s.get('battery_case')}%")
    print(f"Thermal/Cell:  Left {s.get('temp_left_c')}°C | Right {s.get('temp_right_c')}°C | {s.get('vcell_mv')} mV | Cycles L={s.get('cycles_left')} R={s.get('cycles_right')}")
    print(f"Noise Control: {s.get('noise_control_mode_name')} | ANC Level: {s.get('anc_level', 0) + 1}/5 | Ambient Vol: {s.get('ambient_volume', 0) + 1}/5")
    print(f"Detection:     Voice Detect={'ON' if s.get('detect_conversations') else 'OFF'} | Siren Detect={'ON' if s.get('siren_detect') else 'OFF'} | Adaptive Vol={'ON' if s.get('adaptive_volume') else 'OFF'}")
    print(f"Equalizer:     {s.get('equalizer_name')} | 360 Audio={'ON' if s.get('spatial_audio') else 'OFF'} (HeadTrack={'ON' if s.get('spatial_head_tracking') else 'OFF'})")
    print(f"Touch/Lights:  LockAll={'ON' if s.get('touchpad_lock_all') else 'OFF'} | Blade Lights={s.get('lighting_control')} | Bixby={'ON' if s.get('bixby_wakeup') else 'OFF'}")


def main():
    parser = argparse.ArgumentParser(description="Samsung Galaxy Buds4 Pro Control CLI (SM-R640)")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("status", help="Show full earbud status and telemetry")
    sub.add_parser("connect", help="Connect Galaxy Buds4 Pro to Laptop")
    sub.add_parser("disconnect", help="Disconnect Galaxy Buds4 Pro from Laptop")
    sub.add_parser("gui", help="Launch the GTK4 + Libadwaita Desktop Studio")
    sub.add_parser("web", help="Launch the background daemon and Web Studio at http://127.0.0.1:8765")
    sub.add_parser("anc", help="Enable Active Noise Cancellation (ANC)")
    sub.add_parser("ambient", help="Enable Ambient Sound mode")
    sub.add_parser("adaptive", help="Enable Adaptive Noise Control mode")
    sub.add_parser("off", help="Turn Noise Controls Off")

    p_anc_lvl = sub.add_parser("anc-level", help="Set ANC strength level (1..5)")
    p_anc_lvl.add_argument("level", type=int, choices=[1, 2, 3, 4, 5])

    p_amb_vol = sub.add_parser("ambient-vol", help="Set Ambient Sound volume (1..5)")
    p_amb_vol.add_argument("volume", type=int, choices=[1, 2, 3, 4, 5])

    p_voice = sub.add_parser("voice-detect", help="Enable/disable Conversation Detection")
    p_voice.add_argument("state", choices=["on", "off"])

    p_siren = sub.add_parser("siren-detect", help="Enable/disable Siren Detection")
    p_siren.add_argument("state", choices=["on", "off"])

    p_advol = sub.add_parser("adaptive-vol", help="Enable/disable Adaptive Volume")
    p_advol.add_argument("state", choices=["on", "off"])

    p_eq = sub.add_parser("eq", help="Set Equalizer preset (off, bass, soft, dynamic, clear, treble, custom)")
    p_eq.add_argument("preset", choices=["off", "bass", "soft", "dynamic", "clear", "treble", "custom"])

    p_spatial = sub.add_parser("spatial", help="Enable/disable 360 Spatial Audio")
    p_spatial.add_argument("state", choices=["on", "off", "headtrack"])

    p_game = sub.add_parser("game-mode", help="Enable/disable Low-Latency Gaming Mode")
    p_game.add_argument("state", choices=["on", "off"])

    p_light = sub.add_parser("lights", help="Set Blade Lighting style (0=blink, 1=fade, 2=steady)")
    p_light.add_argument("mode", type=int, choices=[0, 1, 2])

    p_ring = sub.add_parser("ring", help="Start or stop Find My Earbuds ringing")
    p_ring.add_argument("state", choices=["start", "stop"])

    p_raw = sub.add_parser("raw", help="Send raw SPP message ID and hex payload")
    p_raw.add_argument("msg_id", type=str)
    p_raw.add_argument("payload_hex", nargs="?", default="")

    args = parser.parse_args()

    if args.cmd == "gui":
        os.execv(sys.executable, [sys.executable, os.path.join(SCRIPT_DIR, "buds4pro_gtk.py")])
    elif args.cmd == "web":
        os.execv(sys.executable, [sys.executable, os.path.join(SCRIPT_DIR, "buds4pro_web.py")])
    elif args.cmd in (None, "status"):
        res = try_http_api("/api/state")
        state = res["state"] if (res and res.get("state")) else run_direct(lambda c: c.request_telemetry_refresh())
        print_status(state)
    elif args.cmd == "connect":
        res = try_http_api("/api/connect", {})
        state = res["state"] if (res and res.get("state")) else run_direct(lambda c: c.request_telemetry_refresh())
        print_status(state)
    elif args.cmd == "disconnect":
        res = try_http_api("/api/disconnect", {})
        if res and res.get("state"):
            print_status(res["state"])
        else:
            ctrl = Buds4ProController()
            ctrl.discover_buds()
            ctrl.disconnect(bluetooth=True)
            print(f"Disconnected {ctrl.state.device_name} ({ctrl.state.device_mac})")
    elif args.cmd == "anc":
        s = execute_action("set_noise_control", {"mode": 1}, lambda c: c.set_noise_control(1))
        print_status(s)
    elif args.cmd == "ambient":
        s = execute_action("set_noise_control", {"mode": 2}, lambda c: c.set_noise_control(2))
        print_status(s)
    elif args.cmd == "adaptive":
        s = execute_action("set_noise_control", {"mode": 3}, lambda c: c.set_noise_control(3))
        print_status(s)
    elif args.cmd == "off":
        s = execute_action("set_noise_control", {"mode": 0}, lambda c: c.set_noise_control(0))
        print_status(s)
    elif args.cmd == "anc-level":
        lvl = args.level - 1
        s = execute_action("set_anc_level", {"level": lvl}, lambda c: c.set_anc_level(lvl))
        print_status(s)
    elif args.cmd == "ambient-vol":
        vol = args.volume - 1
        s = execute_action("set_ambient_volume", {"volume": vol}, lambda c: c.set_ambient_volume(vol))
        print_status(s)
    elif args.cmd == "voice-detect":
        en = args.state == "on"
        s = execute_action("set_conversation_detect", {"enabled": en}, lambda c: c.set_conversation_detect(en))
        print_status(s)
    elif args.cmd == "siren-detect":
        en = args.state == "on"
        s = execute_action("set_siren_detect", {"enabled": en}, lambda c: c.set_siren_detect(en))
        print_status(s)
    elif args.cmd == "adaptive-vol":
        en = args.state == "on"
        s = execute_action("set_adaptive_volume", {"enabled": en}, lambda c: c.set_adaptive_volume(en))
        print_status(s)
    elif args.cmd == "eq":
        eq_map = {"off": 0, "bass": 1, "soft": 2, "dynamic": 3, "clear": 4, "treble": 5, "custom": 7}
        m = eq_map[args.preset]
        s = execute_action("set_equalizer_preset", {"mode": m}, lambda c: c.set_equalizer_preset(m))
        print_status(s)
    elif args.cmd == "spatial":
        en = args.state in ("on", "headtrack")
        ht = args.state == "headtrack"
        s = execute_action("set_spatial_audio", {"enabled": en, "head_tracking": ht}, lambda c: c.set_spatial_audio(en, ht))
        print_status(s)
    elif args.cmd == "game-mode":
        en = args.state == "on"
        s = execute_action("set_gaming_mode", {"enabled": en}, lambda c: c.set_gaming_mode(en))
        print_status(s)
    elif args.cmd == "lights":
        s = execute_action("set_lighting_mode", {"mode": args.mode}, lambda c: c.set_lighting_mode(args.mode))
        print_status(s)
    elif args.cmd == "ring":
        en = args.state == "start"
        s = execute_action("find_my_buds", {"active": en, "wearing": True}, lambda c: c.set_find_my_buds(en, True))
        print_status(s)
    elif args.cmd == "raw":
        mid = int(args.msg_id, 16) if args.msg_id.startswith("0x") else int(args.msg_id, 10)
        pl = bytes.fromhex(args.payload_hex) if args.payload_hex else b""
        s = execute_action("send_raw", {"msg_id": mid, "payload_hex": args.payload_hex}, lambda c: c.send_message(mid, pl))
        print_status(s)


if __name__ == "__main__":
    main()
