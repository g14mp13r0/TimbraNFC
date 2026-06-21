#!/bin/bash
# Ripristino rapido quando dashboard e kiosk non rispondono
# bash standalone/recover-pi.sh
# sudo NETWORK_RESET=1 bash standalone/recover-pi.sh   # forza DHCP su Ethernet

set -uo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
APP_USER="${APP_USER:-$(stat -c '%U' "$APP_DIR" 2>/dev/null || whoami)}"
VENV="$APP_DIR/.venv/bin/python"
PORT="${SERVER_PORT:-8080}"

if [ -f "$APP_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$APP_DIR/.env"
    set +a
    PORT="${SERVER_PORT:-8080}"
fi

echo "=========================================="
echo " TimbraNFC — ripristino server + kiosk"
echo "=========================================="
echo "Cartella: $APP_DIR"
echo "Utente:   $APP_USER"
echo ""

echo "--- 1) Rete ---"
ip -4 addr show 2>/dev/null | grep -E 'inet ' || true
ip route show default 2>/dev/null || echo "(nessun gateway)"
echo ""

if [ "${NETWORK_RESET:-0}" = "1" ] && [ "$(id -u)" -eq 0 ]; then
    echo "→ Reset rete Ethernet su DHCP (TimbraNFC-LAN o prima connessione eth)"
    if command -v nmcli >/dev/null 2>&1; then
        if nmcli -t -f NAME connection show | grep -Fx "TimbraNFC-LAN" >/dev/null 2>&1; then
            nmcli connection modify TimbraNFC-LAN ipv4.method auto ipv4.addresses "" ipv4.gateway "" ipv4.dns ""
            nmcli connection modify TimbraNFC-LAN connection.autoconnect yes
            nmcli connection down TimbraNFC-WLAN 2>/dev/null || true
            nmcli connection up TimbraNFC-LAN || true
        else
            ETH=$(nmcli -t -f DEVICE,TYPE device status 2>/dev/null | awk -F: '$2=="ethernet"{print $1; exit}')
            if [ -n "$ETH" ]; then
                nmcli device connect "$ETH" 2>/dev/null || true
            fi
        fi
        sleep 3
        ip -4 addr show "$ETH" 2>/dev/null | grep inet || ip -4 addr show | grep inet
    else
        echo "nmcli assente — salta reset rete"
    fi
    echo ""
fi

echo "--- 2) Dipendenze Python ---"
if [ ! -x "$VENV" ]; then
    echo "ERRORE: venv assente ($VENV)"
    echo "  cd $APP_DIR && python3 -m venv .venv && .venv/bin/pip install -r requirements-server.txt"
    exit 1
fi
if ! "$VENV" -c "import fastapi, uvicorn" 2>/dev/null; then
    echo "→ Reinstallo requirements-server.txt"
    "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements-server.txt"
fi
if ! "$VENV" -c "import itsdangerous" 2>/dev/null; then
    echo "→ Installo itsdangerous (sessioni login)"
    "$APP_DIR/.venv/bin/pip" install 'itsdangerous>=2.1.0'
fi
if ! "$VENV" -c "import reportlab" 2>/dev/null; then
    echo "→ Installo reportlab (export PDF)"
    "$APP_DIR/.venv/bin/pip" install 'reportlab>=4.0.0'
fi
if ! "$VENV" -c "import weasyprint" 2>/dev/null; then
    echo "→ Installo weasyprint (report turni PDF da HTML)"
    if command -v apt-get >/dev/null 2>&1; then
        echo "  (su Debian/Raspberry Pi: apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0)"
    fi
    "$APP_DIR/.venv/bin/pip" install 'weasyprint>=62.0'
fi
if ! "$VENV" -c "from server.app.main import app" 2>/dev/null; then
    echo "ERRORE: server non importabile:"
    cd "$APP_DIR" && "$VENV" -c "from server.app.main import app" 2>&1 || true
    exit 1
fi
echo "OK import server"
echo ""

echo "--- 3) Correggo SERVER_PORT non valido in .env ---"
if [ -f "$APP_DIR/.env" ] && grep -q '^SERVER_PORT=' "$APP_DIR/.env"; then
    sp=$(grep '^SERVER_PORT=' "$APP_DIR/.env" | cut -d= -f2- | tr -d '"' | tr -d "'")
    if ! [[ "$sp" =~ ^[0-9]+$ ]] || [ "$sp" -lt 1 ] || [ "$sp" -gt 65535 ]; then
        echo "  SERVER_PORT invalido ($sp) → 8080"
        sed -i 's/^SERVER_PORT=.*/SERVER_PORT=8080/' "$APP_DIR/.env"
        PORT=8080
    fi
fi
echo ""

echo "--- 4) Riavvio server systemd ---"
if systemctl is-enabled timbranfc-server >/dev/null 2>&1; then
    sudo systemctl restart timbranfc-server 2>/dev/null || systemctl restart timbranfc-server 2>/dev/null || true
    sleep 2
    systemctl is-active timbranfc-server 2>&1 || true
    echo ""
    echo "Log server (ultime 12 righe):"
    journalctl -u timbranfc-server -n 12 --no-pager 2>/dev/null || true
else
    echo "timbranfc-server non installato — avvio manuale temporaneo"
    pkill -f "standalone/run_server.py" 2>/dev/null || true
    sleep 1
    cd "$APP_DIR" && nohup "$VENV" "$APP_DIR/standalone/run_server.py" >/tmp/timbranfc-server-manual.log 2>&1 &
    sleep 2
fi
echo ""

echo "--- 5) Test locale http://127.0.0.1:${PORT} ---"
if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null; then
    echo "OK health"
    curl -s -o /dev/null -w "GET / → HTTP %{http_code}\n" "http://127.0.0.1:${PORT}/"
else
    echo "NON RISPONDE su porta $PORT"
    echo "Log manuale: tail -30 /tmp/timbranfc-server-manual.log"
    journalctl -u timbranfc-server -n 20 --no-pager 2>/dev/null || true
fi
echo ""

echo "--- 6) IP LAN (apri nel browser da un altro PC) ---"
LAN_IP=$(ip -4 route get 8.8.8.8 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1); exit}')
if [ -n "$LAN_IP" ]; then
    echo "  http://${LAN_IP}:${PORT}/"
else
    echo "  (IP LAN non rilevato — controlla cavo WiFi / rete)"
fi
echo ""

echo "--- 7) Avvio automatico kiosk ---"
if [ ! -f "/home/${APP_USER}/.config/systemd/user/timbranfc-kiosk.service" ] \
    && [ ! -f "/home/${APP_USER}/.config/autostart/timbranfc-kiosk.desktop" ]; then
    echo "Autostart kiosk non configurato."
    if [ "$(id -u)" -eq 0 ]; then
        bash "$APP_DIR/standalone/setup-boot-kiosk.sh"
    else
        echo "  Esegui: sudo bash $APP_DIR/standalone/setup-boot-kiosk.sh"
    fi
else
    bash "$APP_DIR/standalone/verify-kiosk.sh" 2>/dev/null || true
fi
echo ""

echo "--- 8) Riavvio kiosk ---"
if [ -x "$APP_DIR/standalone/restart-kiosk.sh" ]; then
    bash "$APP_DIR/standalone/restart-kiosk.sh" || true
else
    echo "restart-kiosk.sh assente"
fi
echo ""
echo "Fine. Se la web non è raggiungibile da LAN: sudo NETWORK_RESET=1 bash $APP_DIR/standalone/recover-pi.sh"
