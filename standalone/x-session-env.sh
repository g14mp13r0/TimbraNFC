# shellcheck shell=bash
# Imposta DISPLAY/XAUTHORITY per comandi grafici via SSH sul Pi locale.
# source standalone/x-session-env.sh

_xse_user="${APP_USER:-${SUDO_USER:-$(whoami)}}"
_xse_uid="$(id -u "$_xse_user" 2>/dev/null || id -u)"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/${_xse_uid}}"

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
    # auth XWayland (labwc) — glob espanso in sottoshell per evitare hang
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
    local t="${X_CMD_TIMEOUT:-5}"
    if command -v timeout >/dev/null 2>&1; then
        timeout "$t" "$@"
    else
        "$@"
    fi
}

xrandr_query() {
    x_cmd xrandr --query 2>/dev/null
}

x_session_ok() {
    [ -n "$(xrandr_query)" ]
}

x_socket_ok() {
    local _d="${DISPLAY#*:}"
    _d="${_d:-0}"
    [ -S "/tmp/.X11-unix/X${_d}" ]
}
