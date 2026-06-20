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

# Permessi smartcard (PC/SC)
SCARD_GROUP_LINE=""
if getent group scard >/dev/null 2>&1; then
    usermod -aG scard "$APP_USER" 2>/dev/null || true
    SCARD_GROUP_LINE="SupplementaryGroups=scard"
fi

cat > /etc/systemd/system/timbranfc-server.service <<UNIT
[Unit]
Description=TimbraNFC Server
After=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
${SCARD_GROUP_LINE}
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
After=timbranfc-server.service graphical.target pcscd.service pcscd.socket
Requires=timbranfc-server.service
Wants=pcscd.service pcscd.socket

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
SupplementaryGroups=scard
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
X-GNOME-Autostart-Delay=10
DESKTOP
chown "${APP_USER}:${APP_USER}" "$AUTOSTART"

# .env — correggi path pi se presenti
if [ -f "$APP_DIR/.env" ]; then
    sed -i "s|/home/pi/TimbraNFC|${APP_DIR}|g" "$APP_DIR/.env"
    chown "${APP_USER}:${APP_USER}" "$APP_DIR/.env"
fi

# Backend NFC di default: PC/SC per migliore compatibilita ACR122U
if [ -f "$APP_DIR/.env" ] && ! grep -q '^NFC_BACKEND=' "$APP_DIR/.env"; then
    echo "NFC_BACKEND=pcsc" >> "$APP_DIR/.env"
fi
systemctl enable --now pcscd pcscd.socket 2>/dev/null || true

# Disabilita unit legacy con path /home/pi (se presenti)
for legacy in timbratrice dashboard ui-kiosk hub; do
    systemctl disable --now "${legacy}.service" 2>/dev/null || true
done

systemctl daemon-reload
systemctl reset-failed timbranfc-server 2>/dev/null || true
systemctl enable timbranfc-server
systemctl restart timbranfc-server

# Kiosk: SOLO autostart desktop (systemd kiosk fallisce senza sessione X completa)
systemctl disable --now timbranfc-kiosk 2>/dev/null || true

echo "Attendo avvio server (max 45s)..."
SERVER_OK=0
for _ in $(seq 1 45); do
    if curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1; then
        SERVER_OK=1
        break
    fi
    if ! systemctl is-active --quiet timbranfc-server 2>/dev/null; then
        sleep 1
        continue
    fi
    sleep 1
done

if [ "$SERVER_OK" -eq 1 ]; then
    HEALTH=$(curl -sf http://127.0.0.1:8080/health || true)
    echo "Server OK: http://$(hostname -I | awk '{print $1}'):8080"
    echo "Health: $HEALTH"
else
    echo "ERRORE: server non risponde su :8080"
    echo "--- timbranfc-server.service ---"
    grep -E '^(User|ExecStart|WorkingDirectory)=' /etc/systemd/system/timbranfc-server.service || true
    systemctl status timbranfc-server --no-pager -l || true
    journalctl -u timbranfc-server -n 25 --no-pager
    exit 1
fi

echo "Kiosk: usa autostart desktop (timbranfc-kiosk.service disabilitato)"
echo "  bash ${APP_DIR}/standalone/launch_kiosk.sh"
echo "  bash ${APP_DIR}/standalone/verify-kiosk.sh"

echo "Fatto. Dashboard: http://$(hostname -I | awk '{print $1}'):8080"
