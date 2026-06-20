#!/bin/bash
# Fix touch ADS7846 a livello OS (udev/libinput + overlay swapxy)
# sudo bash standalone/fix-touch-os.sh
#
# display_rotate ruota lo schermo ma spesso NON il touch: serve swapxy sull'overlay
# e/o matrice libinput applicata dal kernel.

set -euo pipefail

APP_USER="${APP_USER:-${SUDO_USER:-gpastorino}}"
APP_DIR="${APP_DIR:-/home/${APP_USER}/TimbraNFC}"
CONFIG="${1:-/boot/firmware/config.txt}"
UDEV_RULE="/etc/udev/rules.d/99-timbranfc-touch.rules"

if [ "$(id -u)" -ne 0 ]; then
    echo "Esegui con sudo"
    exit 1
fi

if [ ! -f "$CONFIG" ]; then
    CONFIG=/boot/config.txt
fi

if [ ! -f "$CONFIG" ]; then
    echo "config.txt non trovato" >&2
    exit 1
fi

# Matrice libinput 6 valori (equivalente rotazione 90° CCW / TOUCH_ROTATE=left)
# x' = 0*x + (-1)*y + 1,  y' = 1*x + 0*y + 0  (coordinate normalizzate 0..1)
LIBINPUT_MATRIX="${TOUCH_LIBINPUT_MATRIX:-0 -1 1 1 0 0}"

echo "=== Fix touch OS TimbraNFC ==="

cp "$CONFIG" "${CONFIG}.bak.touch-os-$(date +%Y%m%d%H%M%S)"

# --- 1) Overlay ADS7846: swapxy=1 (allinea touch a display_rotate=1) ---
_overlay_line="$(grep -E '^dtoverlay=ads7846' "$CONFIG" | tail -1 || true)"
if [ -n "$_overlay_line" ]; then
    if echo "$_overlay_line" | grep -q 'swapxy='; then
        sed -i 's/\(dtoverlay=ads7846[^[:space:]]*.*\)swapxy=[^,]*/\1swapxy=1/' "$CONFIG"
        echo "Aggiornato swapxy=1 su overlay ads7846"
    else
        sed -i 's/^\(dtoverlay=ads7846[^[:space:]]*\)/\1,swapxy=1/' "$CONFIG"
        echo "Aggiunto swapxy=1 su overlay ads7846"
    fi
else
    echo "Nessun dtoverlay=ads7846 in $CONFIG (touch potrebbe usare altro driver)."
    echo "Cerca manualmente: grep -i touch $CONFIG"
fi

# --- 2) udev: matrice libinput per ADS7846 (Wayland + sessione desktop) ---
cat > "$UDEV_RULE" <<EOF
# TimbraNFC — rotazione touch SPI 3.5" (ADS7846) con display landscape
ACTION=="add|change", SUBSYSTEM=="input", KERNEL=="event*", \\
  ENV{ID_INPUT_TOUCHSCREEN}=="1", ENV{LIBINPUT_DEVICE_GROUP}=="ads7846", \\
  ENV{LIBINPUT_CALIBRATION_MATRIX}="${LIBINPUT_MATRIX}"

# Fallback: nome dispositivo kernel
ACTION=="add|change", SUBSYSTEM=="input", ATTRS{name}=="*ads7846*", \\
  ENV{LIBINPUT_CALIBRATION_MATRIX}="${LIBINPUT_MATRIX}"
EOF

echo "Scritto $UDEV_RULE"

# --- 3) Autostart touch (sessione X11/XWayland) ---
AUTOSTART="/home/${APP_USER}/.config/autostart"
mkdir -p "$AUTOSTART"
cat > "$AUTOSTART/timbranfc-touch.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=TimbraNFC Touch
Exec=${APP_DIR}/standalone/fix-touchscreen.sh --quiet
Terminal=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=3
EOF
chown -R "${APP_USER}:${APP_USER}" "/home/${APP_USER}/.config"

echo ""
echo "=== Fatto ==="
echo "Riavvia per applicare overlay + udev:"
echo "  sudo reboot"
echo ""
echo "Dopo reboot, verifica da SSH:"
echo "  bash ${APP_DIR}/standalone/diagnose-touch.sh"
echo "  bash ${APP_DIR}/standalone/ssh-touch-fix.sh"
echo ""
echo "Se il touch è invertito/sfasato, prova in .env una di queste matrici:"
echo "  TOUCH_MATRIX=\"0 1 0 -1 0 1 0 0 1\"    # 90° opposta"
echo "  TOUCH_MATRIX=\"1 0 0 0 1 0 0 0 1\"      # identità (se swapxy basta)"
echo ""
echo "Poi: bash ${APP_DIR}/standalone/ssh-touch-fix.sh"
