#!/bin/bash
# Avvio automatico kiosk al boot — senza login manuale
# sudo bash standalone/setup-boot-kiosk.sh
#
# Configura:
#   - boot su desktop con autologin utente
#   - autostart kiosk alla sessione grafica
#   - server systemd già attivo prima del desktop

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

_install_autostart() {
    echo "→ Autostart kiosk UI"

    chmod +x "$APP_DIR/standalone/launch_kiosk.sh"

    local autostart="/home/${APP_USER}/.config/autostart"
    mkdir -p "$autostart"

    cat > "$autostart/timbranfc-kiosk.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=TimbraNFC Kiosk
Comment=Timbratrice presenze NFC — avvio automatico
Exec=${APP_DIR}/standalone/launch_kiosk.sh
Terminal=false
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=15
EOF

    chown -R "${APP_USER}:${APP_USER}" "/home/${APP_USER}/.config"
}

_disable_kiosk_systemd() {
    # Il kiosk richiede DISPLAY: autostart desktop è il metodo affidabile
    systemctl disable --now timbranfc-kiosk.service 2>/dev/null || true
}

_show_status() {
    echo ""
    echo "=== Stato avvio automatico ==="
    systemctl get-default 2>/dev/null | sed 's/^/  target boot: /' || true
    if [ -f /etc/lightdm/lightdm.conf.d/50-timbranfc-autologin.conf ]; then
        grep -E '^autologin-' /etc/lightdm/lightdm.conf.d/50-timbranfc-autologin.conf | sed 's/^/  /'
    fi
    if [ -f "/home/${APP_USER}/.config/autostart/timbranfc-kiosk.desktop" ]; then
        echo "  autostart: ~/.config/autostart/timbranfc-kiosk.desktop"
    fi
    systemctl is-enabled timbranfc-server.service 2>/dev/null | sed 's/^/  timbranfc-server: /' || true
    systemctl is-enabled timbranfc-kiosk.service 2>/dev/null | sed 's/^/  timbranfc-kiosk: /' || true
    echo ""
    echo "Riavvia il Pi: sudo reboot"
    echo "Dopo il boot il kiosk parte da solo (attendi ~30s)."
    echo "Log: tail -f /tmp/timbranfc-kiosk.log"
    echo "Verifica: bash ${APP_DIR}/standalone/verify-kiosk.sh"
}

echo "=== Setup avvio automatico kiosk (senza login) ==="
echo "Utente: $APP_USER"
echo "Cartella: $APP_DIR"
echo ""

_enable_autologin
_install_autostart
_disable_kiosk_systemd
_show_status
