#!/bin/bash
# Installazione TimbraNFC standalone su Raspberry Pi
# Uso: sudo bash standalone/install-raspberry.sh
#      sudo APP_USER=gpastorino bash standalone/install-raspberry.sh

set -euo pipefail

APP_USER="${APP_USER:-${SUDO_USER:-$(logname 2>/dev/null || echo pi)}}"
APP_DIR="${APP_DIR:-/home/${APP_USER}/TimbraNFC}"
APP_GROUP="$(id -gn "$APP_USER" 2>/dev/null || echo "$APP_USER")"

echo "=== TimbraNFC Standalone — Raspberry Pi ==="
echo "Utente: $APP_USER"
echo "Cartella: $APP_DIR"

export DEBIAN_FRONTEND=noninteractive

# Ripara apt se un pacchetto armhf (es. xinput-calibrator) ha rotto le dipendenze
if dpkg -l xinput-calibrator 2>/dev/null | grep -q ^ii; then
    echo "Rimuovo xinput-calibrator (pacchetto armhf incompatibile con OS 64-bit)..."
    apt-get remove --purge -y xinput-calibrator || true
fi
apt-get --fix-broken install -y || true

apt-get update
apt-get install -y \
    python3 python3-venv python3-pip python3-dev python3-tk git \
    pcscd libccid swig libpcsclite-dev \
    build-essential x11-xserver-utils

systemctl enable --now pcscd || echo "Avviso: pcscd non avviato — collegare NFC e riprovare"

if [ ! -d "$APP_DIR" ]; then
    echo "Errore: $APP_DIR non trovato. Clona prima il repo in quella cartella."
    exit 1
fi
chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"

# Virtualenv
sudo -u "$APP_USER" bash <<EOF
set -e
cd "$APP_DIR"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements-server.txt -r requirements-terminal.txt
EOF

# Config
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.standalone.example" "$APP_DIR/.env"
fi
chown "$APP_USER:$APP_GROUP" "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"
mkdir -p "$APP_DIR/data"
chown "$APP_USER:$APP_GROUP" "$APP_DIR/data"

# Seed DB
sudo -u "$APP_USER" bash <<EOF
set -e
set -a
source "$APP_DIR/.env"
set +a
cd "$APP_DIR"
.venv/bin/python server/scripts/seed.py
EOF

# Systemd — generati per l'utente corrente (non hardcoded /home/pi)
cat > /etc/systemd/system/timbranfc-server.service <<UNIT
[Unit]
Description=TimbraNFC — Server e dashboard web (LAN)
After=network.target
Before=timbranfc-kiosk.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${APP_DIR}
EnvironmentFile=-${APP_DIR}/.env
Environment=STANDALONE=1
Environment=TIMBRANFC_DATA=${APP_DIR}/data
Environment=SERVER_HOST=0.0.0.0
Environment=SERVER_PORT=8080
ExecStart=${APP_DIR}/.venv/bin/python standalone/run_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

chmod +x "$APP_DIR/standalone/launch_kiosk.sh"

# Autostart al login desktop (metodo più affidabile del solo systemd)
AUTOSTART_DIR="/home/${APP_USER}/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
sed "s|/home/gpastorino/TimbraNFC|${APP_DIR}|g" \
    "$APP_DIR/standalone/autostart/timbranfc-kiosk.desktop" \
    > "$AUTOSTART_DIR/timbranfc-kiosk.desktop"
chown "$APP_USER:$APP_GROUP" "$AUTOSTART_DIR/timbranfc-kiosk.desktop"

cat > /etc/systemd/system/timbranfc-kiosk.service <<UNIT
[Unit]
Description=TimbraNFC — Kiosk timbratrice (solo touchscreen)
After=timbranfc-server.service graphical.target pcscd.service
Requires=timbranfc-server.service
Wants=pcscd.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_GROUP}
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
StartLimitIntervalSec=120
StartLimitBurst=5

[Install]
WantedBy=graphical.target
UNIT

systemctl daemon-reload
systemctl enable timbranfc-server
systemctl restart timbranfc-server
sleep 2
systemctl enable timbranfc-kiosk || true
systemctl restart timbranfc-kiosk || echo "Kiosk systemd: usa autostart al login se fallisce"

IP=$(hostname -I | awk '{print $1}')
echo ""
echo "=== Installazione completata ==="
echo "Timbratrice: touchscreen (kiosk)"
echo "Dashboard:   http://${IP}:8080"
echo "Utente app:  ${APP_USER}"
echo ""
echo "  sudo systemctl status timbranfc-server timbranfc-kiosk"
echo "  journalctl -u timbranfc-kiosk -f"
echo "  (oppure il kiosk parte da autostart al login desktop)"
