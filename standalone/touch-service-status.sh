#!/bin/bash
# Stato servizio touch user + log (funziona da SSH)
# bash standalone/touch-service-status.sh

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
_uid="$(id -u)"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/${_uid}}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=${XDG_RUNTIME_DIR}/bus}"

echo "=== TimbraNFC touch service ==="
echo "UID=$_uid  XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR"
echo ""

if [ ! -S "${XDG_RUNTIME_DIR}/bus" ]; then
    echo "Bus D-Bus utente non attivo (desktop non loggato?)."
    echo "Verifica autologin: sudo bash $APP_DIR/standalone/setup-remote-desktop.sh"
    echo ""
fi

echo "--- systemctl --user status ---"
systemctl --user status timbranfc-touch.service --no-pager 2>&1 || true
echo ""

echo "--- Log file (/tmp/timbranfc-touch.log) ---"
if [ -f /tmp/timbranfc-touch.log ]; then
    tail -30 /tmp/timbranfc-touch.log
else
    echo "(file assente — servizio/autostart non ancora eseguito)"
fi
echo ""

echo "--- journalctl --user (se disponibile) ---"
if journalctl --user -u timbranfc-touch.service -n 15 --no-pager 2>/dev/null; then
    :
else
    echo "(journal utente non accessibile da questa sessione SSH — usa /tmp/timbranfc-touch.log)"
fi
echo ""

echo "--- Avvio manuale ---"
echo "  bash $APP_DIR/standalone/ssh-touch-fix.sh"
echo "  # oppure:"
echo "  XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS \\"
echo "    systemctl --user start timbranfc-touch.service"
