#!/usr/bin/env python3
"""
Samsung Galaxy Buds4 Pro (SM-R640) Bluetooth SPP Protocol Engine & BlueZ Driver.

Reverse-engineered binary framing and message specifications for Samsung's
proprietary Bluetooth RFCOMM control channel:
  - Primary SPP Service UUID: 2e73a4ad-332d-41fc-90e2-16bef06523f2
  - SMEP Alt Service UUID:    f8620674-a1ed-41ab-a8b9-de9ad655729d
  - Frame format:
      [SOM=0xFD] [Header: uint16 LE (size | flags)] [MsgId: uint8] [Payload: N bytes] [CRC16-CCITT: uint16 LE] [EOM=0xDD]
"""

from __future__ import annotations

import datetime
import os
import socket
import struct
import threading
import time
from dataclasses import dataclass, field, asdict
from enum import IntEnum
from typing import Callable, Dict, List, Optional, Tuple

import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib


SPP_UUID = "2e73a4ad-332d-41fc-90e2-16bef06523f2"
SMEP_UUID = "f8620674-a1ed-41ab-a8b9-de9ad655729d"
PROFILE_PATH = "/org/bluez/buds4pro_studio_profile"

SOM = 0xFD
EOM = 0xDD


class MsgIds(IntEnum):
    UNK_SPP_ALT = 1
    HOT_COMMAND_MANAGE = 15
    SET_MODE_CHANGE = 16
    GET_MODE = 17
    HIDDEN_CMD_MODE = 18
    HIDDEN_CMD_DATA = 19
    SET_DEBUG_MODE = 32
    DEBUG_MODE_LOG = 33
    DEBUG_SKU = 34
    READ_WATER_DETECTION_HISTORY = 35
    DEBUG_GET_VERSION = 36
    DEBUG_GET_ALL_DATA = 38
    DEBUG_BUILD_INFO = 40
    DEBUG_SERIAL_NUMBER = 41
    TOUCH_ON_BUDS = 45
    USAGE_REPORT = 64
    METERING_REPORT = 65
    UNIVERSAL_MSG_ID_ACKNOWLEDGEMENT = 66
    WRITE_PROPERTY = 67
    READ_PROPERTY = 68
    NOTIFY_PROPERTY = 69
    USAGE_REPORT_V2 = 71
    EXTRA_CLEAR_SOUND_CALL = 72
    RESET = 80
    RESP = 81
    REBOOT = 82
    POWEROFF = 83
    STATUS_ALERT = 87
    STATUS_UPDATED = 96
    EXTENDED_STATUS_UPDATED = 97
    CONNECTION_UPDATED = 98
    VERSION_INFO = 99
    SET_HOT_COMMAND = 100
    SET_BIXBY_KEYWORD = 102
    SET_HEARING_TEST_RESULT = 103
    VERSION_INFO_LONG = 104
    CUSTOM_EQUALIZE_RECV = 105
    PAUSE_MEDIA_WHEN_ONE_BUD_REMOVED = 108
    AMBIENT_DURING_CALL_NOTI = 109
    SET_CALL_PATH_CONTROL = 110
    SET_ANC_WITH_ONE_EARBUD = 111
    MAIN_CHANGE = 112
    PROFILE_CONTROL = 113
    PAIRING_MODE = 114
    AUTO_SWITCH_AUDIO_OUTPUT = 115
    MULTIPOINT_INFO = 118
    NOISE_CONTROLS_UPDATE = 119
    NOISE_CONTROLS = 120
    SET_TOUCH_AND_HOLD_NOISE_CONTROLS = 121
    SET_DETECT_CONVERSATIONS = 122
    SET_DETECT_CONVERSATIONS_DURATION = 123
    SET_SPATIAL_AUDIO = 124
    SET_SPEAK_SEAMLESSLY = 125
    SET_AMPLIFY_AMBIENT_SOUND = 126
    SET_AMBIENT_MODE = 128
    AMBIENT_MODE_UPDATED = 129
    CUSTOMIZE_AMBIENT_SOUND = 130
    NOISE_REDUCTION_LEVEL = 131
    AMBIENT_VOLUME = 132
    ADJUST_SOUND_SYNC = 133
    EQUALIZER = 134
    GAME_MODE = 135
    MANAGER_INFO = 136
    CUSTOM_EQUALIZE_SEND = 137
    SET_IN_BAND_RINGTONE = 138
    SET_SIDETONE = 139
    TAP_TEST_MODE = 141
    BUDS_LIGHTING_SYNC = 142
    SET_HEARING_ENHANCEMENTS = 143
    LOCK_TOUCHPAD = 144
    TOUCH_UPDATED = 145
    SET_TOUCHPAD_OPTION = 146
    SET_TOUCHPAD_OTHER_OPTION = 147
    BATTERY_TYPE = 148
    OUTSIDE_DOUBLE_TAP = 149
    EXTRA_HIGH_AMBIENT = 150
    SET_VOICE_WAKE_UP = 151
    SET_NOISE_REDUCTION = 152
    VOICE_WAKE_UP_LANGUAGE = 153
    VOICE_WAKE_UP_EVENT = 154
    NOISE_REDUCTION_MODE_UPDATE = 155
    VOICE_WAKE_UP_LISTENING_STATUS = 156
    CHECK_THE_FIT_OF_EARBUDS = 157
    CHECK_THE_FIT_OF_EARBUDS_RESULT = 158
    PASS_THROUGH = 159
    FIND_MY_EARBUDS_START = 160
    FIND_MY_EARBUDS_STOP = 161
    MUTE_EARBUD = 162
    MUTE_EARBUD_STATUS_UPDATED = 163
    VOICE_NOTI_STATUS = 164
    VOICE_NOTI_STOP = 165
    FIND_MY_EARBUDS_ON_WEARING_START = 166
    UPDATE_TIME = 167
    SELF_TEST = 171
    SET_FMM_CONFIG = 172
    GET_FMM_CONFIG = 173
    SET_SEAMLESS_CONNECTION = 175
    SPATIAL_AUDIO_DATA = 194
    SPATIAL_AUDIO_CONTROL = 195
    SET_ADAPTIVE_VOLUME_ENABLED = 197
    NECK_POSTURE_CALI_DATA = 198
    NECK_POSTURE_CONTROL = 199
    NECK_POSTURE_PHONE_DATA = 200
    NECK_POSTURE_SET = 201
    OVERHEAT = 202
    HEARING_TEST_DATA = 204
    CRADLE_SERIAL_NUMBER = 205
    SOC_BATTERY_CYCLE = 206
    RESET_BATTERY_SOC_CYCLE = 207
    GET_PERSONAL_NAME = 211
    ADAPTIVE_EQ_VOLUME_CONTROL = 217
    ADAPTIVE_EQ_CONTROL = 218
    ADAPTIVE_EQ_STATUS = 219
    UASC_SIREN_DETECT = 222
    TELEMETRY_PERIODIC_244 = 244
    SET_TOUCH_TYPE = 255


class NoiseControlMode(IntEnum):
    OFF = 0
    ANC = 1
    AMBIENT = 2
    ADAPTIVE = 3


PLACEMENT_NAMES = {
    0: "Disconnected",
    1: "Wearing",
    2: "Idle (Out of Ear)",
    3: "In Open Case",
    4: "In Closed Case",
    100: "Charging",
}

