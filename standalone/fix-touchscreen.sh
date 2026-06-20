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
NFC_AUTO_TIMBRATURA="${NFC_AUTO_TIMBRATURA:-1}"

# shellcheck source=standalone/x-session-env.sh
source "$APP_DIR/standalone/x-session-env.sh"
TARGET_W="${DISPLAY_WIDTH:-480}"
TARGET_H="${DISPLAY_HEIGHT:-320}"
TOUCH_ROTATE="${TOUCH_ROTATE:-left}"

if ! command -v xinput >/dev/null 2>&1 || ! command -v xrandr >/dev/null 2>&1; then
    echo "Installa: sudo apt install -y xinput x11-xserver-utils" >&2
    exit 1
fi

log() { [ "${QUIET:-0}" -eq 1 ] || echo "$*"; }

run_timeout() {
    x_cmd "$@" || true
}

# Una sola query xrandr (timeout non deve far crashare set -e)
XRANDR_OUT=""
XRANDR_OUT="$(xrandr_query)" || true

if [ -z "$XRANDR_OUT" ]; then
    echo "Display non disponibile o xrandr timeout (DISPLAY=$DISPLAY)." >&2
    if ! x_socket_ok; then
        exit 1
    fi
    echo "Socket X presente — continuo senza xrandr." >&2
fi

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
done <<< "$(printf '%s\n' "$XRANDR_OUT" | awk '/ connected/{print $1,$2,$3}')"

if [ -z "$OUTPUT" ] && [ -n "$XRANDR_OUT" ]; then
    OUTPUT="$(printf '%s\n' "$XRANDR_OUT" | awk '/ connected/{print $1; exit}')"
    CURRENT_MODE="$(printf '%s\n' "$XRANDR_OUT" | awk -v o="$OUTPUT" '$1==o {print $3; exit}')"
fi

if [ -z "$OUTPUT" ]; then
    OUTPUT="SPI-1"
    CURRENT_MODE="320x480"
    log "xrandr non disponibile — assumo $OUTPUT ($CURRENT_MODE)"
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

        # 1) Wayland compositor (labwc / Pi OS recente) — timeout: può bloccarsi da SSH
        if [ -n "${WAYLAND_DISPLAY:-}" ] && command -v wlr-randr >/dev/null 2>&1; then
            _wlr_err=""
            if _wlr_err="$(run_timeout 5 wlr-randr --output "$OUTPUT" --transform "${_wlr:-90}" 2>&1)"; then
                DEFAULT_MATRIX="$_mat"
                ROTATED=1
                log "Rotazione Wayland (wlr-randr): ${_wlr:-90}°"
            else
                _wlr_rc=$?
                if [ "$_wlr_rc" -eq 124 ]; then
                    log "wlr-randr: timeout (compositor non risponde da SSH — touch applicato comunque)"
                else
                    log "wlr-randr fallito: ${_wlr_err:-exit $_wlr_rc}"
                fi
            fi
        fi

        # 2) XWayland xrandr (spesso fallisce su SPI)
        if [ "$ROTATED" -eq 0 ]; then
            if x_cmd 5 xrandr --output "$OUTPUT" --rotate "$_xr" 2>/dev/null; then
                DEFAULT_MATRIX="$_mat"
                ROTATED=1
                log "Rotazione X11 (xrandr): $_xr"
            else
                log "Rotazione software non disponibile (xrandr timeout/BadMatch)."
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

# Matrice touch dopo rotazione display
if [ -n "${TOUCH_MATRIX:-}" ]; then
    : # esplicita in .env
elif [ "${TOUCH_FIRMWARE_ROTATED:-0}" = "1" ] && [ "$DISPLAY_LANDSCAPE" -eq 1 ] && [ "$ROTATED" -eq 0 ]; then
    DEFAULT_MATRIX="$(touch_matrix_for_rotate identity)"
    log "TOUCH_FIRMWARE_ROTATED=1 + display landscape firmware → matrice identità"
elif [ "$TARGET_W" -gt "$TARGET_H" ]; then
    DEFAULT_MATRIX="$(touch_matrix_for_rotate "$TOUCH_ROTATE")"
    if [ "$DISPLAY_PORTRAIT" -eq 1 ]; then
        log "Matrice touch (${TOUCH_ROTATE}) — display XWayland ancora portrait"
    elif [ "$DISPLAY_LANDSCAPE" -eq 1 ]; then
        log "Matrice touch (${TOUCH_ROTATE}) — display landscape"
    fi
fi

# Touch: xwayland-touch — parse robusto output xinput
discover_touch_devices() {
    TOUCH_IDS=()
    TOUCH_NAMES=()
    local raw=""
    raw="$(x_cmd 15 xinput list 2>&1)" || true
    [ -z "$raw" ] && return 1

    while IFS= read -r line; do
        echo "$line" | grep -qiE 'touch|ads7846|xwayland-touch' || continue
        _id="$(printf '%s' "$line" | sed -n 's/.*id=\([0-9]*\).*/\1/p')"
        _name="$(printf '%s' "$line" | sed -E 's/^[[:space:]]*.*[↳⎜][[:space:]]*//; s/[[:space:]]+id=.*//; s/^[[:space:]]+//')"
        [ -z "$_id" ] && continue
        TOUCH_IDS+=("$_id")
        TOUCH_NAMES+=("${_name:-touch}")
    done <<< "$raw"
    [ "${#TOUCH_IDS[@]}" -gt 0 ]
}

TOUCH_IDS=()
TOUCH_NAMES=()
if ! discover_touch_devices; then
    import_graphical_session_env "${APP_USER:-$(whoami)}" || true
    discover_touch_devices || true
fi

if [ "${#TOUCH_IDS[@]}" -eq 0 ]; then
    if [ "${NFC_AUTO_TIMBRATURA:-0}" = "1" ]; then
        log "Touch non configurato — OK con NFC_AUTO_TIMBRATURA=1"
        exit 0
    fi
    echo "Nessun dispositivo touch in xinput (SSH senza sessione grafica completa)." >&2
    echo "Da SSH prova:" >&2
    echo "  bash $APP_DIR/standalone/ssh-touch-fix.sh" >&2
    exit 1
fi

MATRIX="${TOUCH_MATRIX:-$DEFAULT_MATRIX}"

for i in "${!TOUCH_IDS[@]}"; do
    TOUCH_ID="${TOUCH_IDS[$i]}"
    TOUCH_NAME="${TOUCH_NAMES[$i]}"
    log "Touch: [$TOUCH_ID] $TOUCH_NAME"

    if x_cmd 5 xinput map-to-output "$TOUCH_ID" "$OUTPUT" 2>/dev/null; then
        log "Mappato touch → $OUTPUT"
    fi

    # shellcheck disable=SC2086
    if x_cmd 5 xinput set-prop "$TOUCH_ID" "Coordinate Transformation Matrix" $MATRIX 2>/dev/null; then
        :
    else
        log "Avviso: matrice non applicabile su [$TOUCH_ID]"
    fi
    x_cmd 5 xinput enable "$TOUCH_ID" 2>/dev/null || true
done

log "Matrice touch: $MATRIX"
log "Touch configurato."
