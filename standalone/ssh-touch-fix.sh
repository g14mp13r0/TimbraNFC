#!/bin/bash
# Applica fix touch via SSH (senza accesso fisico al Pi)
# bash standalone/ssh-touch-fix.sh

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=standalone/x-session-env.sh
source "$APP_DIR/standalone/x-session-env.sh"

echo "DISPLAY=$DISPLAY"
echo "XAUTHORITY=${XAUTHORITY:-<non trovato>}"

if ! x_session_ok; then
    echo ""
    echo "Sessione grafica non attiva sul Pi."
    echo "Serve autologin desktop + reboot. Da SSH esegui:"
    echo "  sudo bash $APP_DIR/standalone/setup-remote-desktop.sh"
    echo "  sudo reboot"
    exit 1
fi

echo "Applico fix touch (display + xwayland-touch)..."
bash "$APP_DIR/standalone/fix-touchscreen.sh" || {
    echo ""
    echo "fix-touchscreen.sh terminato con errore (codice $?)"
    exit 1
}
echo ""
echo "OK. Se il kiosk non è visibile, riavvia autostart:"
echo "  pkill -f run_kiosk.py || true"
echo "  nohup $APP_DIR/standalone/launch_kiosk.sh >/tmp/timbranfc-kiosk.log 2>&1 &"
