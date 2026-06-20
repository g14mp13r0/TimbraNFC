#!/bin/bash
# Diagnostica touchscreen Raspberry Pi
# bash standalone/diagnose-touch.sh

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=standalone/x-session-env.sh
source "$APP_DIR/standalone/x-session-env.sh"

echo "=== Diagnostica touch TimbraNFC ==="
echo ""

echo "--- DISPLAY ---"
echo "DISPLAY=$DISPLAY"
echo ""

echo "--- Sessione grafica ---"
if xdpyinfo >/dev/null 2>&1; then
    echo "X11 nativo: OK"
    xdpyinfo | awk '/dimensions:|resolution:/'
elif xrandr --query >/dev/null 2>&1; then
    echo "XWayland: OK (Wayland + DISPLAY=:0 — normale su Pi OS recente)"
    xrandr --query | awk '/Screen | connected/'
else
    echo "Display non raggiungibile. Esegui dal terminale del desktop Pi, non da SSH."
fi
echo ""

echo "--- xinput (dispositivi pointer) ---"
if command -v xinput >/dev/null 2>&1; then
    xinput list 2>/dev/null || echo "(xinput fallito)"
else
    echo "xinput non installato → sudo apt install xinput"
fi
echo ""

echo "--- xrandr (schermi) ---"
if command -v xrandr >/dev/null 2>&1; then
    xrandr --query 2>/dev/null | grep -E ' connected|Screen' || true
else
    echo "xrandr non installato"
fi
echo ""

echo "--- kernel input (touch) ---"
grep -iE 'touch|ads7846|goodix|egalax|ft5406' /proc/bus/input/devices 2>/dev/null | head -20 || \
    echo "(nessun driver touch nel kernel — controlla overlay in /boot/firmware/config.txt)"
echo ""

echo "--- config.txt (display/touch overlay) ---"
for _cfg in /boot/firmware/config.txt /boot/config.txt; do
    [ -f "$_cfg" ] || continue
    echo "File: $_cfg"
    grep -E '^display_rotate=|^lcd_rotate=|^dtoverlay=piscreen|^dtoverlay=ads7846' "$_cfg" || \
        echo "(nessuna riga piscreen/ads7846/display_rotate)"
    break
done
echo ""

echo "--- udev libinput ---"
if [ -f /etc/udev/rules.d/99-timbranfc-touch.rules ]; then
    cat /etc/udev/rules.d/99-timbranfc-touch.rules
else
    echo "(manca 99-timbranfc-touch.rules — esegui fix-touch-os.sh)"
fi
echo ""

if command -v libinput >/dev/null 2>&1; then
    echo "--- libinput list-devices (touch) ---"
    libinput list-devices 2>/dev/null | awk '/Device:|Size:|Calibration/' || true
    echo ""
fi

echo "--- xinput matrice (xwayland-touch) ---"
if command -v xinput >/dev/null 2>&1 && xrandr --query >/dev/null 2>&1; then
    _tid="$(xinput list --id-only 2>/dev/null | while read -r id; do
        n="$(xinput list --name-only "$id" 2>/dev/null || true)"
        case "$n" in *touch*|*Touch*|*ADS7846*) echo "$id"; break ;; esac
    done)"
    if [ -n "$_tid" ]; then
        xinput list-props "$_tid" 2>/dev/null | grep -i 'Coordinate Transformation Matrix' || \
            echo "(proprietà matrice non trovata)"
    else
        echo "(nessun device touch in xinput)"
    fi
else
    echo "(xinput/display non disponibile)"
fi
echo ""

echo "--- udev test ADS7846 ---"
_ev=""
for _d in /dev/input/event*; do
    [ -e "$_d" ] || continue
    if udevadm info -q property -n "$_d" 2>/dev/null | grep -q 'NAME="ADS7846 Touchscreen"'; then
        _ev="$_d"
        break
    fi
done
if [ -n "$_ev" ]; then
    echo "Device: $_ev"
    udevadm info -q property -n "$_ev" 2>/dev/null | grep LIBINPUT_CALIBRATION || \
        echo "LIBINPUT_CALIBRATION_MATRIX non impostata (bug udev o serve reboot)"
else
    echo "(event ADS7846 non trovato)"
fi
echo ""

echo "--- Fix rapido (sessione X) ---"
echo "  bash standalone/ssh-touch-fix.sh"
echo ""
echo "--- Fix OS (piscreen swapxy + udev, richiede reboot) ---"
echo "  sudo bash standalone/fix-touch-os.sh && sudo reboot"
echo ""
echo "Setup rilevato: dtoverlay=piscreen,...,rotate=90"
echo "  → aggiunge swapxy=1 sull'overlay (fix kernel)"
echo "  → corregge udev (match case-sensitive ADS7846 Touchscreen)"
