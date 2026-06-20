#!/bin/bash
# Avvia kiosk timbratrice (DISPLAY + server locale)
set -uo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
APP_USER="${APP_USER:-$(whoami)}"
LOG="${TIMBRANFC_KIOSK_LOG:-/tmp/timbranfc-kiosk.log}"
LOCK="/tmp/timbranfc-kiosk.lock"

exec >>"$LOG" 2>&1

cd "$APP_DIR"
[ -f "$APP_DIR/.env" ] && set -a && source "$APP_DIR/.env" && set +a

export STANDALONE="${STANDALONE:-1}"
export TIMBRANFC_DATA="${TIMBRANFC_DATA:-$APP_DIR/data}"
export SERVER_URL="${SERVER_URL:-http://127.0.0.1:8080}"
export NFC_AUTO_TIMBRATURA="${NFC_AUTO_TIMBRATURA:-1}"

# Un solo kiosk (lock file)
if [ -f "$LOCK" ]; then
    _old_pid="$(cat "$LOCK" 2>/dev/null || true)"
    if [ -n "$_old_pid" ] && kill -0 "$_old_pid" 2>/dev/null; then
        echo "$(date -Iseconds) Kiosk già attivo (pid $_old_pid)"
        exit 0
    fi
fi

for i in $(seq 1 90); do
    if [ -S /tmp/.X11-unix/X0 ] || [ -S /tmp/.X11-unix/X1 ]; then
        break
    fi
    sleep 2
done

# shellcheck source=standalone/x-session-env.sh
source "$APP_DIR/standalone/x-session-env.sh"

if ! x_socket_ok; then
    echo "$(date -Iseconds) ERRORE: socket X assente"
    exit 1
fi

if [ "${NFC_BACKEND:-auto}" = "nfcpy" ]; then
    systemctl stop pcscd.service pcscd.socket 2>/dev/null || true
    systemctl mask pcscd.socket 2>/dev/null || true
elif [ "${NFC_BACKEND:-auto}" = "pcsc" ]; then
    systemctl unmask pcscd.socket pcscd.service 2>/dev/null || true
    systemctl start pcscd.socket pcscd.service 2>/dev/null || true
fi

PY="$APP_DIR/.venv/bin/python"
KIOSK="$APP_DIR/standalone/run_kiosk.py"

_start_python() {
    export DISPLAY XAUTHORITY WAYLAND_DISPLAY XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS
    echo "$(date -Iseconds) Avvio kiosk DISPLAY=$DISPLAY NFC_BACKEND=${NFC_BACKEND:-?}"
    if [ "${NFC_BACKEND:-auto}" = "pcsc" ] && getent group scard >/dev/null 2>&1 \
        && id -nG "$APP_USER" 2>/dev/null | grep -qw scard \
        && ! id -nG 2>/dev/null | grep -qw scard; then
        sg scard -c "export DISPLAY='$DISPLAY' XAUTHORITY='${XAUTHORITY:-}' WAYLAND_DISPLAY='${WAYLAND_DISPLAY:-}' XDG_RUNTIME_DIR='$XDG_RUNTIME_DIR'; exec '$PY' '$KIOSK'"
        return $?
    fi
    "$PY" "$KIOSK"
}

while true; do
    echo ""
    echo "=== $(date -Iseconds) launch_kiosk.sh (user=$APP_USER) ==="

    for i in $(seq 1 30); do
        if curl -sf "${SERVER_URL}/health" >/dev/null 2>&1; then
            echo "Server OK: $SERVER_URL"
            break
        fi
        [ "$i" -eq 30 ] && echo "Avviso: server non pronto, avvio comunque"
        sleep 2
    done

    _start_python
    _rc=$?
    echo "$(date -Iseconds) Kiosk terminato (exit $_rc) — riavvio tra 5s"
    rm -f "$LOCK"
    sleep 5
done
