# Samsung Galaxy Buds4 Pro Studio (`SM-R640`)

[![Platform](https://img.shields.io/badge/platform-Linux%20(BlueZ)-blue)](https://www.bluez.org/)
[![UI](https://img.shields.io/badge/UI-GTK4%20%2B%20Libadwaita%20%7C%20Web%20Studio-6366f1)](https://gnome.pages.gitlab.gnome.org/libadwaita/)
[![License](https://img.shields.io/badge/license-GPLv3-green)](LICENSE)

A native Linux desktop application (**GTK4 + Libadwaita**), embedded **Web Control Studio**, and **CLI (`buds4ctl`)** for controlling all functions and hardware features of the **Samsung Galaxy Buds4 Pro (`SM-R640`)** over Bluetooth RFCOMM (`SPP`).

---

## ✨ Features & Progressive-Disclosure UI Design

The interface is designed around **progressive disclosure** so everyday controls are front-and-center while advanced settings stay tucked away until clicked:

### Always Visible (Primary View)
1. **Hero Battery & Wearing Cards**:
   - Real-time **Left Earbud %**, **Right Earbud %**, and **Charging Case %** with progress bars and wearing status badges (`Wearing`, `Idle`, `In Case`, `Charging ⚡`).
2. **Primary Noise Controls**:
   - **4-Way Segmented Mode Selector**: Switch between **Off**, **ANC (Active Noise Canceling)**, **Ambient Sound**, and **Adaptive**.
   - **Contextual Strength Slider**: Automatically shows the **5-step ANC Strength Slider (Levels 1–5)** when ANC is active, or the **5-step Ambient Sound Volume Slider (Levels 1–5)** when Ambient/Adaptive is active.
   - **Quick Voice Detect Toggle**: Toggle Conversation Detection with one click.
3. **Sound & Equalizer Presets**:
   - Quick-select chips for **Balanced (Off)**, **Bass Boost**, **Soft**, **Dynamic**, **Clear**, **Treble Boost**, and **Custom**.
   - One-click toggles for **360 Spatial Audio** and **Low-Latency Gaming Mode**.

### Expandable Drawers (Revealed Only When Clicked)
- **Voice Detect + Smart Environment**: Conversation timeout (`5s` / `10s` / `15s`), **Adaptive Volume** (adjust volume to surroundings), **Siren Detect**, and **Noise Controls with One Earbud**.
- **Customize Ambient Sound**: Per-ear Left/Right ambient amplification (`0..4`), Ambient Sound Tone (`Soft` → `Clear`), and **Extra High Ambient Volume** boost.
- **9-Band Custom Equalizer & Stereo Balance**: 9 vertical frequency sliders (`63Hz`, `125Hz`, `250Hz`, `500Hz`, `1kHz`, `2kHz`, `4kHz`, `8kHz`, `16kHz`, `-10 dB` to `+10 dB`) + Left/Right Hearing Enhancement balance (`0..32`). Automatically re-applies the custom EQ table when the Buds4 Pro switches noise control modes.
- **Pinch & Touch Controls**: Master touchpad lock, individual pinch gestures (Single, Double, Triple, Pinch & Hold, Call Answer/Decline), Left/Right Pinch & Hold action assignment, and per-ear ANC/Ambient/Adaptive/Off cycle bitmasks.
- **Blade Lights & Voice Assistant**: Earbud LED lighting style (`Blink`, `Fade In/Out`, `Steady`), **Voice Controls (Hot Commands)**, **Bixby Voice Wake-up**, and **Speak Seamlessly**.
- **Calls, Connection & Find My Earbuds**: Call **Sidetone**, **Extra Clear Call Sound**, **Seamless Earbud Connection**, **Auto Pause/Resume**, **Automatic Call Path Control**, **Neck Stretch Posture Reminders**, **Find My Earbuds** (Ring/Stop & Left/Right Mute), **Earbud Fit Test**, and **Hardware Self-Test**.
- **Hardware Details & Developer SPP Console**: Firmware versions (Buds & Case), SKU & Serial Numbers, Left/Right thermistor temperatures (`°C`), cell voltage (`mV`), battery charge cycles, live hexadecimal `RX`/`TX` packet sniffer, and raw SPP frame injector.

---

## 🏗️ Architecture

Because Bluetooth RFCOMM only allows **one active client socket** on the earbuds' control channel at a time, `Samsung Galaxy Buds4 Pro Studio` uses a unified shared-daemon architecture:

```
┌────────────────────────────────────────────────────────────────┐
│                  Samsung Galaxy Buds4 Pro                      │
│       MAC: FC:6E:83:4B:14:49  |  Model: SM-R640 (Buds4 Pro)    │
└───────────────────────────────▲────────────────────────────────┘
                                │  BlueZ RFCOMM Socket
                                │  UUID: 2e73a4ad-332d-41fc-90e2-16bef06523f2
                                ▼
┌────────────────────────────────────────────────────────────────┐
│            buds4pro_protocol.py (Buds4ProController)           │
│   • BlueZ ProfileManager1 D-Bus Registration & Async Connect   │
│   • Binary Framing (0xFD..0xDD) + CRC16-CCITT Checksum Engine  │
│   • State Machine & Decoders for Revision 4 (62-byte status)   │
└───────────▲───────────────────▲────────────────────▲───────────┘
            │                   │                    │
            ▼                   ▼                    ▼
┌───────────────────┐ ┌──────────────────┐ ┌─────────────────────┐
│  buds4pro_gtk.py  │ │  buds4pro_web.py │ │     buds4ctl.py     │
│  Native GTK4 +    │ │  Web Studio UI   │ │  Fast Terminal CLI  │
│  Libadwaita GUI   │ │  127.0.0.1:8765  │ │  & Hotkey Utility   │
└───────────────────┘ └──────────────────┘ └─────────────────────┘
```

---

## 🔬 Reverse-Engineered Protocol Details (`SM-R640`)

### 1. Bluetooth Transport & Framing
- **Primary SPP UUID**: `2e73a4ad-332d-41fc-90e2-16bef06523f2`
- **Alternative SMEP UUID**: `f8620674-a1ed-41ab-a8b9-de9ad655729d`
- **Frame Format**:
  ```
  +-----------+-------------------+------------+------------------+--------------------+-----------+
  | SOM (1B)  | Header (2B, LE)   | MsgId (1B) | Payload (N B)    | CRC16-CCITT (2B)   | EOM (1B)  |
  |   0xFD    | Size | Flags      |  0x00-0xFF | Variable Length  | Over MsgId+Payload |   0xDD    |
  +-----------+-------------------+------------+------------------+--------------------+-----------+
  ```
  - `Header & 0x03FF`: `1 (MsgId) + len(Payload) + 2 (CRC16)`
  - `Header & 0x1000`: Request (`1` incoming / `0` outgoing) vs. Response
  - `Header & 0x2000`: Fragment flag

### 2. Galaxy Buds4 Pro (`SM-R640`) Specific Findings
During live packet analysis of the `SM-R640` (`R640XXU0AZD2`), we mapped and fixed several model-specific behaviors:
- **`EXTENDED_STATUS_UPDATED` (`0x61`, Revision `4`, 62 bytes)**:
  - `Byte 1` = `0x0D` (`13` = `Buds4Pro`), `Bytes 14..17` = `0x0167` (`359` = Buds4 Pro Black/Silver).
  - `Byte 12` = `NoiseControlMode` (`0` = Off, `1` = ANC, `2` = Ambient Sound, `3` = Adaptive).
  - `Byte 21` = Dual-side 4-mode Pinch & Hold cycle bitmask (`bit0` = Ambient, `bit1` = Adaptive, `bit2` = Off, `bit3` = ANC for Right; `bits 4..7` for Left).
  - `Byte 23` & `Byte 24` = 5-step `AmbientSoundVolume` (`0..4`) and 5-step `NoiseReductionLevel` (`0..4`).
  - `Byte 49` = `AdaptiveVolumeEnabled` (`SET_ADAPTIVE_VOLUME_ENABLED = 0xC5`).
  - `Byte 50` = `LightingControl` (`BUDS_LIGHTING_SYNC = 0x8E`: `0` = Blink, `1` = Fade In/Out, `2` = Steady).
  - `Byte 52` = `SirenDetect` (`UASC_SIREN_DETECT = 0xDE`).
- **`CRADLE_SERIAL_NUMBER` (`0xCD`, 27 bytes)**:
  - Unlike older models that used `9 + 11` bytes, the Buds4 Pro cradle sends a **13-byte null-padded firmware version** (`bytes 0..12`, e.g. `R640XXUZD1`) followed by a **14-byte null-padded serial number** (`bytes 13..26`).
- **Periodic Telemetry Frame (`0xF4`, 55 bytes)**:
  - Streams live battery cell voltage in millivolts (`bytes 34..37` LE, e.g. `4871 mV`) alongside `DEBUG_GET_ALL_DATA` (`0x26`) thermistor temperatures (`0.1 °C` units at `bytes 55..58`) and `SOC_BATTERY_CYCLE` (`0xCE`, 64-bit big-endian integers divided by `10000`).

---

## 📦 Installation & Running

### 1. Install System Dependencies

All components use standard Linux system packages (Python 3, BlueZ, PyGObject, GTK4, Libadwaita, and `dbus-python`) with zero external `pip` dependencies required.

**Fedora / RHEL:**
```bash
sudo dnf install bluez python3 python3-gobject python3-dbus gtk4 libadwaita
```

**Ubuntu / Debian:**
```bash
sudo apt install bluez python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 python3-dbus
```

**Arch Linux:**
```bash
sudo pacman -S bluez python python-gobject python-dbus gtk4 libadwaita
```

### 2. Install Desktop Launcher & CLI (`buds4ctl`)

Clone this repository and run the installer script (or `make install`):

```bash
git clone https://github.com/salman44444/samsung-buds4-pro-studio.git
cd samsung-buds4-pro-studio
./install.sh
```

This installs:
- `~/.local/bin/buds4ctl` — Command-line controller
- `~/.local/share/applications/samsung-buds4-pro.desktop` — Application menu shortcut

### 3. Usage

#### Launch the Native GTK4 + Libadwaita Desktop App
```bash
buds4ctl gui
# Or run directly:
python3 buds4pro_gtk.py
```
*(When the desktop app is running, the Web Control Studio is also automatically available at `http://127.0.0.1:8765`.)*

#### Launch Standalone Web Control Studio (`http://127.0.0.1:8765`)
```bash
buds4ctl web
# Or run directly:
python3 buds4pro_web.py
```

#### Command-Line Control (`buds4ctl`)
```bash
buds4ctl status              # Show live battery, temps, cycles, and feature states
buds4ctl connect             # Connect Galaxy Buds4 Pro to laptop
buds4ctl disconnect          # Disconnect Galaxy Buds4 Pro from laptop
buds4ctl anc                 # Enable Active Noise Cancellation (ANC)
buds4ctl ambient             # Enable Ambient Sound mode
buds4ctl adaptive            # Enable Adaptive Noise Control mode
buds4ctl off                 # Disable Noise Controls
buds4ctl anc-level 5         # Set ANC strength level (1..5)
buds4ctl ambient-vol 4       # Set Ambient Sound volume (1..5)
buds4ctl voice-detect on     # Toggle Conversation Detection (on/off)
buds4ctl siren-detect on     # Toggle Siren Detection (on/off)
buds4ctl adaptive-vol on     # Toggle Adaptive Volume (on/off)
buds4ctl eq dynamic          # Set EQ preset (off, bass, soft, dynamic, clear, treble, custom)
buds4ctl spatial headtrack   # Set 360 Spatial Audio (on, off, headtrack)
buds4ctl game-mode on        # Toggle Low-Latency Gaming Mode
buds4ctl lights 1            # Set Blade Lights (0=blink, 1=fade, 2=steady)
buds4ctl ring start          # Ring earbuds (Find My Earbuds)
buds4ctl raw 0x78 01         # Send raw SPP MsgId and hex payload
```

---

## 🙏 Open-Source Credits, References & Acknowledgments

This project builds upon and references the reverse-engineering research and open-source ecosystem listed below:

1. **[GalaxyBudsClient (`timschneeb/GalaxyBudsClient`)](https://github.com/timschneeb/GalaxyBudsClient)** by `@timschneeb` (*GPL-3.0 License*)
   - Primary reference for Samsung Galaxy Buds SPP message IDs (`SppMessageEnums.cs`), `CRC16-CCITT` lookup table (`Crc16.cs`), base status decoders (`ExtendedStatusUpdateDecoder.cs`, `DebugGetAllDataDecoder.cs`), and device specifications (`Buds3ProDeviceSpec.cs`, `Buds4ProDeviceSpec.cs`).
2. **[BlueZNet (`ThePBone/BlueZNet`)](https://github.com/ThePBone/BlueZNet)** & **[BlueZ Linux Bluetooth Stack](https://git.kernel.org/pub/scm/bluetooth/bluez.git)** (*MIT / GPL-2.0+*)
   - Reference for registering a client RFCOMM profile via BlueZ D-Bus `org.bluez.ProfileManager1` and handling `org.bluez.Profile1.NewConnection` file descriptors.
3. **[32feet.NET (`inthehand/32feet`)](https://github.com/inthehand/32feet)** (*MIT License*)
   - Reference for Bluetooth RFCOMM endpoint and SDP service discovery conventions.
4. **[GTK4](https://www.gtk.org/)**, **[Libadwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/)**, & **[PyGObject](https://pygobject.gnome.org/)** (*LGPL-2.1+*)
   - Used to build the native Linux desktop interface (`Adw.ApplicationWindow`, `Adw.ExpanderRow`, `Adw.PreferencesGroup`, and GLib event loop integration).
5. **[dbus-python](https://dbus.freedesktop.org/doc/dbus-python/)** (*MIT / AFL-2.1*)
   - Used to export the `org.bluez.Profile1` D-Bus service object and communicate with `org.bluez.Device1` and `org.bluez.ProfileManager1`.

---

## 📄 License

Distributed under the **GNU General Public License v3.0 (GPL-3.0)** in accordance with upstream protocol references from `GalaxyBudsClient`. See [LICENSE](LICENSE) for full details.
