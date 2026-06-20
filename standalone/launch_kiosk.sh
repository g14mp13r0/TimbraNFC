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

# DISPLAY
if [ -z "${DISPLAY:-}" ]; then
    if [ -S /tmp/.X11-unix/X0 ]; then
        export DISPLAY=:0
    elif [ -S /tmp/.X11-unix/X1 ]; then
        export DISPLAY=:1
    else
        export DISPLAY=:0
    fi
fi

# XAUTHORITY — prova percorsi comuni su Pi OS
if [ -z "${XAUTHORITY:-}" ] || [ ! -f "$XAUTHORITY" ]; then
    UID_NUM="$(id -u "$APP_USER" 2>/dev/null || id -u)"
    for xa in \
        "/home/${APP_USER}/.Xauthority" \
        "/run/user/${UID_NUM}/gdm/Xauthority" \
        "/run/user/${UID_NUM}/.mutter-Xwaylandauth."* \
        "/run/user/${UID_NUM}/.Xauthority"; do
        if [ -f "$xa" ]; then
            export XAUTHORITY="$xa"
            break
        fi
    done
fi

# Verifica X11 (tkinter non funziona su Wayland puro)
if command -v xdpyinfo &>/dev/null; then
    if ! xdpyinfo >/dev/null 2>&1; then
        echo "ERRORE: display X11 non disponibile (DISPLAY=$DISPLAY)" >&2
        echo "Suggerimento: usa sessione desktop X11 o avvia dopo login grafico" >&2
        exit 1
    fi
fi

exec "$APP_DIR/.venv/bin/python" "$APP_DIR/standalone/run_kiosk.py"
