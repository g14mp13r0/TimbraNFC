#!/bin/bash
# Display SPI 3.5" (320x480 portrait) → landscape 480x320 + touch ADS7846
# Uso: bash standalone/fix-touchscreen.sh

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
QUIET=0

while [ $# -gt 0 ]; do
    case "$1" in
        --quiet) QUIET=1; shift ;;
        --matrix)
            shift
            TOUCH_MATRIX="${1:?usage: --matrix \"0 -1 1 1 0 0 0 0 1\"}"
            shift
            ;;
        --no-rotate) TOUCH_NO_ROTATE=1; shift ;;
        *) shift ;;
    esac
done

[ -f "$APP_DIR/.env" ] && set -a && source "$APP_DIR/.env" && set +a

# shellcheck source=standalone/x-session-env.sh
source "$APP_DIR/standalone/x-session-env.sh"
TARGET_W="${DISPLAY_WIDTH:-480}"
TARGET_H="${DISPLAY_HEIGHT:-320}"
TOUCH_ROTATE="${TOUCH_ROTATE:-left}"

if ! command -v xinput >/dev/null 2>&1 || ! command -v xrandr >/dev/null 2>&1; then
    echo "Installa: sudo apt install -y xinput x11-xserver-utils" >&2
    exit 1
fi

if ! xrandr --query >/dev/null 2>&1; then
    echo "Display non disponibile (DISPLAY=$DISPLAY). Esegui dal desktop del Pi." >&2
    exit 1
fi

log() { [ "${QUIET:-0}" -eq 1 ] || echo "$*"; }

# Output SPI (SPI-1, fb_1, ...)
OUTPUT=""
CURRENT_MODE=""
while read -r name mode res _; do
    [ "$mode" = "connected" ] || continue
    case "$name" in
        SPI-*|fb_*|DSI-*)
            OUTPUT="$name"
            CURRENT_MODE="$res"
            break
            ;;
    esac
done < <(xrandr --query | awk '/ connected/{print $1,$2,$3}')

if [ -z "$OUTPUT" ]; then
    OUTPUT="$(xrandr --query | awk '/ connected/{print $1; exit}')"
    CURRENT_MODE="$(xrandr --query | awk -v o="$OUTPUT" '$1==o {print $3; exit}')"
fi

if [ -z "$OUTPUT" ]; then
    echo "Nessun output display trovato." >&2
    exit 1
fi

log "Display: $OUTPUT ($CURRENT_MODE) → target ${TARGET_W}x${TARGET_H}"

# Estrai WxH da "320x480+0+0" o "320x480"
CUR_W="${CURRENT_MODE%%+*}"
CUR_W="${CUR_W%%x*}"
CUR_H="${CURRENT_MODE#*x}"
CUR_H="${CUR_H%%+*}"

# Ruota schermo portrait → landscape (320x480 → 480x320)
DEFAULT_MATRIX="1 0 0 0 1 0 0 0 1"
ROTATED=0

if [ "${TOUCH_NO_ROTATE:-0}" -ne 1 ]; then
    if [ -n "$CUR_W" ] && [ -n "$CUR_H" ] && [ "$CUR_W" -lt "$CUR_H" ] && [ "$TARGET_W" -gt "$TARGET_H" ]; then
        case "$TOUCH_ROTATE" in
            left|L)
                _mat="0 -1 1 1 0 0 0 0 1"
                _wlr="90"
                _xr="left"
                ;;
            right|R)
                _mat="0 1 0 -1 0 1 0 0 1"
                _wlr="270"
                _xr="right"
                ;;
            *)
                _mat="1 0 0 0 1 0 0 0 1"
                _wlr=""
                _xr="$TOUCH_ROTATE"
                ;;
        esac

        # 1) Wayland compositor (Pi OS recente)
        if [ -n "${WAYLAND_DISPLAY:-}" ] && command -v wlr-randr >/dev/null 2>&1; then
            if wlr-randr --output "$OUTPUT" --transform "${_wlr:-90}" 2>/dev/null; then
                DEFAULT_MATRIX="$_mat"
                ROTATED=1
                log "Rotazione Wayland (wlr-randr): ${_wlr:-90}°"
            fi
        fi

        # 2) XWayland xrandr (spesso fallisce su SPI)
        if [ "$ROTATED" -eq 0 ]; then
            if xrandr --output "$OUTPUT" --rotate "$_xr" 2>/dev/null; then
                DEFAULT_MATRIX="$_mat"
                ROTATED=1
                log "Rotazione X11 (xrandr): $_xr"
            else
                log "Rotazione software non disponibile (XWayland BadMatch)."
                log "Applica rotazione permanente e reboot:"
                log "  sudo bash $APP_DIR/standalone/enable-spi-landscape.sh"
                log "  sudo reboot"
                DEFAULT_MATRIX="$_mat"
            fi
        fi
    else
        log "Rotazione display: non necessaria (${CUR_W}x${CUR_H})"
    fi
else
    DEFAULT_MATRIX="0 1 0 -1 0 1 0 0 1"
fi

# Touch: xwayland-touch o ADS7846
TOUCH_ID=""
TOUCH_NAME=""
while IFS= read -r line; do
    id="${line%% *}"
    name="${line#* }"
    lower="$(echo "$name" | tr '[:upper:]' '[:lower:]')"
    case "$lower" in
        *touch*|*ads7846*|*xwayland-touch*)
            TOUCH_ID="$id"
            TOUCH_NAME="$name"
            break
            ;;
    esac
done < <(xinput list --id-only 2>/dev/null | while read -r id; do
    echo "$id $(xinput list --name-only "$id" 2>/dev/null || true)"
done)

if [ -z "$TOUCH_ID" ]; then
    echo "Nessun dispositivo touch trovato (cercato xwayland-touch / ADS7846)." >&2
    exit 1
fi

log "Touch: [$TOUCH_ID] $TOUCH_NAME"

if xinput map-to-output "$TOUCH_ID" "$OUTPUT" 2>/dev/null; then
    log "Mappato touch → $OUTPUT"
fi

MATRIX="${TOUCH_MATRIX:-$DEFAULT_MATRIX}"
# shellcheck disable=SC2086
xinput set-prop "$TOUCH_ID" "Coordinate Transformation Matrix" $MATRIX
log "Matrice touch: $MATRIX"

xinput enable "$TOUCH_ID" 2>/dev/null || true
log "Touch configurato."
