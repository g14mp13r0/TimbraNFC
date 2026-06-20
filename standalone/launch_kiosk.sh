#!/bin/bash
# Avvia kiosk timbratrice (DISPLAY + server locale)
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
APP_USER="${APP_USER:-$(whoami)}"
LOG="${TIMBRANFC_KIOSK_LOG:-/tmp/timbranfc-kiosk.log}"

exec >>"$LOG" 2>&1
echo ""
echo "=== $(date -Iseconds) launch_kiosk.sh (user=$APP_USER) ==="

cd "$APP_DIR"
[ -f "$APP_DIR/.env" ] && set -a && source "$APP_DIR/.env" && set +a

export STANDALONE="${STANDALONE:-1}"
export TIMBRANFC_DATA="${TIMBRANFC_DATA:-$APP_DIR/data}"
export SERVER_URL="${SERVER_URL:-http://127.0.0.1:8080}"
export NFC_AUTO_TIMBRATURA="${NFC_AUTO_TIMBRATURA:-1}"

# Evita doppio avvio
if pgrep -f "$APP_DIR/standalone/run_kiosk.py" >/dev/null 2>&1; then
    echo "Kiosk già in esecuzione — esco"
    exit 0
fi

# Attendi socket X (autostart può partire prima del desktop)
for i in $(seq 1 45); do
    if [ -S /tmp/.X11-unix/X0 ] || [ -S /tmp/.X11-unix/X1 ]; then
        break
    fi
    sleep 2
done

# shellcheck source=standalone/x-session-env.sh
source "$APP_DIR/standalone/x-session-env.sh"

echo "DISPLAY=$DISPLAY XAUTHORITY=${XAUTHORITY:-} WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-}"

if ! x_socket_ok; then
    echo "ERRORE: socket X assente — serve desktop autologin attivo" >&2
    echo "  sudo bash $APP_DIR/standalone/setup-remote-desktop.sh && sudo reboot" >&2
    exit 1
fi

if ! x_session_ok; then
    echo "Avviso: xrandr non risponde (normale su Pi OS) — avvio kiosk comunque"
fi

# Touch solo se serve selezione manuale IT/IP/FP/FT
if [ "${NFC_AUTO_TIMBRATURA}" != "1" ] && [ -x "$APP_DIR/standalone/fix-touchscreen.sh" ]; then
    bash "$APP_DIR/standalone/fix-touchscreen.sh" --quiet 2>/dev/null || true
fi

# Attendi server (max 60s) — run_kiosk ha un secondo tentativo
for i in $(seq 1 30); do
    if curl -sf "${SERVER_URL}/health" >/dev/null 2>&1; then
        echo "Server OK: $SERVER_URL"
        break
    fi
    [ "$i" -eq 30 ] && echo "Avviso: server non ancora pronto, run_kiosk riproverà"
    sleep 2
done

echo "Avvio run_kiosk.py..."
exec "$APP_DIR/.venv/bin/python" "$APP_DIR/standalone/run_kiosk.py"
