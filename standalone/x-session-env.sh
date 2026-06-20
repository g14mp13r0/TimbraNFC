# shellcheck shell=bash
# Imposta DISPLAY/XAUTHORITY per comandi grafici via SSH sul Pi locale.
# source standalone/x-session-env.sh

_xse_user="${APP_USER:-${SUDO_USER:-$(whoami)}}"
_xse_uid="$(id -u "$_xse_user" 2>/dev/null || id -u)"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/${_xse_uid}}"

import_graphical_session_env() {
    local user="${1:-$_xse_user}"
    local uid pid="" name
    uid="$(id -u "$user" 2>/dev/null)" || return 1

    for name in labwc wayfire wlroots wlroots-session pcmanfm; do
        pid="$(pgrep -u "$uid" -x "$name" 2>/dev/null | head -1 || true)"
        [ -n "$pid" ] && break
    done
    if [ -z "$pid" ]; then
        pid="$(pgrep -u "$uid" -f 'Xwayland :0' 2>/dev/null | head -1 || true)"
    fi
    [ -n "$pid" ] || return 1
    [ -r "/proc/${pid}/environ" ] || return 1

    local _ok=0
    while IFS= read -r -d '' _line; do
        case "$_line" in
            DISPLAY=*|WAYLAND_DISPLAY=*|XAUTHORITY=*|DBUS_SESSION_BUS_ADDRESS=*|XDG_RUNTIME_DIR=*)
                export "$_line"
                _ok=1
                ;;
        esac
    done < "/proc/${pid}/environ"
    [ "$_ok" -eq 1 ]
}

# Importa env dal compositor desktop (xinput/xrandr da SSH altrimenti falliscono)
import_graphical_session_env "$_xse_user" || true

export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=${XDG_RUNTIME_DIR}/bus}"

if [ -z "${WAYLAND_DISPLAY:-}" ]; then
    for _wl in wayland-1 wayland-0; do
        if [ -S "${XDG_RUNTIME_DIR}/${_wl}" ]; then
            export WAYLAND_DISPLAY="$_wl"
            break
        fi
    done
fi

if [ -S /tmp/.X11-unix/X0 ]; then
    export DISPLAY="${DISPLAY:-:0}"
elif [ -S /tmp/.X11-unix/X1 ]; then
    export DISPLAY="${DISPLAY:-:1}"
else
    export DISPLAY="${DISPLAY:-:0}"
fi

if [ -z "${XAUTHORITY:-}" ] || [ ! -f "$XAUTHORITY" ]; then
    for _xa in \
        "/home/${_xse_user}/.Xauthority" \
        "/run/user/${_xse_uid}/gdm/Xauthority" \
        "/run/user/${_xse_uid}/.Xauthority"; do
        if [ -f "$_xa" ]; then
            export XAUTHORITY="$_xa"
            break
        fi
    done
    if [ -z "${XAUTHORITY:-}" ] || [ ! -f "$XAUTHORITY" ]; then
        for _xa in /run/user/"${_xse_uid}"/.mutter-Xwaylandauth.*; do
            if [ -f "$_xa" ]; then
                export XAUTHORITY="$_xa"
                break
            fi
        done
    fi
fi

# xrandr/xinput da SSH possono bloccarsi: usare sempre timeout
x_cmd() {
    local t="${1:-${X_CMD_TIMEOUT:-5}}"
    if [ "$#" -gt 0 ] && [[ "$1" =~ ^[0-9]+$ ]]; then
        shift
    else
        t="${X_CMD_TIMEOUT:-5}"
    fi
    if command -v timeout >/dev/null 2>&1; then
        timeout "$t" "$@"
    else
        "$@"
    fi
}

xrandr_query() {
    x_cmd xrandr --query 2>/dev/null || true
}

x_session_ok() {
    [ -n "$(xrandr_query)" ]
}

x_socket_ok() {
    local _d="${DISPLAY#*:}"
    _d="${_d:-0}"
    [ -S "/tmp/.X11-unix/X${_d}" ]
}

# Esegue uno script nella sessione grafica utente (xinput funziona lì)
run_in_user_graphical_session() {
    local script="$1"
    shift || true

    if [ ! -f "$script" ]; then
        return 1
    fi

    import_graphical_session_env "$_xse_user" || true

    if sudo -u "$_xse_user" env \
        XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" \
        DBUS_SESSION_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS" \
        DISPLAY="$DISPLAY" \
        WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-}" \
        XAUTHORITY="${XAUTHORITY:-}" \
        X_CMD_TIMEOUT="${X_CMD_TIMEOUT:-15}" \
        systemd-run --user --wait --collect --quiet \
        --setenv=DISPLAY="$DISPLAY" \
        --setenv=WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-}" \
        --setenv=XAUTHORITY="${XAUTHORITY:-}" \
        --setenv=X_CMD_TIMEOUT="${X_CMD_TIMEOUT:-15}" \
        bash "$script" "$@"; then
        return 0
    fi

    bash "$script" "$@"
}
