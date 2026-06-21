#!/bin/bash
# Avvio automatico kiosk al boot — senza login manuale
# sudo bash standalone/setup-boot-kiosk.sh
#
# Configura:
#   - boot su desktop con autologin utente
#   - servizio systemd utente (kiosk alla sessione grafica)
#   - autostart desktop come fallback

set -euo pipefail

APP_USER="${APP_USER:-${SUDO_USER:-gpastorino}}"
APP_DIR="${APP_DIR:-/home/${APP_USER}/TimbraNFC}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Esegui con sudo"
    exit 1
fi

if [ ! -f "$APP_DIR/standalone/launch_kiosk.sh" ]; then
    echo "Errore: $APP_DIR/standalone/launch_kiosk.sh non trovato"
    exit 1
fi

_detect_desktop_session() {
    local s
    for s in rpd-labwc LXDE-pi-wayfire LXDE-pi-x openbox; do
        if [ -f "/usr/share/wayland-sessions/${s}.desktop" ] \
            || [ -f "/usr/share/xsessions/${s}.desktop" ]; then
            echo "$s"
            return 0
        fi
    done
    echo "LXDE-pi-x"
}

_enable_autologin() {
    echo "→ Autologin desktop per $APP_USER"

    if command -v raspi-config >/dev/null 2>&1; then
        raspi-config nonint do_boot_behaviour B4 2>/dev/null || true
    fi

    systemctl set-default graphical.target 2>/dev/null || true

    local session
    session="$(_detect_desktop_session)"
    mkdir -p /etc/lightdm/lightdm.conf.d
    cat > /etc/lightdm/lightdm.conf.d/50-timbranfc-autologin.conf <<EOF
# TimbraNFC — login automatico al desktop (no password)
[Seat:*]
autologin-user=${APP_USER}
autologin-user-timeout=0
autologin-session=${session}
EOF
    echo "  sessione desktop: $session"
}

_install_autostart_fallback() {
    echo "→ Autostart desktop (fallback)"

    chmod +x "$APP_DIR/standalone/launch_kiosk.sh"

    local autostart="/home/${APP_USER}/.config/autostart"
    mkdir -p "$autostart"

    sed "s|@APP_DIR@|${APP_DIR}|g" \
        "$APP_DIR/standalone/autostart/timbranfc-kiosk.desktop" \
        > "$autostart/timbranfc-kiosk.desktop"

    chown -R "${APP_USER}:${APP_USER}" "/home/${APP_USER}/.config"
}

_install_user_kiosk_service() {
    echo "→ Servizio systemd utente (avvio kiosk alla sessione grafica)"

    local uid user_unit="/home/${APP_USER}/.config/systemd/user"
    uid="$(id -u "$APP_USER")"
    mkdir -p "$user_unit"

    sed -e "s|@APP_DIR@|${APP_DIR}|g" -e "s|@APP_USER@|${APP_USER}|g" \
        "$APP_DIR/standalone/systemd/timbranfc-kiosk.user.service" \
        > "$user_unit/timbranfc-kiosk.service"

    chown -R "${APP_USER}:${APP_USER}" "/home/${APP_USER}/.config/systemd"

    loginctl enable-linger "$APP_USER" 2>/dev/null || true

    _userctl() {
        sudo -u "$APP_USER" \
            XDG_RUNTIME_DIR="/run/user/${uid}" \
            DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${uid}/bus" \
            systemctl --user "$@"
    }

    _userctl daemon-reload
    _userctl enable timbranfc-kiosk.service

    if [ -d "/run/user/${uid}" ] && [ -S "/run/user/${uid}/bus" ]; then
        _userctl restart timbranfc-kiosk.service 2>/dev/null || \
            _userctl start timbranfc-kiosk.service 2>/dev/null || true
    fi
}

_disable_kiosk_systemd() {
    # Il servizio di sistema non ha DISPLAY: usiamo systemd --user + autostart
    systemctl disable --now timbranfc-kiosk.service 2>/dev/null || true
}

_show_status() {
    local uid
    uid="$(id -u "$APP_USER" 2>/dev/null || echo '?')"
    echo ""
    echo "=== Stato avvio automatico ==="
    systemctl get-default 2>/dev/null | sed 's/^/  target boot: /' || true
    if [ -f /etc/lightdm/lightdm.conf.d/50-timbranfc-autologin.conf ]; then
        grep -E '^autologin-' /etc/lightdm/lightdm.conf.d/50-timbranfc-autologin.conf | sed 's/^/  /'
    else
        echo "  autologin: NON configurato"
    fi
    if [ -f "/home/${APP_USER}/.config/autostart/timbranfc-kiosk.desktop" ]; then
        echo "  autostart: ~/.config/autostart/timbranfc-kiosk.desktop"
    fi
    if [ -f "/home/${APP_USER}/.config/systemd/user/timbranfc-kiosk.service" ]; then
        echo "  user service: ~/.config/systemd/user/timbranfc-kiosk.service"
        sudo -u "$APP_USER" \
            XDG_RUNTIME_DIR="/run/user/${uid}" \
            DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${uid}/bus" \
            systemctl --user is-enabled timbranfc-kiosk.service 2>/dev/null \
            | sed 's/^/  timbranfc-kiosk (user): /' || true
    fi
    systemctl is-enabled timbranfc-server.service 2>/dev/null | sed 's/^/  timbranfc-server: /' || true
    systemctl is-enabled timbranfc-kiosk.service 2>/dev/null | sed 's/^/  timbranfc-kiosk (system, disabilitato): /' || true
    echo ""
    echo "Riavvia il Pi: sudo reboot"
    echo "Dopo il boot il kiosk parte da solo (attendi ~30–60s)."
    echo "Log: tail -f /tmp/timbranfc-kiosk.log"
    echo "Verifica: bash ${APP_DIR}/standalone/verify-kiosk.sh"
}

echo "=== Setup avvio automatico kiosk (senza login) ==="
echo "Utente: $APP_USER"
echo "Cartella: $APP_DIR"
echo ""

_enable_autologin
_install_user_kiosk_service
_install_autostart_fallback
_disable_kiosk_systemd
_show_status
