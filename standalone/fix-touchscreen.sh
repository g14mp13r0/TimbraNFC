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

touch_matrix_for_rotate() {
    case "${1:-left}" in
        left|L)  echo "0 -1 1 1 0 0 0 0 1" ;;
        right|R) echo "0 1 0 -1 0 1 0 0 1" ;;
        inverted|180|2) echo "-1 0 1 0 -1 1 0 0 1" ;;
        none|identity|0) echo "1 0 0 0 1 0 0 0 1" ;;
        *) echo "1 0 0 0 1 0 0 0 1" ;;
    esac
}

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
DEFAULT_MATRIX="$(touch_matrix_for_rotate identity)"
ROTATED=0
DISPLAY_PORTRAIT=0
DISPLAY_LANDSCAPE=0

if [ -n "$CUR_W" ] && [ -n "$CUR_H" ]; then
    [ "$CUR_W" -lt "$CUR_H" ] && DISPLAY_PORTRAIT=1
    [ "$CUR_W" -gt "$CUR_H" ] && DISPLAY_LANDSCAPE=1
fi

if [ "${TOUCH_NO_ROTATE:-0}" -ne 1 ]; then
    if [ "$DISPLAY_PORTRAIT" -eq 1 ] && [ "$TARGET_W" -gt "$TARGET_H" ]; then
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
                log "Usa rotazione firmware: sudo bash $APP_DIR/standalone/enable-spi-landscape.sh"
                DEFAULT_MATRIX="$_mat"
            fi
        fi
    elif [ "$DISPLAY_LANDSCAPE" -eq 1 ]; then
        log "Display già landscape (${CUR_W}x${CUR_H}) — rotazione schermo non serve"
    else
        log "Rotazione display: non necessaria (${CUR_W}x${CUR_H})"
    fi
else
    DEFAULT_MATRIX="$(touch_matrix_for_rotate right)"
fi

# Matrice touch: display_rotate ruota il framebuffer ma spesso lascia ADS7846 in portrait
if [ "${TOUCH_FIRMWARE_ROTATED:-0}" = "1" ]; then
    DEFAULT_MATRIX="$(touch_matrix_for_rotate identity)"
    log "TOUCH_FIRMWARE_ROTATED=1 → matrice identità"
elif [ "$TARGET_W" -gt "$TARGET_H" ] && [ -z "${TOUCH_MATRIX:-}" ]; then
    DEFAULT_MATRIX="$(touch_matrix_for_rotate "$TOUCH_ROTATE")"
    if [ "$DISPLAY_LANDSCAPE" -eq 1 ]; then
        log "Matrice touch OS (${TOUCH_ROTATE}) — necessaria con display_rotate=1"
    fi
fi

# Touch: xwayland-touch o ADS7846 (tutti i dispositivi touch trovati)
TOUCH_IDS=()
TOUCH_NAMES=()
while IFS= read -r line; do
    id="${line%% *}"
    name="${line#* }"
    lower="$(echo "$name" | tr '[:upper:]' '[:lower:]')"
    case "$lower" in
        *touch*|*ads7846*|*xwayland-touch*)
            TOUCH_IDS+=("$id")
            TOUCH_NAMES+=("$name")
            ;;
    esac
done < <(xinput list --id-only 2>/dev/null | while read -r id; do
    echo "$id $(xinput list --name-only "$id" 2>/dev/null || true)"
done)

if [ "${#TOUCH_IDS[@]}" -eq 0 ]; then
    echo "Nessun dispositivo touch trovato (cercato xwayland-touch / ADS7846)." >&2
    echo "Fix OS: sudo bash $APP_DIR/standalone/fix-touch-os.sh && sudo reboot" >&2
    exit 1
fi

MATRIX="${TOUCH_MATRIX:-$DEFAULT_MATRIX}"

for i in "${!TOUCH_IDS[@]}"; do
    TOUCH_ID="${TOUCH_IDS[$i]}"
    TOUCH_NAME="${TOUCH_NAMES[$i]}"
    log "Touch: [$TOUCH_ID] $TOUCH_NAME"

    if xinput map-to-output "$TOUCH_ID" "$OUTPUT" 2>/dev/null; then
        log "Mappato touch → $OUTPUT"
    fi

    # shellcheck disable=SC2086
    xinput set-prop "$TOUCH_ID" "Coordinate Transformation Matrix" $MATRIX 2>/dev/null || \
        log "Avviso: matrice non applicabile su [$TOUCH_ID] (prova fix-touch-os.sh)"
    xinput enable "$TOUCH_ID" 2>/dev/null || true
done

log "Matrice touch: $MATRIX"
log "Touch configurato."