TOUCH_OPTION_NAMES = {
    1: "Voice Assistant / Bixby",
    2: "Switch Noise Controls",
    3: "Volume Control",
    4: "Spotify Spot On",
    5: "Custom (Left)",
    6: "Custom (Right)",
}

EQ_PRESET_NAMES = {
    0: "Off (Balanced)",
    1: "Bass Boost",
    2: "Soft",
    3: "Dynamic",
    4: "Clear",
    5: "Treble Boost",
    7: "Custom (9-Band)",
}

DEVICE_COLOR_NAMES = {
    359: "Buds4 Pro Silver/Black (SM-R640)",
    360: "Buds4 Pro White (SM-R640)",
    361: "Buds4 Pro Apricot (SM-R640)",
    340: "Buds3 Pro Silver",
    341: "Buds3 Pro White",
}

BIXBY_LANGUAGES = {
    0: "de-DE (German)",
    1: "en-GB (English UK)",
    2: "en-US (English US)",
    3: "es-ES (Spanish)",
    4: "fr-FR (French)",
    5: "it-IT (Italian)",
    6: "ko-KR (Korean)",
    7: "pt-BR (Portuguese BR)",
    8: "zh-CN (Chinese)",
    9: "hu-HU (Hungarian)",
}

CRC16_TAB = [
    0, 4129, 8258, 12387, 16516, 20645, 24774, 28903, 33032, 37161, 41290,
    45419, 49548, 53677, 57806, 61935, 4657, 528, 12915, 8786, 21173, 17044, 29431, 25302,
    37689, 33560, 45947, 41818, 54205, 50076, 62463, 58334, 9314, 13379, 1056, 5121, 25830,
    29895, 17572, 21637, 42346, 46411, 34088, 38153, 58862, 62927, 50604, 54669, 13907,
    9842, 5649, 1584, 30423, 26358, 22165, 18100, 46939, 42874, 38681, 34616, 63455, 59390,
    55197, 51132, 18628, 22757, 26758, 30887, 2112, 6241, 10242, 14371, 51660, 55789,
    59790, 63919, 35144, 39273, 43274, 47403, 23285, 19156, 31415, 27286, 6769, 2640,
    14899, 10770, 56317, 52188, 64447, 60318, 39801, 35672, 47931, 43802, 27814, 31879,
    19684, 23749, 11298, 15363, 3168, 7233, 60846, 64911, 52716, 56781, 44330, 48395,
    36200, 40265, 32407, 28342, 24277, 20212, 15891, 11826, 7761, 3696, 65439, 61374,
    57309, 53244, 48923, 44858, 40793, 36728, 37256, 33193, 45514, 41451, 53516, 49453,
    61774, 57711, 4224, 161, 12482, 8419, 20484, 16421, 28742, 24679, 33721, 37784, 41979,
    46042, 49981, 54044, 58239, 62302, 689, 4752, 8947, 13010, 16949, 21012, 25207, 29270,
    46570, 42443, 38312, 34185, 62830, 58703, 54572, 50445, 13538, 9411, 5280, 1153, 29798,
    25671, 21540, 17413, 42971, 47098, 34713, 38840, 59231, 63358, 50973, 55100, 9939,
    14066, 1681, 5808, 26199, 30326, 17941, 22068, 55628, 51565, 63758, 59695, 39368,
    35305, 47498, 43435, 22596, 18533, 30726, 26663, 6336, 2273, 14466, 10403, 52093,
    56156, 60223, 64286, 35833, 39896, 43963, 48026, 19061, 23124, 27191, 31254, 2801,
    6864, 10931, 14994, 64814, 60687, 56684, 52557, 48554, 44427, 40424, 36297, 31782,
    27655, 23652, 19525, 15522, 11395, 7392, 3265, 61215, 65342, 53085, 57212, 44955,
    49082, 36825, 40952, 28183, 32310, 20053, 24180, 11923, 16050, 3793, 7920
]


def crc16_ccitt(data: bytes) -> int:
    crc = 0
    for b in data:
        crc = (CRC16_TAB[((crc >> 8) ^ b) & 0xFF] ^ (crc << 8)) & 0xFFFF
    return crc


def encode_spp_message(
    msg_id: int,
    payload: bytes = b"",
    is_response: bool = False,
    is_fragment: bool = False,
) -> bytes:
    size = 1 + len(payload) + 2
    header = bytearray(struct.pack("<H", size))
    if is_fragment:
        header[1] |= 0x20
    if is_response:
        header[1] |= 0x10
    crc = crc16_ccitt(bytes([msg_id & 0xFF]) + payload)
    crc_bytes = struct.pack("<H", crc)
    return bytes([SOM]) + bytes(header) + bytes([msg_id & 0xFF]) + payload + crc_bytes + bytes([EOM])


@dataclass
class SppPacket:
    msg_id: int
    name: str
    is_request: bool
    is_fragment: bool
    payload: bytes
    direction: str = "RX"  # "RX" or "TX"
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3])

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "direction": self.direction,
            "msg_id": self.msg_id,
            "msg_hex": f"0x{self.msg_id:02X}",
            "name": self.name,
            "is_request": self.is_request,
            "is_fragment": self.is_fragment,
            "length": len(self.payload),
            "payload_hex": self.payload.hex(" "),
        }


def msg_id_name(mid: int) -> str:
    try:
        return MsgIds(mid).name
    except ValueError:
        return f"UNKNOWN_{mid}"


def decode_spp_stream(buf: bytearray) -> List[SppPacket]:
    packets: List[SppPacket] = []
    while len(buf) >= 7:
        if buf[0] != SOM:
            idx = buf.find(SOM, 1)
            if idx == -1:
                buf.clear()
                break
            del buf[:idx]
            continue
        header = struct.unpack("<H", buf[1:3])[0]
        is_frag = bool(header & 0x2000)
        is_req = bool(header & 0x1000)
        size = header & 0x03FF
        total = 1 + 2 + size + 1
        if size < 3 or total > 1030:
            del buf[0]
            continue
        if len(buf) < total:
            break
        raw = bytes(buf[:total])
        del buf[:total]
        if raw[-1] != EOM:
            continue
        mid = raw[3]
        payload = raw[4 : 4 + size - 3]
        packets.append(
            SppPacket(
                msg_id=mid,
                name=msg_id_name(mid),
                is_request=is_req,
                is_fragment=is_frag,
                payload=payload,
                direction="RX",
            )
        )
    return packets


