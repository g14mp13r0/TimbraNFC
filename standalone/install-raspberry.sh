#!/bin/bash
# Installazione TimbraNFC standalone su Raspberry Pi
# Eseguire come root o con sudo: bash standalone/install-raspberry.sh

set -euo pipefail

APP_USER="${APP_USER:-pi}"
APP_DIR="${APP_DIR:-/home/pi/TimbraNFC}"

echo "=== TimbraNFC Standalone — Raspberry Pi ==="

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 python3-venv python3-pip git pcscd libusb-dev nginx

systemctl enable --now pcscd

# Codice
if [ ! -d "$APP_DIR/.git" ]; then
    git clone https://github.com/g14mp13r0/TimbraNFC.git "$APP_DIR"
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# Virtualenv (server + terminal)
sudo -u "$APP_USER" bash <<EOF
cd "$APP_DIR"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements-server.txt -r requirements-terminal.txt
EOF

# Config
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.standalone.example" "$APP_DIR/.env"
    chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
fi

mkdir -p "$APP_DIR/data"
chown "$APP_USER:$APP_USER" "$APP_DIR/data"

# Seed DB
sudo -u "$APP_USER" bash <<EOF
set -a
source "$APP_DIR/.env"
set +a
cd "$APP_DIR"
.venv/bin/python server/scripts/seed.py
EOF

# Systemd
cp "$APP_DIR/standalone/systemd/timbranfc-server.service" /etc/systemd/system/
cp "$APP_DIR/standalone/systemd/timbranfc-kiosk.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable timbranfc-server timbranfc-kiosk
systemctl restart timbranfc-server
systemctl restart timbranfc-kiosk || echo "Kiosk: avviare dopo login grafico (DISPLAY=:0)"

IP=$(hostname -I | awk '{print $1}')
echo ""
echo "=== Installazione completata ==="
echo "Timbratrice: touchscreen del Raspberry (kiosk)"
echo "Dashboard:   http://${IP}:8080  (da qualsiasi PC in rete)"
echo "API docs:    http://${IP}:8080/docs"
echo "Login admin: admin@local / admin  (cambiare in .env)"
echo ""
echo "Comandi utili:"
echo "  sudo systemctl status timbranfc-server timbranfc-kiosk"
echo "  journalctl -u timbranfc-kiosk -f"
