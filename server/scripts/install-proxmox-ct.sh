#!/bin/bash
# Installazione TimbraNFC Server su CT Proxmox (Debian 12 / Ubuntu 22.04+)
# Eseguire come root: bash server/scripts/install-proxmox-ct.sh

set -euo pipefail

APP_USER="${APP_USER:-timbranfc}"
APP_DIR="${APP_DIR:-/opt/timbranfc}"
DB_NAME="${DB_NAME:-timbranfc}"
DB_USER="${DB_USER:-timbranfc}"
DB_PASS="${DB_PASS:-$(openssl rand -base64 18 | tr -dc 'a-zA-Z0-9' | head -c 24)}"

echo "=== TimbraNFC — installazione server su CT ==="

# --- Dipendenze di sistema ---
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
    python3 python3-pip python3-venv git \
    mariadb-server mariadb-client \
    nginx openssl \
    curl

# --- MariaDB ---
systemctl enable --now mariadb

mysql -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';"
mysql -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';"
mysql -e "FLUSH PRIVILEGES;"

# --- Utente applicazione ---
if ! id "$APP_USER" &>/dev/null; then
    useradd -r -m -d "$APP_DIR" -s /bin/bash "$APP_USER"
fi

# --- Codice (se non già presente) ---
if [ ! -f "$APP_DIR/server/app/main.py" ]; then
    echo "Clono repository..."
    apt-get install -y git
    git clone https://github.com/g14mp13r0/TimbraNFC.git "$APP_DIR"
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
fi

# --- Virtualenv ---
sudo -u "$APP_USER" bash <<EOF
cd "$APP_DIR"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements-server.txt
EOF

# --- Config .env ---
ENV_FILE="$APP_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    API_KEY=$(openssl rand -hex 24)
    SECRET_KEY=$(openssl rand -hex 32)
    cat > "$ENV_FILE" <<EOF
DATABASE_URL=mysql+pymysql://${DB_USER}:${DB_PASS}@localhost/${DB_NAME}
API_KEY=${API_KEY}
SECRET_KEY=${SECRET_KEY}
ADMIN_EMAIL=admin@local
ADMIN_PASSWORD=admin
DEFAULT_SEDE_ID=1
EOF
    chown "$APP_USER:$APP_USER" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo ""
    echo ">>> Credenziali generate in ${ENV_FILE}"
    echo ">>> Dashboard: admin@local / admin  (CAMBIARE SUBITO)"
    echo ">>> API_KEY per i terminali: ${API_KEY}"
fi

# --- Seed database ---
sudo -u "$APP_USER" bash <<EOF
set -a
source "$ENV_FILE"
set +a
cd "$APP_DIR"
.venv/bin/python server/scripts/seed.py
EOF

# --- Alembic (create tables via SQLAlchemy se seed non basta) ---
sudo -u "$APP_USER" bash <<EOF
set -a
source "$ENV_FILE"
set +a
cd "$APP_DIR"
.venv/bin/alembic -c server/migrations/alembic.ini upgrade head 2>/dev/null || true
EOF

# --- Systemd ---
sed "s|/home/pi/TimbraNFC|${APP_DIR}|g; s|User=pi|User=${APP_USER}|g; s|/usr/bin/python3|${APP_DIR}/.venv/bin/python|g" \
    "$APP_DIR/server/systemd/timbranfc-server.service" > /etc/systemd/system/timbranfc-server.service

systemctl daemon-reload
systemctl enable --now timbranfc-server

# --- Nginx (HTTP, TLS opzionale sotto) ---
cat > /etc/nginx/sites-available/timbranfc <<'NGINX'
server {
    listen 80;
    server_name _;

    client_max_body_size 2m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/timbranfc /etc/nginx/sites-enabled/timbranfc
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

IP=$(hostname -I | awk '{print $1}')
echo ""
echo "=== Installazione completata ==="
echo "Dashboard:  http://${IP}/"
echo "API docs:   http://${IP}/docs"
echo "Config:     ${ENV_FILE}"
echo ""
echo "Sui terminali Raspberry impostare:"
echo "  SERVER_URL=http://${IP}"
echo "  API_KEY=<valore in .env>"
