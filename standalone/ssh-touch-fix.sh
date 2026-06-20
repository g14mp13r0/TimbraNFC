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
echo "DBUS_SESSION_BUS_ADDRESS=${DBUS_SESSION_BUS_ADDRESS:-<non impostato>}"

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

export X_CMD_TIMEOUT=15

echo "Applico fix touch nella sessione desktop (systemd-run --user)..."
if run_in_user_graphical_session "$APP_DIR/standalone/fix-touchscreen.sh"; then
    echo ""
    echo "OK."
else
    _rc=$?
    echo ""
    echo "fix-touchscreen terminato con errore (codice $_rc)"
    echo ""
    echo "Se persiste, installa servizio user e reboot:"
    echo "  sudo bash $APP_DIR/standalone/fix-touch-os.sh"
    echo "  sudo reboot"
    exit "$_rc"
fi

echo ""
echo "Se il kiosk non risponde al touch, riavvia:"
echo "  pkill -f run_kiosk.py || true"
echo "  nohup $APP_DIR/standalone/launch_kiosk.sh >/tmp/timbranfc-kiosk.log 2>&1 &"
