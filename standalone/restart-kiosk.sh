#!/bin/bash
# Riavvia il kiosk (ferma loop + python, poi riavvia in background)
# bash standalone/restart-kiosk.sh

set -uo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
APP_USER="${APP_USER:-$(stat -c '%U' "$APP_DIR" 2>/dev/null || whoami)}"
LOG="${TIMBRANFC_KIOSK_LOG:-/tmp/timbranfc-kiosk.log}"
LOCK="/tmp/timbranfc-kiosk.lock"
LAUNCH="$APP_DIR/standalone/launch_kiosk.sh"
KIOSK_PY="$APP_DIR/standalone/run_kiosk.py"

_kiosk_running() {
    pgrep -f "$KIOSK_PY" >/dev/null 2>&1
}

_launch_running() {
    pgrep -f "$LAUNCH" >/dev/null 2>&1
}

echo "=== Riavvio kiosk TimbraNFC ==="
echo "Cartella: $APP_DIR"
echo "Utente:   $APP_USER"
echo ""

echo "1) Fermo processi esistenti..."
pkill -f "$KIOSK_PY" 2>/dev/null || true
pkill -f "$LAUNCH" 2>/dev/null || true
sleep 2
rm -f "$LOCK"

if _kiosk_running || _launch_running; then
    echo "   Avviso: qualche processo è ancora attivo — provo kill -9"
    pkill -9 -f "$KIOSK_PY" 2>/dev/null || true
    pkill -9 -f "$LAUNCH" 2>/dev/null || true
    sleep 1
    rm -f "$LOCK"
fi

echo "2) Verifica codice aggiornato..."
if [ -d "$APP_DIR/.git" ]; then
    _hash="$(git -C "$APP_DIR" rev-parse --short HEAD 2>/dev/null || echo '?')"
    echo "   git HEAD: $_hash  (se vecchio: cd $APP_DIR && git pull)"
fi

# shellcheck source=standalone/x-session-env.sh
source "$APP_DIR/standalone/x-session-env.sh"
import_graphical_session_env "$APP_USER" || true

if ! x_socket_ok; then
    echo "Avviso: DISPLAY/X non rilevato ora — launch_kiosk.sh attende il desktop."
else
    echo "Sessione grafica: DISPLAY=${DISPLAY:-?}"
fi

echo "3) Avvio kiosk in background..."
export APP_DIR APP_USER DISPLAY XAUTHORITY WAYLAND_DISPLAY XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS
nohup bash "$LAUNCH" >>"$LOG" 2>&1 &
_launch_pid=$!
sleep 2

if ! kill -0 "$_launch_pid" 2>/dev/null && ! _launch_running; then
    echo "ERRORE: launch_kiosk.sh terminato subito."
    echo "--- Log ($LOG) — ultime 15 righe ---"
    tail -15 "$LOG" 2>/dev/null || echo "(log assente)"
    exit 1
fi

echo "4) Attendo avvio run_kiosk.py (max 90s)..."
_ok=0
for _ in $(seq 1 90); do
    if _kiosk_running; then
        _ok=1
        break
    fi
    if ! _launch_running && ! kill -0 "$_launch_pid" 2>/dev/null; then
        echo "ERRORE: launch_kiosk.sh terminato prima dell'avvio del kiosk."
        break
    fi
    sleep 1
done

echo ""
if [ "$_ok" -eq 1 ]; then
    echo "OK — kiosk attivo:"
    pgrep -af "$KIOSK_PY" || true
    exit 0
fi

echo "ERRORE — kiosk NON avviato entro 90s (launch pid $_launch_pid)."
echo "--- Log ($LOG) — ultime 20 righe ---"
tail -20 "$LOG" 2>/dev/null || echo "(log assente)"
echo ""
echo "Avvio manuale: bash $LAUNCH"
exit 1
