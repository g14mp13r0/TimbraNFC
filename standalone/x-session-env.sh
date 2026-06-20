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
        "/run/user/${_xse_uid}/.mutter-Xwaylandauth."* \
        "/run/user/${_xse_uid}/.Xauthority"; do
        if [ -f "$_xa" ]; then
            export XAUTHORITY="$_xa"
            break
        fi
    done
fi

x_session_ok() {
    xrandr --query >/dev/null 2>&1
}