@dataclass
class Buds4ProState:
    connected: bool = False
    device_mac: str = "FC:6E:83:4B:14:49"
    device_name: str = "Salman's Buds4 Pro"
    model_id: int = 13
    model_name: str = "Galaxy Buds4 Pro (SM-R640)"
    revision: int = 4

    # Battery & Charging
    battery_left: int = 0
    battery_right: int = 0
    battery_case: int = 0
    charging_left: bool = False
    charging_right: bool = False
    charging_case: bool = False
    is_coupled: bool = True
    main_connection: str = "Left"
    placement_left: int = 0
    placement_right: int = 0
    placement_left_name: str = "Disconnected"
    placement_right_name: str = "Disconnected"

    # Noise Control
    noise_control_mode: int = 1  # 0=Off, 1=ANC, 2=Ambient, 3=Adaptive
    noise_control_mode_name: str = "ANC (Active Noise Cancellation)"
    anc_level: int = 4  # 0..4 (Level 1..5)
    ambient_volume: int = 4  # 0..4 (Level 1..5)
    extra_high_ambient: bool = False
    noise_controls_with_one_earbud: bool = False

    # Customize Ambient Sound
    ambient_custom_enabled: bool = False
    ambient_custom_left: int = 2
    ambient_custom_right: int = 2
    ambient_custom_tone: int = 2  # 0..4 (Soft -> Clear)
    customize_conversation_boost: bool = False
    customize_anc_level: int = 0

    # Intelligent Audio / Detection
    detect_conversations: bool = True
    detect_conversations_duration: int = 0  # 0=5s, 1=10s, 2=15s
    siren_detect: bool = True
    adaptive_volume: bool = True
    auto_adjust_sound: bool = False
    adapt_sound_enabled: bool = True

    # Equalizer & Sound
    equalizer_mode: int = 0  # 0=Off, 1=BassBoost, 2=Soft, 3=Dynamic, 4=Clear, 5=TrebleBoost, 7=Custom
    equalizer_name: str = "Off (Balanced)"
    custom_eq_bands: List[int] = field(default_factory=lambda: [0] * 9)
    peq_mod: int = 1
    stereo_balance: int = 16  # 0..32 (16 = center)
    spatial_audio: bool = True
    spatial_head_tracking: bool = False
    gaming_mode: bool = False
    adjust_sound_sync: bool = False

    # Pinch, Swipe & Touch Controls
    touchpad_lock_all: bool = False
    single_pinch_on: bool = True
    double_pinch_on: bool = True
    triple_pinch_on: bool = True
    pinch_hold_on: bool = True
    double_pinch_call_on: bool = True
    pinch_hold_call_on: bool = True
    swipe_volume_on: bool = True
    touch_option_left: int = 2  # 1=Voice, 2=NoiseControl, 3=Volume, 4=Spotify
    touch_option_right: int = 2
    double_pinch_hold_advanced: int = 0
    outside_double_tap: bool = False

    # Pinch & Hold Noise Control Cycle Bitmask (Byte 21)
    # Right: bit0=Ambient, bit1=Adaptive, bit2=Off, bit3=ANC
    # Left:  bit4=Ambient, bit5=Adaptive, bit6=Off, bit7=ANC
    nc_cycle_right_ambient: bool = True
    nc_cycle_right_adaptive: bool = False
    nc_cycle_right_off: bool = False
    nc_cycle_right_anc: bool = True
    nc_cycle_left_ambient: bool = True
    nc_cycle_left_adaptive: bool = False
    nc_cycle_left_off: bool = False
    nc_cycle_left_anc: bool = True

    # Blade Lights & Voice
    lighting_control: int = 0  # 0=Blink, 1=Fade, 2=Steady
    bixby_wakeup: bool = False
    bixby_language: int = 3
    bixby_keyword: int = 0
    speak_seamlessly: bool = False
    hot_command_enabled: bool = False
    hot_command_language: int = 0
    hot_command_version: str = "1.1.0"

    # Call & Connection Features
    sidetone_enabled: bool = False
    extra_clear_call: bool = False
    call_path_control: bool = True
    seamless_connection: bool = True
    auto_pause_resume: bool = False
    neck_stretch_calibration: bool = False
    multipoint_supported: bool = True
    multipoint_state: int = 0
    streaming_mask: int = 0

    # Hardware, Firmware & Telemetry
    color_id: int = 359
    color_name: str = "Buds4 Pro Silver/Black (SM-R640)"
    sku_left: str = "SM-R640NZKAXAR"
    sku_right: str = "SM-R640NZKAXAR"
    fw_version_left: str = ""
    fw_version_right: str = ""
    fw_version_cradle: str = ""
    hw_version: str = ""
    touch_fw_version: str = ""
    serial_left: str = ""
    serial_right: str = ""
    serial_cradle: str = ""
    peer_bt_mac: str = ""
    temp_left_c: float = 0.0
    temp_right_c: float = 0.0
    vcell_mv: int = 0
    cycles_left: float = 0.0
    cycles_right: float = 0.0
    fit_test_left: str = "Not Run"
    fit_test_right: str = "Not Run"
    self_test_passed: Optional[bool] = None
    self_test_details: Dict[str, bool] = field(default_factory=dict)
    find_my_buds_active: bool = False
    mute_left: bool = False
    mute_right: bool = False
    buds4_extra_tail_hex: str = ""
    last_updated: str = ""


class _BluezProfile(dbus.service.Object):
    def __init__(self, bus: dbus.Bus, path: str, controller: "Buds4ProController"):
        super().__init__(bus, path)
        self.controller = controller

    @dbus.service.method("org.bluez.Profile1", in_signature="", out_signature="")
    def Release(self):
        self.controller._on_profile_release()

    @dbus.service.method("org.bluez.Profile1", in_signature="oha{sv}", out_signature="")
    def NewConnection(self, path, fd, properties):
        raw_fd = fd.take()
        self.controller._on_new_connection(str(path), raw_fd)

    @dbus.service.method("org.bluez.Profile1", in_signature="o", out_signature="")
    def RequestDisconnection(self, path):
        self.controller._on_request_disconnection(str(path))


