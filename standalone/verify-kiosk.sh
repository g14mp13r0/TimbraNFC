#!/bin/bash
# Diagnostica rapida kiosk che esce subito
# bash standalone/verify-kiosk.sh

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_USER="${APP_USER:-$(whoami)}"
LOG="/tmp/timbranfc-kiosk.log"

echo "=== Verifica kiosk TimbraNFC ==="
echo ""

echo "--- Processo ---"
pgrep -af run_kiosk.py || echo "(non in esecuzione)"
echo ""

echo "--- Server ---"
curl -sf http://127.0.0.1:8080/health && echo || echo "Server NON risponde — sudo systemctl restart timbranfc-server"
echo ""

echo "--- Display ---"
# shellcheck source=standalone/x-session-env.sh
source "$APP_DIR/standalone/x-session-env.sh"
echo "DISPLAY=$DISPLAY socket=$(x_socket_ok && echo OK || echo NO)"
echo ""

echo "--- Autologin desktop ---"
if [ -f /etc/lightdm/lightdm.conf.d/50-timbranfc-autologin.conf ]; then
    grep -E '^autologin-' /etc/lightdm/lightdm.conf.d/50-timbranfc-autologin.conf | sed 's/^/  /'
else
    echo "  NON configurato — esegui: sudo bash $APP_DIR/standalone/setup-boot-kiosk.sh"
fi
AUTOSTART="/home/${APP_USER}/.config/autostart/timbranfc-kiosk.desktop"
if [ -f "$AUTOSTART" ]; then
    echo "  autostart: $AUTOSTART"
else
    echo "  autostart: ASSENTE"
fi
echo ""

echo "--- Kiosk systemd (dovrebbe essere disabled) ---"
systemctl is-enabled timbranfc-kiosk.service 2>/dev/null || echo "non installato"
systemctl is-active timbranfc-kiosk.service 2>/dev/null || true
echo ""

echo "--- Log ($LOG) ---"
tail -40 "$LOG" 2>/dev/null || echo "(log assente)"
echo ""

echo "--- Avvio manuale ---"
echo "  bash $APP_DIR/standalone/launch_kiosk.sh"
echo "  tail -f $LOG"
