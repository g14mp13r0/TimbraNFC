#!/bin/bash
# Cancella comandi remoti pendenti (es. restart_kiosk bloccato in loop)
# bash standalone/clear-pending-commands.sh

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
UUID_FILE="${APP_DIR}/data/device_uuid"
SERVER="${SERVER_URL:-http://127.0.0.1:8080}"

[ -f "$APP_DIR/.env" ] && set -a && source "$APP_DIR/.env" && set +a
SERVER="${SERVER_URL:-$SERVER}"

if [ ! -f "$UUID_FILE" ]; then
    echo "File device UUID non trovato: $UUID_FILE"
    exit 1
fi

UUID="$(tr -d '[:space:]' < "$UUID_FILE")"
echo "Device UUID: $UUID"

"$APP_DIR/.venv/bin/python" <<PY
import sys
sys.path.insert(0, "${APP_DIR}")
import requests
from server.app.db import SessionLocal
from server.app.models import DeviceComando, Dispositivo

uuid = "${UUID}"
db = SessionLocal()
dev = db.query(Dispositivo).filter(Dispositivo.device_uuid == uuid).first()
if not dev:
    print("Dispositivo non trovato nel DB")
    sys.exit(1)
pending = (
    db.query(DeviceComando)
    .filter(DeviceComando.dispositivo_id == dev.id, DeviceComando.eseguito == False)
    .all()
)
if not pending:
    print("Nessun comando pendente.")
    sys.exit(0)
for cmd in pending:
    cmd.eseguito = True
    print(f"Annullato: id={cmd.id} tipo={cmd.tipo}")
db.commit()
print("Fatto.")
PY

echo ""
echo "Riavvia kiosk:"
echo "  pkill -f run_kiosk.py || true"
echo "  bash ${APP_DIR}/standalone/launch_kiosk.sh"
