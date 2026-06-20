#!/bin/bash
# Applica fix touch via SSH (senza accesso fisico al Pi)
# bash standalone/ssh-touch-fix.sh

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=standalone/x-session-env.sh
source "$APP_DIR/standalone/x-session-env.sh"

echo "DISPLAY=$DISPLAY"
echo "XAUTHORITY=${XAUTHORITY:-<non trovato>}"
echo "WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-<non impostato>}"

echo -n "Verifica sessione X... "
if x_session_ok; then
    echo "OK"
elif x_socket_ok; then
    echo "xrandr timeout ma socket X attivo — continuo"
else
    echo "NON DISPONIBILE"
    echo ""
    echo "Sessione grafica non attiva sul Pi."
    echo "Serve autologin desktop + reboot. Da SSH esegui:"
    echo "  sudo bash $APP_DIR/standalone/setup-remote-desktop.sh"
    echo "  sudo reboot"
    exit 1
fi

echo "Applico fix touch (display + xwayland-touch)..."
export X_CMD_TIMEOUT=8
if bash "$APP_DIR/standalone/fix-touchscreen.sh"; then
    :
else
    _rc=$?
    echo ""
    echo "fix-touchscreen.sh terminato con errore (codice $_rc)"
    exit "$_rc"
fi

echo ""
echo "OK. Se il kiosk non è visibile, riavvia autostart:"
echo "  pkill -f run_kiosk.py || true"
echo "  nohup $APP_DIR/standalone/launch_kiosk.sh >/tmp/timbranfc-kiosk.log 2>&1 &"
