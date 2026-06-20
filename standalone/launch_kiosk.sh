#!/bin/bash
# Avvia kiosk con DISPLAY/XAUTHORITY corretti (Raspberry Pi OS Desktop)
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
APP_USER="${APP_USER:-$(whoami)}"

cd "$APP_DIR"
[ -f "$APP_DIR/.env" ] && set -a && source "$APP_DIR/.env" && set +a

export STANDALONE="${STANDALONE:-1}"
export TIMBRANFC_DATA="${TIMBRANFC_DATA:-$APP_DIR/data}"
export SERVER_URL="${SERVER_URL:-http://127.0.0.1:8080}"

# Attendi sessione grafica (max 60s)
for i in $(seq 1 30); do
    if [ -S "/tmp/.X11-unix/X0" ] || [ -S "/tmp/.X11-unix/X1" ]; then
        break
    fi
    sleep 2
done

# shellcheck source=standalone/x-session-env.sh
source "$APP_DIR/standalone/x-session-env.sh"

if ! x_session_ok; then
    echo "ERRORE: sessione grafica non disponibile (DISPLAY=$DISPLAY)" >&2
    echo "Da SSH: sudo bash standalone/setup-remote-desktop.sh && sudo reboot" >&2
    exit 1
fi

# Touchscreen SPI: mappa input sul display corretto
if [ -x "$APP_DIR/standalone/fix-touchscreen.sh" ]; then
    bash "$APP_DIR/standalone/fix-touchscreen.sh" --quiet 2>/dev/null || true
fi

exec "$APP_DIR/.venv/bin/python" "$APP_DIR/standalone/run_kiosk.py"
