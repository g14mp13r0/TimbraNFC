#!/bin/bash
# Configura kiosk + touch per uso remoto (solo SSH, nessun accesso fisico al Pi)
# sudo bash standalone/setup-remote-desktop.sh
#
# Prerequisito: Raspberry Pi OS con desktop e autologin utente abilitato.

set -euo pipefail

APP_USER="${APP_USER:-${SUDO_USER:-gpastorino}}"
APP_DIR="${APP_DIR:-/home/${APP_USER}/TimbraNFC}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Esegui con sudo"
    exit 1
fi

echo "=== Setup desktop remoto TimbraNFC ==="
echo "Utente: $APP_USER"

# Autologin desktop (raspi-config se disponibile)
if command -v raspi-config >/dev/null 2>&1; then
    echo "Abilito autologin desktop..."
    raspi-config nonint do_boot_behaviour B4 2>/dev/null || \
        echo "Autologin: configura manualmente con sudo raspi-config → Boot → Desktop Autologin"
fi

AUTOSTART="/home/${APP_USER}/.config/autostart"
mkdir -p "$AUTOSTART"

cat > "$AUTOSTART/timbranfc-touch.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=TimbraNFC Touch
Exec=${APP_DIR}/standalone/fix-touchscreen.sh --quiet
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

sed "s|/home/gpastorino/TimbraNFC|${APP_DIR}|g" \
    "$APP_DIR/standalone/autostart/timbranfc-kiosk.desktop" \
    > "$AUTOSTART/timbranfc-kiosk.desktop"

chown -R "${APP_USER}:${APP_USER}" "/home/${APP_USER}/.config"

# Server systemd sì, kiosk NO (conflitto NFC/touch — usa autostart desktop)
systemctl disable --now timbranfc-kiosk 2>/dev/null || true
systemctl enable timbranfc-server 2>/dev/null || true

chmod +x "$APP_DIR/standalone/fix-touchscreen.sh" "$APP_DIR/standalone/launch_kiosk.sh"

echo ""
echo "Fatto. Prossimi passi:"
echo "  1) sudo reboot   (oppure login desktop se già autologin)"
echo "  2) Da SSH dopo reboot: bash ${APP_DIR}/standalone/ssh-touch-fix.sh"
echo "  3) Dashboard: http://$(hostname -I | awk '{print $1}'):8080"
