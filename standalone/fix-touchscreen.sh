#!/bin/bash
# Mappa il touch sul display corretto (3.5" SPI 480x320)
# Uso: bash standalone/fix-touchscreen.sh
#      TOUCH_MATRIX="0 1 0 -1 0 1 0 0 1" bash standalone/fix-touchscreen.sh

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
QUIET=0

while [ $# -gt 0 ]; do
    case "$1" in
        --quiet) QUIET=1; shift ;;
        --matrix)
            shift
            TOUCH_MATRIX="${1:?usage: --matrix \"0 1 0 -1 0 1 0 0 1\"}"
            shift
            ;;
        *) shift ;;
    esac
done

[ -f "$APP_DIR/.env" ] && set -a && source "$APP_DIR/.env" && set +a

export DISPLAY="${DISPLAY:-:0}"

if ! command -v xinput >/dev/null 2>&1; then
    echo "Installa: sudo apt install -y xinput x11-xserver-utils" >&2
    exit 1
fi

if ! xdpyinfo >/dev/null 2>&1; then
    echo "Sessione X11 non attiva (DISPLAY=$DISPLAY). Avvia da desktop, non da SSH puro." >&2
    exit 1
fi

log() { [ "$QUIET" -eq 1 ] || echo "$*"; }

TOUCH_ID=""
TOUCH_NAME=""
while IFS= read -r line; do
    id="${line%% *}"
    name="${line#* }"
    lower="$(echo "$name" | tr '[:upper:]' '[:lower:]')"
    case "$lower" in
        *touch*|*ads7846*|*goodix*|*egalax*|*ft5406*|*stylus*|*pen*)
            TOUCH_ID="$id"
            TOUCH_NAME="$name"
            break
            ;;
    esac
done < <(xinput list --id-only 2>/dev/null | while read -r id; do
    echo "$id $(xinput list --name-only "$id" 2>/dev/null || true)"
done)

if [ -z "$TOUCH_ID" ]; then
    echo "Nessun dispositivo touch trovato. Esegui: bash standalone/diagnose-touch.sh" >&2
    exit 1
fi

log "Touch: [$TOUCH_ID] $TOUCH_NAME"

OUTPUT=""
if xrandr --query 2>/dev/null | grep -q '^fb_1 connected'; then
    OUTPUT="fb_1"
else
    while read -r name mode _; do
        [ "$mode" = "connected" ] || continue
        res="$(xrandr --query | awk -v n="$name" '$1==n {print $3; exit}')"
        if [ "$res" = "480x320" ] || [ "$res" = "320x480" ]; then
            OUTPUT="$name"
            break
        fi
        [ -z "$OUTPUT" ] && OUTPUT="$name"
    done < <(xrandr --query | awk '/ connected/{print $1,$2}')
fi

if [ -n "$OUTPUT" ]; then
    if xinput map-to-output "$TOUCH_ID" "$OUTPUT" 2>/dev/null; then
        log "Mappato touch → $OUTPUT"
    else
        log "map-to-output non supportato su questo driver"
    fi
fi

MATRIX="${TOUCH_MATRIX:-}"
if [ -n "$MATRIX" ]; then
    # shellcheck disable=SC2086
    xinput set-prop "$TOUCH_ID" "Coordinate Transformation Matrix" $MATRIX
    log "Matrice touch: $MATRIX"
else
    # 90° orario — comune TFT 3.5" in landscape
    if xinput set-prop "$TOUCH_ID" "Coordinate Transformation Matrix" 0 1 0 -1 0 1 0 0 1 2>/dev/null; then
        log "Matrice default 90° applicata"
    fi
fi

xinput enable "$TOUCH_ID" 2>/dev/null || true
log "Touch configurato."
