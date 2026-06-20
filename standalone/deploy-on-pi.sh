#!/bin/bash
# Aggiorna repo e corregge servizi systemd sul Raspberry Pi
# Uso: bash standalone/deploy-on-pi.sh

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP_DIR"

echo "=== TimbraNFC deploy ==="
git pull
sudo bash "$APP_DIR/standalone/fix-services.sh"
