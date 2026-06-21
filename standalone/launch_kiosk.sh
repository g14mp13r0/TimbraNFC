#!/bin/bash
# Avvia kiosk timbratrice (DISPLAY + server locale)
set -uo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
APP_USER="${APP_USER:-$(stat -c '%U' "$APP_DIR" 2>/dev/null || whoami)}"
LOG="${TIMBRANFC_KIOSK_LOG:-/tmp/timbranfc-kiosk.log}"
LOCK="/tmp/timbranfc-kiosk.lock"

exec >>"$LOG" 2>&1

cd "$APP_DIR"
[ -f "$APP_DIR/.env" ] && set -a && source "$APP_DIR/.env" && set +a

export STANDALONE="${STANDALONE:-1}"
export TIMBRANFC_DATA="${TIMBRANFC_DATA:-$APP_DIR/data}"
export SERVER_URL="${SERVER_URL:-http://127.0.0.1:8080}"
export NFC_AUTO_TIMBRATURA="${NFC_AUTO_TIMBRATURA:-1}"
export APP_DIR APP_USER

# pcscd si configura con sudo (fix-services / pcscd-on.sh) — mai systemctl start/stop
# come utente normale: polkit chiede la password e blocca l'autostart del kiosk.
_check_pcscd() {
    local backend="${NFC_BACKEND:-auto}"
    if [ "$(id -u)" -eq 0 ]; then
        if [ "$backend" = "nfcpy" ]; then
            systemctl stop pcscd.service pcscd.socket 2>/dev/null || true
            systemctl mask pcscd.socket 2>/dev/null || true
        elif [ "$backend" = "pcsc" ] || [ "$backend" = "auto" ]; then
            systemctl unmask pcscd.socket pcscd.service 2>/dev/null || true
            systemctl start pcscd.socket pcscd.service 2>/dev/null || true
        fi
        return
    fi
    if [ "$backend" = "pcsc" ] || [ "$backend" = "auto" ]; then
        if ! systemctl is-active --quiet pcscd.service 2>/dev/null; then
            echo "$(date -Iseconds) Avviso: pcscd non attivo — esegui una volta: sudo bash $APP_DIR/standalone/pcscd-on.sh"
        fi
    elif [ "$backend" = "nfcpy" ]; then
        if systemctl is-active --quiet pcscd.socket 2>/dev/null \
            || systemctl is-active --quiet pcscd.service 2>/dev/null; then
            echo "$(date -Iseconds) Avviso: pcscd attivo con NFC_BACKEND=nfcpy — sudo bash $APP_DIR/standalone/pcscd-off.sh"
        fi
    fi
}

LAUNCH_LOCK="/tmp/timbranfc-kiosk.launch.lock"
exec 9>"$LAUNCH_LOCK"
if ! flock -n 9; then
    echo "$(date -Iseconds) launch_kiosk.sh già in esecuzione — esco"
    exit 0
fi

PY="$APP_DIR/.venv/bin/python"
KIOSK="$APP_DIR/standalone/run_kiosk.py"

_graphical_ready() {
    local uid
    uid="$(id -u "$APP_USER" 2>/dev/null || id -u)"
    if [ -S /tmp/.X11-unix/X0 ] || [ -S /tmp/.X11-unix/X1 ]; then
        return 0
    fi
    if [ -n "${XDG_RUNTIME_DIR:-}" ] && [ -S "${XDG_RUNTIME_DIR}/wayland-0" ]; then
        return 0
    fi
    if [ -S "/run/user/${uid}/wayland-0" ] || [ -S "/run/user/${uid}/wayland-1" ]; then
        return 0
    fi
    # shellcheck source=standalone/x-session-env.sh
    source "$APP_DIR/standalone/x-session-env.sh"
    if import_graphical_session_env "$APP_USER" 2>/dev/null; then
        if x_socket_ok; then
            return 0
        fi
        if [ -n "${WAYLAND_DISPLAY:-}" ]; then
            return 0
        fi
    fi
    return 1
}

_wait_for_display() {
    local i
    for i in $(seq 1 90); do
        if _graphical_ready; then
            return 0
        fi
        sleep 2
    done
    return 1
}

_start_python() {
    export DISPLAY XAUTHORITY WAYLAND_DISPLAY XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS
    echo "$(date -Iseconds) Avvio kiosk DISPLAY=$DISPLAY NFC_BACKEND=${NFC_BACKEND:-?}"
    if [ ! -x "$PY" ]; then
        echo "$(date -Iseconds) ERRORE: Python venv assente: $PY"
        return 127
    fi
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
    echo "=== $(date -Iseconds) launch_kiosk.sh (user=$APP_USER pid=$$) ==="

    if [ -f "$LOCK" ]; then
        _old_pid="$(cat "$LOCK" 2>/dev/null || true)"
        if [ -n "$_old_pid" ] && kill -0 "$_old_pid" 2>/dev/null; then
            echo "$(date -Iseconds) Kiosk già attivo (pid $_old_pid)"
            sleep 30
            continue
        fi
        rm -f "$LOCK"
    fi

    if ! _wait_for_display; then
        echo "$(date -Iseconds) Attendo sessione grafica (X11/Wayland)..."
        sleep 10
        continue
    fi

    # shellcheck source=standalone/x-session-env.sh
    source "$APP_DIR/standalone/x-session-env.sh"
    import_graphical_session_env "$APP_USER" || true
    if ! _graphical_ready; then
        echo "$(date -Iseconds) Attendo DISPLAY/XAUTHORITY/WAYLAND..."
        sleep 10
        continue
    fi

    _check_pcscd

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
