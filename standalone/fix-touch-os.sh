#!/bin/bash
# Fix touch ADS7846 / piscreen a livello OS (overlay swapxy + udev libinput)
# sudo bash standalone/fix-touch-os.sh
#
# Su Pi OS Bookworm+ il touch passa da libinput → compositor → xwayland-touch.
# xinput da solo non basta: serve swapxy sull'overlay piscreen/ads7846 e/o udev.

set -euo pipefail

APP_USER="${APP_USER:-${SUDO_USER:-gpastorino}}"
APP_DIR="${APP_DIR:-/home/${APP_USER}/TimbraNFC}"
CONFIG="${1:-/boot/firmware/config.txt}"
UDEV_RULE="/etc/udev/rules.d/99-timbranfc-touch.rules"
LIBINPUT_QUIRKS="/etc/libinput/local-overrides.quirks.d/99-timbranfc-touch.quirks"

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

# Matrice libinput 6 valori (solo se swapxy overlay non basta)
# Con piscreen+rotate=90 di solito basta swapxy=1 → matrice identità
LIBINPUT_MATRIX="${TOUCH_LIBINPUT_MATRIX:-}"
PISCREEN_SWAPXY="${PISCREEN_SWAPXY:-1}"
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

# --- 1) Overlay piscreen (display SPI 3.5" con ADS7846 integrato) ---
_piscreen_line="$(grep -E '^dtoverlay=piscreen' "$CONFIG" | tail -1 || true)"
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
        echo "Overlay piscreen già configurato: $_piscreen_line"
    fi
    echo ""
    echo "Se il touch resta sfasato dopo reboot, prova varianti (in .env o export):"
    echo "  PISCREEN_SWAPXY=1 PISCREEN_INVX=1 PISCREEN_INVY=0 sudo bash standalone/fix-touch-os.sh"
    echo "  PISCREEN_SWAPXY=1 PISCREEN_INVX=0 PISCREEN_INVY=1 sudo bash standalone/fix-touch-os.sh"
fi

# --- 2) Overlay ads7846 standalone (altri pannelli SPI) ---
_ads_line="$(grep -E '^dtoverlay=ads7846' "$CONFIG" | tail -1 || true)"
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
    echo "Cerca: grep -iE 'piscreen|ads7846|touch' $CONFIG"
fi

# Matrice libinput di default
if [ -z "$LIBINPUT_MATRIX" ]; then
    if [ -n "$_piscreen_line" ] && [ "$PISCREEN_SWAPXY" = "1" ]; then
        LIBINPUT_MATRIX="1 0 0 0 1 0"
        echo "libinput: matrice identità (rotazione touch via swapxy overlay)"
    else
        LIBINPUT_MATRIX="0 -1 1 1 0 0"
        echo "libinput: matrice rotazione 90° (TOUCH_LIBINPUT_MATRIX per override)"
    fi
fi

# --- 3) udev libinput (match ESATTO sul nome — udev è case-sensitive) ---
cat > "$UDEV_RULE" <<EOF
# TimbraNFC — calibrazione touch ADS7846 (Wayland/labwc/libinput)
# Nota: *ads7846* minuscolo NON matcha "ADS7846 Touchscreen"
ACTION=="add|change", SUBSYSTEM=="input", KERNEL=="event*", \\
  ATTRS{name}=="ADS7846 Touchscreen", \\
  ENV{LIBINPUT_CALIBRATION_MATRIX}="${LIBINPUT_MATRIX}"
EOF

echo "Scritto $UDEV_RULE"

# --- 4) libinput quirks (backup se udev env non basta) ---
mkdir -p "$(dirname "$LIBINPUT_QUIRKS")"
cat > "$LIBINPUT_QUIRKS" <<EOF
# TimbraNFC — touch SPI landscape
[Timbranfc ADS7846 landscape]
MatchName=ADS7846 Touchscreen
AttrCalibrationMatrix=${LIBINPUT_MATRIX}
EOF

echo "Scritto $LIBINPUT_QUIRKS"

# --- 5) Autostart touch XWayland (kiosk Tkinter) ---
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

# Ricarica udev senza reboot (overlay piscreen richiede comunque reboot)
udevadm control --reload-rules
udevadm trigger --subsystem-match=input --action=change 2>/dev/null || \
    udevadm trigger --subsystem-match=input 2>/dev/null || true

echo ""
echo "=== Fatto ==="
echo "Riavvia per applicare overlay piscreen (swapxy):"
echo "  sudo reboot"
echo ""
echo "Dopo reboot:"
echo "  bash ${APP_DIR}/standalone/diagnose-touch.sh"
echo ""
echo "libinput deve mostrare Calibration diversa da 'identity matrix'."
echo "Poi, se serve per il kiosk X11:"
echo "  bash ${APP_DIR}/standalone/ssh-touch-fix.sh"
echo ""
echo "Se con swapxy=1 il touch è già corretto, in .env:"
echo "  TOUCH_FIRMWARE_ROTATED=1"
echo "  TOUCH_MATRIX=\"1 0 0 0 1 0 0 0 1\""
