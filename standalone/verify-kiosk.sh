#!/bin/bash
# Diagnostica rapida kiosk che esce subito
# bash standalone/verify-kiosk.sh

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_USER="${APP_USER:-$(stat -c '%U' "$APP_DIR" 2>/dev/null || whoami)}"
UID_NUM="$(id -u "$APP_USER" 2>/dev/null || id -u)"
LOG="/tmp/timbranfc-kiosk.log"

echo "=== Verifica kiosk TimbraNFC ==="
echo ""

echo "--- Processo ---"
pgrep -af run_kiosk.py || echo "(non in esecuzione)"
pgrep -af launch_kiosk.sh || echo "(launch_kiosk non in esecuzione)"
echo ""

echo "--- Server ---"
curl -sf http://127.0.0.1:8080/health && echo || echo "Server NON risponde — sudo systemctl restart timbranfc-server"
echo ""

echo "--- Display ---"
# shellcheck source=standalone/x-session-env.sh
source "$APP_DIR/standalone/x-session-env.sh"
import_graphical_session_env "$APP_USER" 2>/dev/null || true
echo "DISPLAY=${DISPLAY:-?} WAYLAND=${WAYLAND_DISPLAY:-?} X_socket=$(x_socket_ok && echo OK || echo NO)"
if [ -S "/run/user/${UID_NUM}/wayland-0" ]; then
    echo "Wayland socket: /run/user/${UID_NUM}/wayland-0 OK"
fi
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
    grep '^Exec=' "$AUTOSTART" | sed 's/^/    /'
else
    echo "  autostart: ASSENTE"
fi
USER_UNIT="/home/${APP_USER}/.config/systemd/user/timbranfc-kiosk.service"
if [ -f "$USER_UNIT" ]; then
    echo "  user service: $USER_UNIT"
    if [ -d "/run/user/${UID_NUM}" ]; then
        sudo -u "$APP_USER" \
            XDG_RUNTIME_DIR="/run/user/${UID_NUM}" \
            DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${UID_NUM}/bus" \
            systemctl --user is-enabled timbranfc-kiosk.service 2>/dev/null \
            | sed 's/^/    enabled: /' || echo "    (sessione utente non attiva)"
        sudo -u "$APP_USER" \
            XDG_RUNTIME_DIR="/run/user/${UID_NUM}" \
            DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${UID_NUM}/bus" \
            systemctl --user is-active timbranfc-kiosk.service 2>/dev/null \
            | sed 's/^/    active: /' || true
    fi
else
    echo "  user service: ASSENTE — sudo bash $APP_DIR/standalone/setup-boot-kiosk.sh"
fi
echo ""

echo "--- Kiosk systemd di sistema (deve essere disabled) ---"
systemctl is-enabled timbranfc-kiosk.service 2>/dev/null || echo "non installato"
systemctl is-active timbranfc-kiosk.service 2>/dev/null || true
echo ""

echo "--- Log ($LOG) ---"
tail -40 "$LOG" 2>/dev/null || echo "(log assente)"
echo ""

echo "--- Ripara avvio automatico ---"
echo "  sudo bash $APP_DIR/standalone/setup-boot-kiosk.sh"
echo ""
echo "--- Avvio manuale ---"
echo "  bash $APP_DIR/standalone/launch_kiosk.sh"
echo "  tail -f $LOG"
