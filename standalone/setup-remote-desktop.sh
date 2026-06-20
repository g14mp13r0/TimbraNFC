#!/bin/bash
# Configura kiosk + touch per uso remoto (solo SSH, nessun accesso fisico al Pi)
# sudo bash standalone/setup-remote-desktop.sh
#
# Abilita autologin desktop e avvio automatico kiosk UI al boot.

set -euo pipefail

APP_USER="${APP_USER:-${SUDO_USER:-gpastorino}}"
APP_DIR="${APP_DIR:-/home/${APP_USER}/TimbraNFC}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Esegui con sudo"
    exit 1
fi

echo "=== Setup desktop remoto TimbraNFC ==="
echo "Utente: $APP_USER"

bash "$APP_DIR/standalone/setup-boot-kiosk.sh"

AUTOSTART="/home/${APP_USER}/.config/autostart"
mkdir -p "$AUTOSTART"

cat > "$AUTOSTART/timbranfc-touch.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=TimbraNFC Touch
Exec=${APP_DIR}/standalone/fix-touchscreen.sh --quiet
Terminal=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
EOF

chown -R "${APP_USER}:${APP_USER}" "/home/${APP_USER}/.config"

systemctl enable timbranfc-server 2>/dev/null || true
chmod +x "$APP_DIR/standalone/fix-touchscreen.sh" "$APP_DIR/standalone/launch_kiosk.sh"

echo ""
echo "Fatto. Prossimi passi:"
echo "  1) sudo reboot"
echo "  2) Il kiosk parte da solo (~30s dopo il boot, senza login)"
echo "  3) Dashboard: http://$(hostname -I | awk '{print $1}'):8080"
