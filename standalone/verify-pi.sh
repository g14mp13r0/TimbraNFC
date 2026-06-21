#!/bin/bash
# Diagnostica rapida sul Raspberry Pi
# bash standalone/verify-pi.sh

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "=== TimbraNFC verify ==="
echo "Cartella: $APP_DIR"
echo ""

echo "--- systemd server ---"
systemctl is-active timbranfc-server 2>&1 || true
grep -E '^(User|Group|ExecStart|WorkingDirectory)=' /etc/systemd/system/timbranfc-server.service 2>/dev/null || echo "(unit assente)"
echo ""

echo "--- systemd kiosk ---"
systemctl is-active timbranfc-kiosk 2>&1 || true
grep -E '^(User|ExecStart)=' /etc/systemd/system/timbranfc-kiosk.service 2>/dev/null || echo "(unit assente)"
echo ""

echo "--- health ---"
curl -sf http://127.0.0.1:8080/health && echo || echo "NON RISPONDE"
echo ""

echo "--- pagine dashboard (HTTP) ---"
FAIL=0
for path in / /dipendenti /timbrature /report /dispositivi /static/style.css; do
    code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8080${path}" || echo "000")
    echo "  ${path} -> ${code}"
    if [ "$code" != "200" ]; then
        FAIL=1
    fi
done
if [ "$FAIL" -eq 1 ]; then
    echo ""
    echo "  ERRORE: almeno una pagina non risponde 200 — log server:"
    journalctl -u timbranfc-server -n 15 --no-pager 2>/dev/null || true
fi
echo ""

echo "--- porta 8080 ---"
ss -tlnp 2>/dev/null | grep ':8080' || netstat -tlnp 2>/dev/null | grep ':8080' || echo "(nessun listener)"
echo ""

echo "--- display (kiosk) ---"
echo "DISPLAY=${DISPLAY:-<vuoto>}"
[ -S /tmp/.X11-unix/X0 ] && echo "X0: presente" || echo "X0: assente"
echo ""

echo "--- log server (ultime 8 righe) ---"
journalctl -u timbranfc-server -n 8 --no-pager 2>/dev/null || true
