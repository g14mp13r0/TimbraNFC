#!/bin/bash
# Riavvia il kiosk (ferma loop + python, poi riavvia in background)
# bash standalone/restart-kiosk.sh

set -uo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
APP_USER="${APP_USER:-$(stat -c '%U' "$APP_DIR" 2>/dev/null || whoami)}"
LOG="${TIMBRANFC_KIOSK_LOG:-/tmp/timbranfc-kiosk.log}"
LOCK="/tmp/timbranfc-kiosk.lock"
LAUNCH="$APP_DIR/standalone/launch_kiosk.sh"

echo "=== Riavvio kiosk TimbraNFC ==="
echo "Cartella: $APP_DIR"
echo "Utente:   $APP_USER"
echo ""

echo "1) Fermo processi esistenti..."
pkill -f "$APP_DIR/standalone/run_kiosk.py" 2>/dev/null || true
pkill -f "$LAUNCH" 2>/dev/null || true
sleep 2
rm -f "$LOCK"

if pgrep -f "$APP_DIR/standalone/run_kiosk.py" >/dev/null 2>&1 \
    || pgrep -f "$LAUNCH" >/dev/null 2>&1; then
    echo "   Avviso: qualche processo è ancora attivo — provo kill -9"
    pkill -9 -f "$APP_DIR/standalone/run_kiosk.py" 2>/dev/null || true
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
    echo "ERRORE: sessione grafica non disponibile (DISPLAY/X)."
    echo "  Accedi al desktop del Pi oppure: sudo bash $APP_DIR/standalone/setup-boot-kiosk.sh"
    echo "  Poi riprova: bash $APP_DIR/standalone/restart-kiosk.sh"
    exit 1
fi

echo "3) Avvio kiosk (DISPLAY=${DISPLAY:-?})..."
export APP_DIR APP_USER DISPLAY XAUTHORITY WAYLAND_DISPLAY XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS
nohup bash "$LAUNCH" >>"$LOG" 2>&1 &
_launch_pid=$!
sleep 2

_ok=0
for _ in $(seq 1 20); do
    if pgrep -f "$APP_DIR/standalone/run_kiosk.py" >/dev/null 2>&1; then
        _ok=1
        break
    fi
    sleep 1
done

echo ""
if [ "$_ok" -eq 1 ]; then
    echo "OK — kiosk attivo:"
    pgrep -af "$APP_DIR/standalone/run_kiosk.py" || true
    exit 0
fi

echo "ERRORE — kiosk NON avviato (launch pid $_launch_pid)."
echo "Controlla il log:"
echo ""
echo "--- Log ($LOG) — ultime 25 righe ---"
tail -25 "$LOG" 2>/dev/null || echo "(log assente)"
echo ""
echo "Monitoraggio: tail -f $LOG"
exit 1
