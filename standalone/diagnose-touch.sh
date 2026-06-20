#!/bin/bash
# Diagnostica touchscreen Raspberry Pi
# bash standalone/diagnose-touch.sh

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=standalone/x-session-env.sh
source "$APP_DIR/standalone/x-session-env.sh"

echo "=== Diagnostica touch TimbraNFC ==="
echo ""

echo "--- Sessione ---"
echo "DISPLAY=$DISPLAY"
echo "WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-<non impostato>}"
echo "XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-<non impostato>}"
echo ""

echo "--- XWayland (xrandr) ---"
_xr="$(xrandr_query)"
if [ -n "$_xr" ]; then
    printf '%s\n' "$_xr" | awk '/Screen | connected/'
    _res="$(printf '%s\n' "$_xr" | awk '/ connected/{print $3; exit}')"
    case "$_res" in
        320x480*) echo "→ Portrait: serve rotazione sessione (wlr-randr) per kiosk 480x320" ;;
        480x320*) echo "→ Landscape OK per kiosk" ;;
    esac
else
    if x_socket_ok; then
        echo "xrandr timeout — socket X presente, sessione desktop probabilmente attiva"
    else
        echo "Display non raggiungibile da SSH (manca sessione desktop?)"
    fi
fi
echo ""

echo "--- Wayland (wlr-randr) ---"
if [ -n "${WAYLAND_DISPLAY:-}" ] && command -v wlr-randr >/dev/null 2>&1; then
    run_timeout 5 wlr-randr 2>/dev/null | awk '/^SPI-|^DSI-|^HDMI-|Transform:|current mode/' || \
        run_timeout 5 wlr-randr 2>/dev/null | head -15 || echo "(wlr-randr timeout o non disponibile)"
else
    echo "(wlr-randr non disponibile — installa: sudo apt install wlr-randr)"
fi
echo ""

echo "--- xinput ---"
if command -v xinput >/dev/null 2>&1; then
    xinput list 2>/dev/null | grep -E 'pointer|touch|Touch|ADS7846' || xinput list 2>/dev/null || true
else
    echo "xinput non installato"
fi
echo ""

echo "--- kernel ADS7846 ---"
grep -A6 'Name="ADS7846' /proc/bus/input/devices 2>/dev/null | head -10 || echo "(non trovato)"
echo ""

echo "--- config.txt ---"
for _cfg in /boot/firmware/config.txt /boot/config.txt; do
    [ -f "$_cfg" ] || continue
    echo "File: $_cfg"
    grep -E '^display_rotate=|^dtoverlay=piscreen|^dtoverlay=ads7846' "$_cfg" || true
    break
done
echo ""

echo "--- udev rule ---"
[ -f /etc/udev/rules.d/99-timbranfc-touch.rules ] && \
    cat /etc/udev/rules.d/99-timbranfc-touch.rules || echo "(manca — sudo bash standalone/fix-touch-os.sh)"
echo ""

echo "--- libinput device ---"
if command -v libinput >/dev/null 2>&1; then
    libinput list-devices 2>/dev/null | awk '
        /^Device:/ { dev=$0 }
        /^Size:/ { size=$0 }
        /^Calibration:/ { print dev; print size; print $0; print "" }
    ' || true
else
    echo "(libinput non installato)"
fi
echo ""

echo "--- libinput quirks (event ADS7846) ---"
_ev=""
for _name in /sys/class/input/event*/device/name; do
    [ -f "$_name" ] || continue
    if [ "$(tr -d '\n' < "$_name" 2>/dev/null)" = "ADS7846 Touchscreen" ]; then
        _ev="/dev/input/$(basename "$(dirname "$(dirname "$_name")")")"
        break
    fi
done
if [ -n "$_ev" ]; then
    echo "Event node: $_ev"
    if command -v libinput >/dev/null 2>&1; then
        libinput quirks list "$_ev" 2>/dev/null || libinput list-quirks "$_ev" 2>/dev/null || \
            echo "(comando quirks non disponibile su questa versione libinput)"
    fi
    echo "--- udevadm test ---"
    udevadm info -q property -n "$_ev" 2>/dev/null | grep -E 'LIBINPUT_CALIBRATION|ID_INPUT_TOUCHSCREEN|NAME=' || true
else
    echo "(event ADS7846 non trovato in /sys/class/input/)"
fi
echo ""

echo "--- xinput matrice (xwayland-touch) ---"
if command -v xinput >/dev/null 2>&1 && { [ -n "$_xr" ] || x_socket_ok; }; then
    _tid="$(xinput list --id-only 2>/dev/null | while read -r id; do
        n="$(xinput list --name-only "$id" 2>/dev/null || true)"
        case "$n" in *touch*|*Touch*) echo "$id"; break ;; esac
    done)"
    if [ -n "$_tid" ]; then
        xinput list-props "$_tid" 2>/dev/null | grep -i 'Coordinate Transformation Matrix' || true
    fi
fi
echo ""

echo "--- Azioni consigliate ---"
echo "1) Rimuovi TOUCH_FIRMWARE_ROTATED=1 da .env se presente"
echo "2) sudo bash standalone/fix-touch-os.sh && sudo reboot"
echo "3) bash standalone/ssh-touch-fix.sh"
echo "   (wlr-randr 480x320 + matrice touch su xwayland-touch)"
