#!/bin/bash
# Corregge systemd per l'utente corrente (es. gpastorino invece di pi)
# sudo bash standalone/fix-services.sh

set -euo pipefail

APP_USER="${APP_USER:-${SUDO_USER:-gpastorino}}"
APP_DIR="${APP_DIR:-/home/${APP_USER}/TimbraNFC}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Esegui con sudo"
    exit 1
fi

if [ ! -f "$APP_DIR/.venv/bin/python" ]; then
    echo "Errore: venv non trovato in $APP_DIR/.venv"
    exit 1
fi

echo "Utente: $APP_USER"
echo "Cartella: $APP_DIR"

chmod +x "$APP_DIR/standalone/launch_kiosk.sh" 2>/dev/null || true

cat > /etc/systemd/system/timbranfc-server.service <<UNIT
[Unit]
Description=TimbraNFC Server
After=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=-${APP_DIR}/.env
Environment=STANDALONE=1
Environment=TIMBRANFC_DATA=${APP_DIR}/data
Environment=SERVER_HOST=0.0.0.0
Environment=SERVER_PORT=8080
ExecStart=${APP_DIR}/.venv/bin/python ${APP_DIR}/standalone/run_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

cat > /etc/systemd/system/timbranfc-kiosk.service <<UNIT
[Unit]
Description=TimbraNFC Kiosk
After=timbranfc-server.service graphical.target
Requires=timbranfc-server.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=-${APP_DIR}/.env
Environment=APP_DIR=${APP_DIR}
Environment=APP_USER=${APP_USER}
Environment=STANDALONE=1
Environment=TIMBRANFC_DATA=${APP_DIR}/data
Environment=SERVER_URL=http://127.0.0.1:8080
ExecStart=${APP_DIR}/standalone/launch_kiosk.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=graphical.target
UNIT

# Autostart desktop
AUTOSTART="/home/${APP_USER}/.config/autostart/timbranfc-kiosk.desktop"
mkdir -p "$(dirname "$AUTOSTART")"
cat > "$AUTOSTART" <<DESKTOP
[Desktop Entry]
Type=Application
Name=TimbraNFC Kiosk
Exec=${APP_DIR}/standalone/launch_kiosk.sh
Terminal=false
X-GNOME-Autostart-enabled=true
DESKTOP
chown "${APP_USER}:${APP_USER}" "$AUTOSTART"

# .env — correggi path pi se presenti
if [ -f "$APP_DIR/.env" ]; then
    sed -i "s|/home/pi/TimbraNFC|${APP_DIR}|g" "$APP_DIR/.env"
    chown "${APP_USER}:${APP_USER}" "$APP_DIR/.env"
fi

systemctl daemon-reload
systemctl enable timbranfc-server
systemctl restart timbranfc-server
sleep 2

if curl -sf http://127.0.0.1:8080/health >/dev/null; then
    echo "Server OK: http://$(hostname -I | awk '{print $1}'):8080"
else
    echo "Server non risponde — controlla: journalctl -u timbranfc-server -n 20"
    journalctl -u timbranfc-server -n 15 --no-pager
    exit 1
fi

systemctl enable timbranfc-kiosk
systemctl restart timbranfc-kiosk || echo "Kiosk: riavvia dopo login desktop o usa autostart"

echo "Fatto. Dashboard: http://$(hostname -I | awk '{print $1}'):8080"
