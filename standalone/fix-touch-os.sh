#!/bin/bash
# Fix touch ADS7846 / piscreen a livello OS (udev libinput + overlay opzionale)
# sudo bash standalone/fix-touch-os.sh
#
# Pi OS Bookworm+: touch ADS7846 → libinput → labwc → xwayland-touch → kiosk Tkinter

set -euo pipefail

APP_USER="${APP_USER:-${SUDO_USER:-gpastorino}}"
APP_DIR="${APP_DIR:-/home/${APP_USER}/TimbraNFC}"
CONFIG="${1:-/boot/firmware/config.txt}"
UDEV_RULE="/etc/udev/rules.d/99-timbranfc-touch.rules"
LIBINPUT_QUIRKS="/etc/libinput/local-overrides.quirks"
QUIRK_SECTION="Timbranfc ADS7846 landscape"

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

# Matrice libinput 6 valori (affine 2D). Default: rotazione 90° CCW per landscape kiosk.
LIBINPUT_MATRIX="${TOUCH_LIBINPUT_MATRIX:-0 -1 1 1 0 0}"
PISCREEN_SWAPXY="${PISCREEN_SWAPXY:-0}"
PISCREEN_INVX="${PISCREEN_INVX:-0}"
PISCREEN_INVY="${PISCREEN_INVY:-0}"

echo "=== Fix touch OS TimbraNFC ==="

cp "$CONFIG" "${CONFIG}.bak.touch-os-$(date +%Y%m%d%H%M%S)"

_overlay_set_param() {
    local key="$1"
    local val="$2"
    local line="$3"
    if echo "$line" | grep -q "${key}="; then
        echo "$line" | sed -E "s/(${key}=)[^,]*/\\1${val}/"
    else
        echo "${line},${key}=${val}"
    fi
}

_piscreen_line="$(grep -E '^dtoverlay=piscreen' "$CONFIG" | tail -1 || true)"
_ads_line="$(grep -E '^dtoverlay=ads7846' "$CONFIG" | tail -1 || true)"

if [ -n "$_piscreen_line" ]; then
    _new="$_piscreen_line"
    _new="$(_overlay_set_param swapxy "$PISCREEN_SWAPXY" "$_new")"
    _new="$(_overlay_set_param invx "$PISCREEN_INVX" "$_new")"
    _new="$(_overlay_set_param invy "$PISCREEN_INVY" "$_new")"
    if [ "$_new" != "$_piscreen_line" ]; then
        sed -i "s|^dtoverlay=piscreen.*|${_new}|" "$CONFIG"
        echo "Aggiornato overlay piscreen:"
        echo "  $_new"
    else
        echo "Overlay piscreen: $_piscreen_line"
    fi
    echo ""
    echo "Nota: rotate=90 sul piscreen ruota il pannello DRM; XWayland può restare 320x480."
    echo "La rotazione sessione (wlr-randr) è in fix-touchscreen.sh / autostart."
fi

if [ -n "$_ads_line" ]; then
    _new="$_ads_line"
    _new="$(_overlay_set_param swapxy "$PISCREEN_SWAPXY" "$_new")"
    _new="$(_overlay_set_param invx "$PISCREEN_INVX" "$_new")"
    _new="$(_overlay_set_param invy "$PISCREEN_INVY" "$_new")"
    if [ "$_new" != "$_ads_line" ]; then
        sed -i "s|^dtoverlay=ads7846.*|${_new}|" "$CONFIG"
        echo "Aggiornato overlay ads7846: $_new"
    fi
elif [ -z "$_piscreen_line" ]; then
    echo "Nessun dtoverlay=piscreen o ads7846 in $CONFIG"
fi

# --- udev libinput (varie strategie di match) ---
cat > "$UDEV_RULE" <<EOF
# TimbraNFC — calibrazione touch ADS7846 (Wayland/labwc/libinput)
# Matrice 6 valori: ${LIBINPUT_MATRIX}

# Match primario: nome esatto device input
ACTION=="add|change", SUBSYSTEM=="input", ENV{ID_INPUT_TOUCHSCREEN}=="1", \\
  ATTRS{name}=="ADS7846 Touchscreen", \\
  ENV{LIBINPUT_CALIBRATION_MATRIX}="${LIBINPUT_MATRIX}"

# Fallback senza ID_INPUT_TOUCHSCREEN (alcuni kernel)
ACTION=="add|change", SUBSYSTEM=="input", KERNEL=="event*", \\
  ATTRS{name}=="ADS7846 Touchscreen", \\
  ENV{LIBINPUT_CALIBRATION_MATRIX}="${LIBINPUT_MATRIX}"
EOF

echo "Scritto $UDEV_RULE (matrice: ${LIBINPUT_MATRIX})"

# --- libinput quirks: /etc/libinput/local-overrides.quirks (unico path valido) ---
touch "$LIBINPUT_QUIRKS"
if grep -q "^\[${QUIRK_SECTION}\]" "$LIBINPUT_QUIRKS" 2>/dev/null; then
    awk -v section="[${QUIRK_SECTION}]" '
        BEGIN { skip=0 }
        /^\[/ { if ($0 == section) { skip=1; next } else { skip=0 } }
        !skip { print }
    ' "$LIBINPUT_QUIRKS" > "${LIBINPUT_QUIRKS}.tmp"
    mv "${LIBINPUT_QUIRKS}.tmp" "$LIBINPUT_QUIRKS"
fi
cat >> "$LIBINPUT_QUIRKS" <<EOF

[${QUIRK_SECTION}]
MatchUdevType=touch
MatchName=ADS7846 Touchscreen
AttrCalibrationMatrix=${LIBINPUT_MATRIX}
EOF
rm -rf /etc/libinput/local-overrides.quirks.d 2>/dev/null || true

echo "Aggiornato $LIBINPUT_QUIRKS"

# --- Autostart: rotazione display + touch ogni login desktop ---
AUTOSTART="/home/${APP_USER}/.config/autostart"
mkdir -p "$AUTOSTART"
cat > "$AUTOSTART/timbranfc-touch.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=TimbraNFC Touch
Exec=${APP_DIR}/standalone/fix-touchscreen.sh --quiet
Terminal=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=4
EOF

USER_SYSTEMD="/home/${APP_USER}/.config/systemd/user"
mkdir -p "$USER_SYSTEMD"
sed "s|@APP_DIR@|${APP_DIR}|g" "$APP_DIR/standalone/systemd/timbranfc-touch.user.service" \
    > "$USER_SYSTEMD/timbranfc-touch.service"

chown -R "${APP_USER}:${APP_USER}" "/home/${APP_USER}/.config"

_uid_app="$(id -u "$APP_USER")"
sudo -u "$APP_USER" env \
    XDG_RUNTIME_DIR="/run/user/${_uid_app}" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${_uid_app}/bus" \
    systemctl --user enable timbranfc-touch.service 2>/dev/null || true

udevadm control --reload-rules
udevadm trigger --subsystem-match=input --action=change 2>/dev/null || true

echo ""
echo "=== Fatto ==="
echo "1) Riavvia (overlay): sudo reboot"
echo "2) Dopo reboot: bash ${APP_DIR}/standalone/ssh-touch-fix.sh"
echo "3) Verifica: bash ${APP_DIR}/standalone/diagnose-touch.sh"
echo ""
echo "In .env NON usare TOUCH_FIRMWARE_ROTATED=1 finché il touch non funziona."
echo "Varianti overlay se sfasato:"
echo "  PISCREEN_SWAPXY=1 PISCREEN_INVX=1 sudo bash standalone/fix-touch-os.sh"
