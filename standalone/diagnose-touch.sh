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

echo "--- Fix rapido ---"
echo "  bash standalone/ssh-touch-fix.sh"
echo ""
echo "Se xrandr fallisce (BadMatch), rotazione permanente:"
echo "  sudo bash standalone/enable-spi-landscape.sh && sudo reboot"
