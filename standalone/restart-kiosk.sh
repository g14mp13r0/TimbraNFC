#!/bin/bash
# Riavvia il kiosk (ferma loop + python, poi riavvia in background)
# bash standalone/restart-kiosk.sh

set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
LOG="${TIMBRANFC_KIOSK_LOG:-/tmp/timbranfc-kiosk.log}"
LOCK="/tmp/timbranfc-kiosk.lock"

echo "=== Riavvio kiosk TimbraNFC ==="
echo "Cartella: $APP_DIR"
echo ""

echo "1) Fermo processi esistenti..."
pkill -f run_kiosk.py 2>/dev/null || true
pkill -f launch_kiosk.sh 2>/dev/null || true
sleep 2
rm -f "$LOCK"

if pgrep -f run_kiosk.py >/dev/null 2>&1 || pgrep -f launch_kiosk.sh >/dev/null 2>&1; then
    echo "   Avviso: qualche processo è ancora attivo — provo kill -9"
    pkill -9 -f run_kiosk.py 2>/dev/null || true
    pkill -9 -f launch_kiosk.sh 2>/dev/null || true
    sleep 1
    rm -f "$LOCK"
fi

echo "2) Verifica codice aggiornato..."
if [ -d "$APP_DIR/.git" ]; then
    _hash="$(git -C "$APP_DIR" rev-parse --short HEAD 2>/dev/null || echo '?')"
    echo "   git HEAD: $_hash  (se vecchio: cd $APP_DIR && git pull)"
fi

echo "3) Avvio kiosk in background..."
nohup bash "$APP_DIR/standalone/launch_kiosk.sh" >/dev/null 2>&1 &
sleep 4

echo ""
if pgrep -f run_kiosk.py >/dev/null 2>&1; then
    echo "OK — kiosk attivo:"
    pgrep -af run_kiosk.py || true
else
    echo "ERRORE — kiosk NON avviato."
    echo "Controlla il log:"
fi

echo ""
echo "--- Log ($LOG) — ultime 20 righe ---"
tail -20 "$LOG" 2>/dev/null || echo "(log assente)"
echo ""
echo "Monitoraggio: tail -f $LOG"
