#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${HOME}/.local/share/applications"

echo "==> Checking Python 3, GTK4, Libadwaita, and D-Bus bindings..."
python3 -c "import dbus, gi; gi.require_version('Gtk', '4.0'); gi.require_version('Adw', '1'); from gi.repository import Gtk, Adw, GLib"

chmod +x "${REPO_DIR}/buds4pro_protocol.py" \
         "${REPO_DIR}/buds4pro_gtk.py" \
         "${REPO_DIR}/buds4pro_web.py" \
         "${REPO_DIR}/buds4ctl.py"

mkdir -p "${BIN_DIR}" "${APP_DIR}"
ln -sf "${REPO_DIR}/buds4ctl.py" "${BIN_DIR}/buds4ctl"

cat > "${APP_DIR}/samsung-buds4-pro.desktop" <<EOF
[Desktop Entry]
Name=Samsung Buds4 Pro Studio
Comment=Control ANC, Ambient Sound, 9-Band EQ, 360 Audio, Pinch Gestures, and Telemetry for Galaxy Buds4 Pro
Exec=/usr/bin/python3 ${REPO_DIR}/buds4pro_gtk.py
Icon=audio-headphones
Terminal=false
Type=Application
Categories=AudioVideo;Audio;Settings;HardwareSettings;
Keywords=Samsung;Galaxy;Buds;Buds4;Pro;ANC;Bluetooth;Equalizer;
StartupWMClass=io.github.salman.SamsungBuds4ProStudio
EOF

echo "==> Installed CLI to: ${BIN_DIR}/buds4ctl"
echo "==> Installed Desktop Entry to: ${APP_DIR}/samsung-buds4-pro.desktop"
echo "==> Done! Run 'buds4ctl gui' to open the desktop app or 'buds4ctl status' for CLI status."