class Buds4ProController:
    """Manages the BlueZ RFCOMM connection and Samsung SPP protocol for Buds4 Pro."""

    def __init__(self, mac_address: Optional[str] = None):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        self.state = Buds4ProState()
        if mac_address:
            self.state.device_mac = mac_address

        self.sock: Optional[socket.socket] = None
        self.rx_buf = bytearray()
        self.packet_log: List[dict] = []
        self.listeners: List[Callable[[Buds4ProState, Optional[SppPacket]], None]] = []
        self._lock = threading.Lock()
        self._io_watch_id: Optional[int] = None
        self._profile_registered = False
        self._profile = _BluezProfile(self.bus, PROFILE_PATH, self)
        self.bus.add_signal_receiver(
            self._on_bluez_properties_changed,
            signal_name="PropertiesChanged",
            dbus_interface="org.freedesktop.DBus.Properties",
            bus_name="org.bluez",
            path_keyword="path",
        )

    def _on_bluez_properties_changed(self, interface, changed, invalidated, path=None):
        if interface != "org.bluez.Device1":
            return
        expected_suffix = "dev_" + self.state.device_mac.replace(":", "_")
        if path and expected_suffix in str(path):
            if "Connected" in changed:
                if bool(changed["Connected"]) and not self.state.connected:
                    GLib.timeout_add(400, lambda: (self.connect(), False)[1])
                elif not bool(changed["Connected"]):
                    self.state.connected = False
                    self._notify()

    def add_listener(self, cb: Callable[[Buds4ProState, Optional[SppPacket]], None]):
        self.listeners.append(cb)

    def _notify(self, pkt: Optional[SppPacket] = None):
        self.state.last_updated = datetime.datetime.now().strftime("%H:%M:%S")
        for cb in list(self.listeners):
            try:
                cb(self.state, pkt)
            except Exception as e:
                print(f"[Buds4Pro] Listener error: {e}")

    def discover_buds(self) -> Tuple[str, str]:
        """Find paired Samsung Buds4 Pro (or any Galaxy Buds) via BlueZ ObjectManager."""
        om = dbus.Interface(self.bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
        objects = om.GetManagedObjects()
        for path, ifaces in objects.items():
            dev = ifaces.get("org.bluez.Device1")
            if not dev:
                continue
            name = str(dev.get("Name", dev.get("Alias", "")))
            addr = str(dev.get("Address", ""))
            uuids = [str(u).lower() for u in dev.get("UUIDs", [])]
            if SPP_UUID in uuids or "buds" in name.lower():
                self.state.device_mac = addr
                self.state.device_name = name
                return addr, name
        return self.state.device_mac, self.state.device_name

    def connect(self, callback: Optional[Callable[[bool, str], None]] = None):
        """Register BlueZ SPP profile and connect to the earbuds asynchronously."""
        mac, name = self.discover_buds()
        dev_path = "/org/bluez/hci0/dev_" + mac.replace(":", "_")
        pm = dbus.Interface(self.bus.get_object("org.bluez", "/org/bluez"), "org.bluez.ProfileManager1")
        try:
            dev_obj = self.bus.get_object("org.bluez", dev_path)
            dev = dbus.Interface(dev_obj, "org.bluez.Device1")
            props = dbus.Interface(dev_obj, "org.freedesktop.DBus.Properties")
        except Exception as e:
            if callback:
                callback(False, f"Device {mac} not found on BlueZ: {e}")
            return

        if not self._profile_registered:
            try:
                pm.UnregisterProfile(PROFILE_PATH)
            except Exception:
                pass
            opts = {
                "Role": dbus.String("client"),
                "Service": dbus.String(SPP_UUID),
                "Name": dbus.String("SamsungBuds4ProStudio"),
            }
            try:
                pm.RegisterProfile(PROFILE_PATH, SPP_UUID, opts)
                self._profile_registered = True
            except Exception as e:
                if "AlreadyExists" not in str(e) and "already registered" not in str(e):
                    if callback:
                        callback(False, f"RegisterProfile failed: {e}")
                    return
                self._profile_registered = True

        # Ensure basic Bluetooth link is connected first
        try:
            is_conn = bool(props.Get("org.bluez.Device1", "Connected"))
        except Exception:
            is_conn = False

        def do_connect_profile(attempt: int = 1):
            def on_profile_err(e):
                err_str = str(e)
                if "AlreadyConnected" in err_str:
                    if callback:
                        callback(True, f"Already connected to {name} ({mac})")
                    return
                if attempt < 6 and ("InProgress" in err_str or "Failed" in err_str or "busy" in err_str):
                    GLib.timeout_add(500, lambda: (do_connect_profile(attempt + 1), False)[1])
                    return
                if callback:
                    callback(False, f"ConnectProfile error: {e}")

            dev.ConnectProfile(
                SPP_UUID,
                reply_handler=lambda: callback(True, f"Connected to {name} ({mac})") if callback else None,
                error_handler=on_profile_err,
            )

        def do_basic_connect(attempt: int = 1):
            def on_conn_err(e):
                err_str = str(e)
                if "AlreadyConnected" in err_str:
                    do_connect_profile()
                    return
                if attempt < 6 and ("InProgress" in err_str or "busy" in err_str):
                    GLib.timeout_add(500, lambda: (do_basic_connect(attempt + 1), False)[1])
                    return
                if callback:
                    callback(False, f"Bluetooth Connect failed: {e}")

            dev.Connect(
                reply_handler=lambda: do_connect_profile(),
                error_handler=on_conn_err,
            )

        if not is_conn:
            do_basic_connect()
        else:
            do_connect_profile()

    def disconnect(self, bluetooth: bool = True):
        """Disconnect the SPP control channel and optionally the full Bluetooth link."""
        mac = self.state.device_mac
        dev_path = "/org/bluez/hci0/dev_" + mac.replace(":", "_")
        if self._io_watch_id is not None:
            GLib.source_remove(self._io_watch_id)
            self._io_watch_id = None
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        try:
            dev = dbus.Interface(self.bus.get_object("org.bluez", dev_path), "org.bluez.Device1")
            dev.DisconnectProfile(
                SPP_UUID,
                reply_handler=lambda: None,
                error_handler=lambda _: None,
            )
            if bluetooth:
                dev.Disconnect(
                    reply_handler=lambda: None,
                    error_handler=lambda _: None,
                )
        except Exception:
            pass
        self.state.connected = False
        self._notify()

    def _on_profile_release(self):
        self.state.connected = False
        self._notify()

    def _on_request_disconnection(self, path: str):
        self.disconnect(bluetooth=False)

    def _on_new_connection(self, path: str, raw_fd: int):
        if self._io_watch_id is not None:
            GLib.source_remove(self._io_watch_id)
            self._io_watch_id = None
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = socket.fromfd(raw_fd, socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        os.close(raw_fd)
        self.sock.setblocking(False)
        self.state.connected = True
        self._io_watch_id = GLib.io_add_watch(
            self.sock.fileno(),
            GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR,
            self._on_socket_Readable,
        )
        self._notify()
        GLib.timeout_add(250, self._send_initial_handshake)

    def _send_initial_handshake(self) -> bool:
        if not self.state.connected:
            return False
        # Handshake as Samsung Android 14 device + query all diagnostic / hardware metadata
        self.send_message(MsgIds.MANAGER_INFO, bytes([1, 1, 34]))
        self.request_telemetry_refresh()
        return False

    def request_telemetry_refresh(self):
        for mid in (
            MsgIds.DEBUG_GET_ALL_DATA,
            MsgIds.DEBUG_SKU,
            MsgIds.DEBUG_SERIAL_NUMBER,
            MsgIds.CRADLE_SERIAL_NUMBER,
            MsgIds.CUSTOM_EQUALIZE_RECV,
            MsgIds.MULTIPOINT_INFO,
            MsgIds.SOC_BATTERY_CYCLE,
        ):
            self.send_message(mid, b"")

    def _on_socket_Readable(self, fd: int, condition: int) -> bool:
        if condition & (GLib.IO_HUP | GLib.IO_ERR):
            self.state.connected = False
            self.sock = None
            self._io_watch_id = None
            self._notify()
            return False
        if not self.sock:
            return False
        try:
            data = self.sock.recv(4096)
            if not data:
                self.state.connected = False
                self._notify()
                return False
            self.rx_buf.extend(data)
            for pkt in decode_spp_stream(self.rx_buf):
                self._record_packet(pkt)
                self._handle_packet(pkt)
                self._notify(pkt)
        except BlockingIOError:
            pass
        except Exception as e:
            print(f"[Buds4Pro] Socket read error: {e}")
            self.state.connected = False
            self._notify()
            return False
        return True

    def _record_packet(self, pkt: SppPacket):
        with self._lock:
            self.packet_log.append(pkt.to_dict())
            if len(self.packet_log) > 250:
                del self.packet_log[:-250]

    def send_message(self, msg_id: int, payload: bytes = b"", is_response: bool = False) -> bool:
        if not self.sock or not self.state.connected:
            return False
        raw = encode_spp_message(int(msg_id), payload, is_response=is_response)
        try:
            self.sock.sendall(raw)
            pkt = SppPacket(
                msg_id=int(msg_id),
                name=msg_id_name(int(msg_id)),
                is_request=not is_response,
                is_fragment=False,
                payload=payload,
                direction="TX",
            )
            self._record_packet(pkt)
            self._notify(pkt)
            return True
        except Exception as e:
            print(f"[Buds4Pro] Send error: {e}")
            return False

    # =========================================================================
    # Incoming Packet Decoders (Reverse-Engineered for Galaxy Buds4 Pro SM-R640)
    # =========================================================================
    def _handle_packet(self, pkt: SppPacket):
        pl = pkt.payload
        mid = pkt.msg_id

        if mid == MsgIds.EXTENDED_STATUS_UPDATED and len(pl) >= 35:
            self._decode_extended_status(pl)
        elif mid == MsgIds.STATUS_UPDATED and len(pl) >= 7:
            self._decode_basic_status(pl)
        elif mid == MsgIds.NOISE_CONTROLS_UPDATE and len(pl) >= 1:
            self.state.noise_control_mode = pl[0]
            self.state.noise_control_mode_name = self._nc_mode_label(pl[0])
            # Re-apply custom EQ if active (Buds4 Pro firmware drops custom EQ table on NC switch)
            if self.state.equalizer_mode == 7:
                self.set_custom_equalizer(self.state.custom_eq_bands)
        elif mid == MsgIds.VERSION_INFO_LONG and len(pl) >= 42:
            hw_l = f"rev{(pl[0] >> 4):X}.{pl[0] & 0x0F:X}"
            self.state.hw_version = hw_l
            self.state.fw_version_left = pl[2:22].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
            self.state.fw_version_right = pl[22:42].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
        elif mid == MsgIds.CRADLE_SERIAL_NUMBER and len(pl) >= 24:
            # Buds4 Pro uses 13-byte null-padded FW string + 14-byte null-padded serial number
            self.state.fw_version_cradle = pl[0:13].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
            self.state.serial_cradle = pl[13:27].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
        elif mid == MsgIds.DEBUG_SKU and len(pl) >= 28:
            self.state.sku_left = pl[0:14].decode("ascii", errors="ignore").strip("\x00")
            self.state.sku_right = pl[14:28].decode("ascii", errors="ignore").strip("\x00")
        elif mid == MsgIds.DEBUG_SERIAL_NUMBER and len(pl) >= 22:
            self.state.serial_left = pl[0:11].decode("ascii", errors="ignore").strip("\x00")
            self.state.serial_right = pl[11:22].decode("ascii", errors="ignore").strip("\x00")
        elif mid == MsgIds.DEBUG_GET_ALL_DATA and len(pl) >= 98:
            self._decode_debug_all_data(pl)
        elif mid == MsgIds.SOC_BATTERY_CYCLE and len(pl) >= 16:
            left_raw = int.from_bytes(pl[0:8], "big", signed=False)
            right_raw = int.from_bytes(pl[8:16], "big", signed=False)
            self.state.cycles_left = round(left_raw / 10000.0, 2)
            self.state.cycles_right = round(right_raw / 10000.0, 2)
        elif mid == MsgIds.MULTIPOINT_INFO and len(pl) >= 5:
            self.state.multipoint_supported = pl[1] == 1
            self.state.multipoint_state = pl[2]
            self.state.streaming_mask = pl[4]
        elif mid == MsgIds.TELEMETRY_PERIODIC_244 and len(pl) >= 42:
            # Buds4 Pro periodic sensor/voltage telemetry frame (0xF4)
            vcell = int.from_bytes(pl[34:38], "little", signed=False)
            if 2500 <= vcell <= 5500:
                self.state.vcell_mv = vcell
        elif mid == MsgIds.CHECK_THE_FIT_OF_EARBUDS_RESULT and len(pl) >= 2:
            fit_map = {0: "Poor Seal (Adjust Earbud)", 1: "Good Fit", 2: "Test Failed"}
            self.state.fit_test_left = fit_map.get(pl[0], f"Code {pl[0]}")
            self.state.fit_test_right = fit_map.get(pl[1], f"Code {pl[1]}")
        elif mid == MsgIds.SELF_TEST and len(pl) >= 4:
            self._decode_self_test(pl)
        elif mid == MsgIds.MUTE_EARBUD_STATUS_UPDATED and len(pl) >= 2:
            self.state.mute_left = bool(pl[0])
            self.state.mute_right = bool(pl[1])
        elif mid == MsgIds.FIND_MY_EARBUDS_STOP:
            self.state.find_my_buds_active = False
        elif mid == MsgIds.UNIVERSAL_MSG_ID_ACKNOWLEDGEMENT and len(pl) >= 1:
            self._decode_ack(pl)

    def _decode_basic_status(self, pl: bytes):
        self.state.revision = pl[0]
        self.state.battery_left = pl[1]
        self.state.battery_right = pl[2]
        self.state.is_coupled = bool(pl[3])
        self.state.main_connection = "Left" if pl[4] == 1 else "Right"
        self.state.placement_left = (pl[5] & 0xF0) >> 4
        self.state.placement_right = pl[5] & 0x0F
        self.state.battery_case = pl[6]
        if len(pl) >= 8:
            chg = pl[7]
            self.state.charging_left = bool(chg & 0x10)
            self.state.charging_right = bool(chg & 0x04)
            self.state.charging_case = bool(chg & 0x01)
        self.state.placement_left_name = PLACEMENT_NAMES.get(self.state.placement_left, "Unknown")
        self.state.placement_right_name = PLACEMENT_NAMES.get(self.state.placement_right, "Unknown")

    def _decode_extended_status(self, pl: bytes):
        s = self.state
        s.revision = pl[0]
        s.model_id = pl[1]
        s.battery_left = pl[2]
        s.battery_right = pl[3]
        s.is_coupled = bool(pl[4])
        s.main_connection = "Left" if pl[5] == 1 else "Right"
        s.placement_left = (pl[6] & 0xF0) >> 4
        s.placement_right = pl[6] & 0x0F
        s.placement_left_name = PLACEMENT_NAMES.get(s.placement_left, "Unknown")
        s.placement_right_name = PLACEMENT_NAMES.get(s.placement_right, "Unknown")
        s.battery_case = pl[7]
        s.adjust_sound_sync = pl[8] == 1
        s.equalizer_mode = pl[9]
        s.equalizer_name = EQ_PRESET_NAMES.get(s.equalizer_mode, f"Preset {s.equalizer_mode}")

        # Byte 10: Advanced Touchpad Lock bitmask
        b10 = pl[10]
        s.pinch_hold_on = bool(b10 & (1 << 0))
        s.triple_pinch_on = bool(b10 & (1 << 1))
        s.double_pinch_on = bool(b10 & (1 << 2))
        s.single_pinch_on = bool(b10 & (1 << 3))
        s.double_pinch_call_on = bool(b10 & (1 << 4))
        s.pinch_hold_call_on = bool(b10 & (1 << 5))
        s.swipe_volume_on = bool(b10 & (1 << 6))
        s.touchpad_lock_all = not bool(b10 & (1 << 7))

        # Byte 11: Left/Right Pinch & Hold Action
        s.touch_option_left = (pl[11] & 0xF0) >> 4
        s.touch_option_right = pl[11] & 0x0F

        # Byte 12: Noise Control Mode (0=Off, 1=ANC, 2=Ambient, 3=Adaptive)
        s.noise_control_mode = pl[12]
        s.noise_control_mode_name = self._nc_mode_label(pl[12])

        # Byte 13: Bixby Voice Wake-up
        s.bixby_wakeup = pl[13] == 1

        # Bytes 14..17: Device Color IDs
        color_l = struct.unpack("<H", pl[14:16])[0]
        color_r = struct.unpack("<H", pl[16:18])[0]
        s.color_id = color_r if color_r else color_l
        s.color_name = DEVICE_COLOR_NAMES.get(s.color_id, f"Model Color #{s.color_id}")

        s.bixby_language = pl[18]
        s.seamless_connection = pl[19] == 0

        # Byte 21: Pinch & Hold Noise Control Cycle Bitmask
        b21 = pl[21]
        s.nc_cycle_right_ambient = bool(b21 & (1 << 0))
        s.nc_cycle_right_adaptive = bool(b21 & (1 << 1))
        s.nc_cycle_right_off = bool(b21 & (1 << 2))
        s.nc_cycle_right_anc = bool(b21 & (1 << 3))
        s.nc_cycle_left_ambient = bool(b21 & (1 << 4))
        s.nc_cycle_left_adaptive = bool(b21 & (1 << 5))
        s.nc_cycle_left_off = bool(b21 & (1 << 6))
        s.nc_cycle_left_anc = bool(b21 & (1 << 7))

        s.speak_seamlessly = pl[22] == 1
        s.ambient_volume = pl[23]
        s.anc_level = pl[24]
        s.stereo_balance = pl[25]
        s.detect_conversations = pl[26] == 1
        s.detect_conversations_duration = pl[27] if pl[27] <= 2 else 1
        s.noise_controls_with_one_earbud = pl[28] == 1
        s.ambient_custom_enabled = pl[29] == 1
        s.ambient_custom_left = (pl[30] & 0xF0) >> 4
        s.ambient_custom_right = pl[30] & 0x0F
        s.ambient_custom_tone = pl[31]
        s.outside_double_tap = pl[32] == 1
        s.sidetone_enabled = pl[33] == 1
        s.call_path_control = pl[34] == 0

        if len(pl) >= 46:
            s.spatial_audio = bool(pl[35])
            s.customize_conversation_boost = bool(pl[36])
            s.customize_anc_level = pl[37]
            s.neck_stretch_calibration = bool(pl[38])
            s.bixby_keyword = pl[39]
            s.auto_adjust_sound = pl[40] not in (0, 1)
            s.spatial_head_tracking = bool(pl[41])
            chg = pl[42]
            s.charging_left = bool(chg & 0x10)
            s.charging_right = bool(chg & 0x04)
            s.charging_case = bool(chg & 0x01)
            s.extra_clear_call = bool(pl[43])
            s.extra_high_ambient = bool(pl[44])
            s.auto_pause_resume = bool(pl[45])

        if len(pl) >= 54:
            s.hot_command_enabled = bool(pl[46])
            s.hot_command_language = pl[47]
            s.peq_mod = pl[48]
            s.adaptive_volume = bool(pl[49])
            s.lighting_control = pl[50]
            s.double_pinch_hold_advanced = pl[51]
            s.siren_detect = bool(pl[52])
            s.adapt_sound_enabled = bool(pl[53])

        if len(pl) >= 57:
            s.hot_command_version = f"{pl[54]}.{pl[55]}.{pl[56]}"
        if len(pl) > 57:
            s.buds4_extra_tail_hex = pl[57:].hex(" ")

    def _decode_debug_all_data(self, pl: bytes):
        hw1 = (pl[1] & 0xF0) >> 4
        hw2 = pl[1] & 0x0F
        self.state.hw_version = f"rev{hw1:X}.{hw2:X}"
        sw_str = pl[2:22].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
        if sw_str:
            self.state.fw_version_left = sw_str
            self.state.fw_version_right = sw_str
        self.state.touch_fw_version = f"0x{pl[22]:02X}"
        self.state.peer_bt_mac = ":".join(f"{b:02X}" for b in pl[23:29])
        t_left = struct.unpack("<h", pl[55:57])[0] * 0.1
        t_right = struct.unpack("<h", pl[57:59])[0] * 0.1
        if 0 < t_left < 80:
            self.state.temp_left_c = round(t_left, 1)
        if 0 < t_right < 80:
            self.state.temp_right_c = round(t_right, 1)

    def _decode_self_test(self, pl: bytes):
        bits = struct.unpack("<I", pl[:4])[0]
        checks = {
            "Hardware Version": (bits & (1 << 0)) == 0,
            "Software Version": (bits & (1 << 1)) == 0,
            "Touch Firmware": (bits & (1 << 2)) == 0,
            "Left Serial Number": (bits & (1 << 3)) == 0,
            "Right Serial Number": (bits & (1 << 4)) == 0,
            "Left BT Address": (bits & (1 << 5)) == 0,
            "Right BT Address": (bits & (1 << 6)) == 0,
            "Left Accelerometer": (bits & (0b111 << 7)) == 0,
            "Right Accelerometer": (bits & (0b111 << 10)) == 0,
            "Left Proximity": (bits & (1 << 13)) == 0,
            "Right Proximity": (bits & (1 << 14)) == 0,
            "Left Thermistor": (bits & (1 << 15)) == 0,
            "Right Thermistor": (bits & (1 << 16)) == 0,
            "Left Battery ADC": (bits & (0b111 << 17)) == 0,
            "Right Battery ADC": (bits & (0b111 << 20)) == 0,
            "Left Hall Sensor": (bits & (1 << 23)) == 0,
            "Right Hall Sensor": (bits & (1 << 24)) == 0,
        }
        self.state.self_test_details = checks
        self.state.self_test_passed = all(checks.values())

    def _decode_ack(self, pl: bytes):
        ack_id = pl[0]
        val = pl[1] if len(pl) > 1 else 0
        if ack_id == MsgIds.NOISE_CONTROLS:
            self.state.noise_control_mode = val
            self.state.noise_control_mode_name = self._nc_mode_label(val)
        elif ack_id == MsgIds.NOISE_REDUCTION_LEVEL:
            self.state.anc_level = val
        elif ack_id == MsgIds.AMBIENT_VOLUME:
            self.state.ambient_volume = val
        elif ack_id == MsgIds.EQUALIZER:
            self.state.equalizer_mode = val
            self.state.equalizer_name = EQ_PRESET_NAMES.get(val, f"Preset {val}")
        elif ack_id == MsgIds.SET_DETECT_CONVERSATIONS:
            self.state.detect_conversations = bool(val)
        elif ack_id == MsgIds.SET_DETECT_CONVERSATIONS_DURATION:
            self.state.detect_conversations_duration = val
        elif ack_id == MsgIds.SET_ANC_WITH_ONE_EARBUD:
            self.state.noise_controls_with_one_earbud = bool(val)
        elif ack_id == MsgIds.EXTRA_CLEAR_SOUND_CALL:
            self.state.extra_clear_call = bool(val)
        elif ack_id == MsgIds.SET_SIDETONE:
            self.state.sidetone_enabled = bool(val)
        elif ack_id == MsgIds.EXTRA_HIGH_AMBIENT:
            self.state.extra_high_ambient = bool(val)
        elif ack_id == MsgIds.SET_VOICE_WAKE_UP:
            self.state.bixby_wakeup = bool(val)
        elif ack_id == MsgIds.SET_SPEAK_SEAMLESSLY:
            self.state.speak_seamlessly = bool(val)
        elif ack_id == MsgIds.SET_SEAMLESS_CONNECTION:
            self.state.seamless_connection = (val == 0)
        elif ack_id == MsgIds.SET_CALL_PATH_CONTROL:
            self.state.call_path_control = (val == 0)
        elif ack_id == MsgIds.ADJUST_SOUND_SYNC:
            self.state.adjust_sound_sync = bool(val)

    @staticmethod
    def _nc_mode_label(mode: int) -> str:
        return {
            0: "Off",
            1: "ANC (Active Noise Cancellation)",
            2: "Ambient Sound",
            3: "Adaptive Noise Control",
        }.get(mode, f"Mode {mode}")

    # =========================================================================
    # High-Level Feature Control Commands
    # =========================================================================
    def set_noise_control(self, mode: int) -> bool:
        """0=Off, 1=ANC, 2=Ambient Sound, 3=Adaptive"""
        mode = int(mode) & 0xFF
        self.state.noise_control_mode = mode
        self.state.noise_control_mode_name = self._nc_mode_label(mode)
        return self.send_message(MsgIds.NOISE_CONTROLS, bytes([mode]))

    def set_anc_level(self, level: int) -> bool:
        """Buds4 Pro 5-step ANC level: 0..4 (Level 1..5)"""
        level = max(0, min(4, int(level)))
        self.state.anc_level = level
        return self.send_message(MsgIds.NOISE_REDUCTION_LEVEL, bytes([level]))

    def set_ambient_volume(self, volume: int) -> bool:
        """Buds4 Pro 5-step Ambient volume: 0..4 (Level 1..5)"""
        volume = max(0, min(4, int(volume)))
        self.state.ambient_volume = volume
        return self.send_message(MsgIds.AMBIENT_VOLUME, bytes([volume]))

    def set_extra_high_ambient(self, enabled: bool) -> bool:
        self.state.extra_high_ambient = bool(enabled)
        return self.send_message(MsgIds.EXTRA_HIGH_AMBIENT, bytes([1 if enabled else 0]))

    def set_customize_ambient(self, enabled: bool, left_vol: int, right_vol: int, tone: int) -> bool:
        left_vol = max(0, min(4, int(left_vol)))
        right_vol = max(0, min(4, int(right_vol)))
        tone = max(0, min(4, int(tone)))
        self.state.ambient_custom_enabled = bool(enabled)
        self.state.ambient_custom_left = left_vol
        self.state.ambient_custom_right = right_vol
        self.state.ambient_custom_tone = tone
        return self.send_message(
            MsgIds.CUSTOMIZE_AMBIENT_SOUND,
            bytes([1 if enabled else 0, left_vol, right_vol, tone]),
        )

    def set_conversation_detect(self, enabled: bool) -> bool:
        self.state.detect_conversations = bool(enabled)
        return self.send_message(MsgIds.SET_DETECT_CONVERSATIONS, bytes([1 if enabled else 0]))

    def set_conversation_detect_duration(self, duration_idx: int) -> bool:
        """0 = 5s, 1 = 10s, 2 = 15s"""
        duration_idx = max(0, min(2, int(duration_idx)))
        self.state.detect_conversations_duration = duration_idx
        return self.send_message(MsgIds.SET_DETECT_CONVERSATIONS_DURATION, bytes([duration_idx]))

    def set_siren_detect(self, enabled: bool) -> bool:
        self.state.siren_detect = bool(enabled)
        return self.send_message(MsgIds.UASC_SIREN_DETECT, bytes([1 if enabled else 0]))

    def set_adaptive_volume(self, enabled: bool) -> bool:
        self.state.adaptive_volume = bool(enabled)
        return self.send_message(MsgIds.SET_ADAPTIVE_VOLUME_ENABLED, bytes([1 if enabled else 0]))

    def set_noise_controls_one_earbud(self, enabled: bool) -> bool:
        self.state.noise_controls_with_one_earbud = bool(enabled)
        return self.send_message(MsgIds.SET_ANC_WITH_ONE_EARBUD, bytes([1 if enabled else 0]))

    def set_equalizer_preset(self, mode: int) -> bool:
        """0=Off, 1=BassBoost, 2=Soft, 3=Dynamic, 4=Clear, 5=TrebleBoost, 7=Custom"""
        mode = int(mode)
        self.state.equalizer_mode = mode
        self.state.equalizer_name = EQ_PRESET_NAMES.get(mode, f"Preset {mode}")
        if mode == 7:
            return self.set_custom_equalizer(self.state.custom_eq_bands)
        return self.send_message(MsgIds.EQUALIZER, bytes([mode & 0xFF]))

    def set_custom_equalizer(self, bands: List[int]) -> bool:
        """9-band signed gains [-10..+10]"""
        cleaned = [max(-10, min(10, int(x))) for x in (bands + [0] * 9)[:9]]
        self.state.custom_eq_bands = cleaned
        self.state.equalizer_mode = 7
        self.state.equalizer_name = EQ_PRESET_NAMES[7]
        payload = bytes([9]) + bytes((b & 0xFF) for b in cleaned)
        self.send_message(MsgIds.CUSTOM_EQUALIZE_SEND, payload)
        return self.send_message(MsgIds.EQUALIZER, bytes([7]))

    def set_stereo_balance(self, value: int) -> bool:
        """0 (Full Left) .. 16 (Center) .. 32 (Full Right)"""
        value = max(0, min(32, int(value)))
        self.state.stereo_balance = value
        return self.send_message(MsgIds.SET_HEARING_ENHANCEMENTS, bytes([value]))

    def set_spatial_audio(self, enabled: bool, head_tracking: bool = False) -> bool:
        self.state.spatial_audio = bool(enabled)
        self.state.spatial_head_tracking = bool(head_tracking)
        ok = self.send_message(MsgIds.SET_SPATIAL_AUDIO, bytes([1 if enabled else 0]))
        if enabled and head_tracking:
            self.send_message(MsgIds.SPATIAL_AUDIO_CONTROL, bytes([0]))  # Attach
        else:
            self.send_message(MsgIds.SPATIAL_AUDIO_CONTROL, bytes([1]))  # Detach
        return ok

    def set_gaming_mode(self, enabled: bool) -> bool:
        self.state.gaming_mode = bool(enabled)
        self.state.adjust_sound_sync = bool(enabled)
        self.send_message(MsgIds.GAME_MODE, bytes([1 if enabled else 0]))
        return self.send_message(MsgIds.ADJUST_SOUND_SYNC, bytes([1 if enabled else 0]))

    def set_touchpad_gestures(
        self,
        lock_all: bool,
        single_pinch: bool,
        double_pinch: bool,
        triple_pinch: bool,
        pinch_hold: bool,
        double_pinch_call: bool,
        pinch_hold_call: bool,
    ) -> bool:
        self.state.touchpad_lock_all = bool(lock_all)
        self.state.single_pinch_on = bool(single_pinch)
        self.state.double_pinch_on = bool(double_pinch)
        self.state.triple_pinch_on = bool(triple_pinch)
        self.state.pinch_hold_on = bool(pinch_hold)
        self.state.double_pinch_call_on = bool(double_pinch_call)
        self.state.pinch_hold_call_on = bool(pinch_hold_call)
        payload = bytes([
            0 if lock_all else 1,
            1 if single_pinch else 0,
            1 if double_pinch else 0,
            1 if triple_pinch else 0,
            1 if pinch_hold else 0,
            1 if double_pinch_call else 0,
            1 if pinch_hold_call else 0,
        ])
        return self.send_message(MsgIds.LOCK_TOUCHPAD, payload)

    def set_touchpad_options(self, left_option: int, right_option: int) -> bool:
        """1=VoiceAssistant, 2=NoiseControl, 3=Volume, 4=Spotify, 5=OtherL, 6=OtherR"""
        self.state.touch_option_left = int(left_option)
        self.state.touch_option_right = int(right_option)
        return self.send_message(
            MsgIds.SET_TOUCHPAD_OPTION,
            bytes([int(left_option) & 0xFF, int(right_option) & 0xFF]),
        )

    def set_pinch_hold_nc_cycle(
        self,
        left_anc: bool,
        left_ambient: bool,
        left_adaptive: bool,
        left_off: bool,
        right_anc: bool,
        right_ambient: bool,
        right_adaptive: bool,
        right_off: bool,
    ) -> bool:
        """Buds3/Buds4 dual-side bitmask: bit0=Ambient, bit1=Adaptive, bit2=Off, bit3=ANC"""
        self.state.nc_cycle_left_anc = left_anc
        self.state.nc_cycle_left_ambient = left_ambient
        self.state.nc_cycle_left_adaptive = left_adaptive
        self.state.nc_cycle_left_off = left_off
        self.state.nc_cycle_right_anc = right_anc
        self.state.nc_cycle_right_ambient = right_ambient
        self.state.nc_cycle_right_adaptive = right_adaptive
        self.state.nc_cycle_right_off = right_off

        left_mask = (
            (1 if left_ambient else 0)
            | (2 if left_adaptive else 0)
            | (4 if left_off else 0)
            | (8 if left_anc else 0)
        )
        right_mask = (
            (1 if right_ambient else 0)
            | (2 if right_adaptive else 0)
            | (4 if right_off else 0)
            | (8 if right_anc else 0)
        )
        return self.send_message(
            MsgIds.SET_TOUCH_AND_HOLD_NOISE_CONTROLS,
            bytes([left_mask, right_mask]),
        )

    def set_lighting_mode(self, mode: int) -> bool:
        """Blade lights style: 0=Blink, 1=Fade In/Out, 2=Steady"""
        mode = max(0, min(2, int(mode)))
        self.state.lighting_control = mode
        return self.send_message(MsgIds.BUDS_LIGHTING_SYNC, bytes([mode]))

    def set_bixby_wakeup(self, enabled: bool) -> bool:
        self.state.bixby_wakeup = bool(enabled)
        return self.send_message(MsgIds.SET_VOICE_WAKE_UP, bytes([1 if enabled else 0]))

    def set_bixby_language(self, lang_id: int) -> bool:
        self.state.bixby_language = int(lang_id) & 0xFF
        return self.send_message(MsgIds.VOICE_WAKE_UP_LANGUAGE, bytes([self.state.bixby_language]))

    def set_speak_seamlessly(self, enabled: bool) -> bool:
        self.state.speak_seamlessly = bool(enabled)
        return self.send_message(MsgIds.SET_SPEAK_SEAMLESSLY, bytes([1 if enabled else 0]))

    def set_hot_command(self, enabled: bool) -> bool:
        self.state.hot_command_enabled = bool(enabled)
        return self.send_message(MsgIds.SET_HOT_COMMAND, bytes([1 if enabled else 0]))

    def set_sidetone(self, enabled: bool) -> bool:
        self.state.sidetone_enabled = bool(enabled)
        return self.send_message(MsgIds.SET_SIDETONE, bytes([1 if enabled else 0]))

    def set_extra_clear_call(self, enabled: bool) -> bool:
        self.state.extra_clear_call = bool(enabled)
        return self.send_message(MsgIds.EXTRA_CLEAR_SOUND_CALL, bytes([1 if enabled else 0]))

    def set_auto_pause_resume(self, enabled: bool) -> bool:
        self.state.auto_pause_resume = bool(enabled)
        return self.send_message(MsgIds.PAUSE_MEDIA_WHEN_ONE_BUD_REMOVED, bytes([1 if enabled else 0]))

    def set_seamless_connection(self, enabled: bool) -> bool:
        """Note: wire protocol uses inverted boolean (0 = Enabled, 1 = Disabled)"""
        self.state.seamless_connection = bool(enabled)
        return self.send_message(MsgIds.SET_SEAMLESS_CONNECTION, bytes([0 if enabled else 1]))

    def set_call_path_control(self, enabled: bool) -> bool:
        """Note: wire protocol uses inverted boolean (0 = Enabled, 1 = Disabled)"""
        self.state.call_path_control = bool(enabled)
        return self.send_message(MsgIds.SET_CALL_PATH_CONTROL, bytes([0 if enabled else 1]))

    def set_in_band_ringtone(self, enabled: bool) -> bool:
        return self.send_message(MsgIds.SET_IN_BAND_RINGTONE, bytes([1 if enabled else 0]))

    def set_neck_posture_reminder(self, enabled: bool) -> bool:
        self.state.neck_stretch_calibration = bool(enabled)
        return self.send_message(MsgIds.NECK_POSTURE_SET, bytes([1 if enabled else 0]))

    def set_find_my_buds(self, active: bool, ring_while_wearing: bool = False) -> bool:
        self.state.find_my_buds_active = bool(active)
        if active:
            mid = MsgIds.FIND_MY_EARBUDS_ON_WEARING_START if ring_while_wearing else MsgIds.FIND_MY_EARBUDS_START
            return self.send_message(mid, b"")
        return self.send_message(MsgIds.FIND_MY_EARBUDS_STOP, b"")

    def set_find_my_buds_mute(self, mute_left: bool, mute_right: bool) -> bool:
        self.state.mute_left = bool(mute_left)
        self.state.mute_right = bool(mute_right)
        return self.send_message(
            MsgIds.MUTE_EARBUD,
            bytes([1 if mute_left else 0, 1 if mute_right else 0]),
        )

    def run_fit_test(self, start: bool = True) -> bool:
        if start:
            self.state.fit_test_left = "Testing..."
            self.state.fit_test_right = "Testing..."
        return self.send_message(MsgIds.CHECK_THE_FIT_OF_EARBUDS, bytes([1 if start else 0]))

    def run_self_test(self) -> bool:
        return self.send_message(MsgIds.SELF_TEST, b"")

    def start_pairing_mode(self) -> bool:
        return self.send_message(MsgIds.PAIRING_MODE, b"")

    def sync_time(self) -> bool:
        now_ms = int(time.time() * 1000)
        utc_offset_ms = int((datetime.datetime.now().astimezone().utcoffset() or datetime.timedelta()).total_seconds() * 1000)
        payload = struct.pack("<qi", now_ms, utc_offset_ms)
        return self.send_message(MsgIds.UPDATE_TIME, payload)

    def reboot_buds(self) -> bool:
        return self.send_message(MsgIds.REBOOT, b"")

    def factory_reset(self) -> bool:
        return self.send_message(MsgIds.RESET, b"")

    def to_dict(self) -> dict:
        return asdict(self.state)
