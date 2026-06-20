#!/bin/bash
# Configura lettore ACR122U per kiosk standalone
# sudo bash standalone/fix-nfc.sh
#
# Prova: reset USB → nfcpy → PC/SC (con polkit + gruppo scard)

set -euo pipefail

APP_USER="${APP_USER:-${SUDO_USER:-gpastorino}}"
APP_DIR="${APP_DIR:-/home/${APP_USER}/TimbraNFC}"
ENV_FILE="${APP_DIR}/.env"
UDEV_RULE="/etc/udev/rules.d/99-timbranfc-acr122u.rules"
POLKIT_RULE="/etc/polkit-1/rules.d/50-timbranfc-pcscd.rules"
PY="${APP_DIR}/.venv/bin/python"
TEST="${APP_DIR}/standalone/test-nfc.py"
NFC_MODE="${NFC_MODE:-auto}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Esegui con sudo"
    exit 1
fi

echo "=== Fix NFC TimbraNFC (modalità: $NFC_MODE) ==="

if ! lsusb 2>/dev/null | grep -qiE '072f:2200|072f.*2200'; then
    echo "ERRORE: ACR122U (072f:2200) non trovato su USB"
    lsusb 2>/dev/null || true
    exit 1
fi
lsusb | grep -iE '072f|acr' || true

export DEBIAN_FRONTEND=noninteractive
apt-get install -y pcscd libpcsclite1 libccid libacsccid1 pcsc-tools usbutils 2>/dev/null || true

# Driver kernel pn533 blocca ACR122U — blacklist obbligatorio
if [ -f "$APP_DIR/standalone/fix-acr122u-kernel.sh" ]; then
    bash "$APP_DIR/standalone/fix-acr122u-kernel.sh"
fi

if ! getent group scard >/dev/null 2>&1; then
    groupadd scard 2>/dev/null || true
fi
usermod -aG scard "$APP_USER" 2>/dev/null || true

cat > "$UDEV_RULE" <<'EOF'
# ACR122U — accesso USB diretto (nfcpy) + gruppo scard (pcscd)
SUBSYSTEM=="usb", ATTRS{idVendor}=="072f", ATTRS{idProduct}=="2200", MODE="0666", GROUP="scard"
EOF

mkdir -p /etc/polkit-1/rules.d
cat > "$POLKIT_RULE" <<'EOF'
// TimbraNFC — accesso PC/SC per utente kiosk
polkit.addRule(function(action, subject) {
    if (action.id.indexOf("pcsc") !== -1 || action.id.indexOf("pcscd") !== -1) {
        return polkit.Result.YES;
    }
});
EOF

udevadm control --reload-rules
udevadm trigger
sleep 1

touch "$ENV_FILE"
chown "${APP_USER}:${APP_USER}" "$ENV_FILE"

_set_backend() {
    if grep -q '^NFC_BACKEND=' "$ENV_FILE"; then
        sed -i "s/^NFC_BACKEND=.*/NFC_BACKEND=$1/" "$ENV_FILE"
    else
        echo "NFC_BACKEND=$1" >> "$ENV_FILE"
    fi
}

_usb_dev_path() {
    local bus dev
    bus="$(lsusb -d 072f:2200 2>/dev/null | awk '{print $2}' | head -1)"
    dev="$(lsusb -d 072f:2200 2>/dev/null | awk '{print $4}' | tr -d ':' | head -1)"
    [ -n "$bus" ] && [ -n "$dev" ] || return 1
    printf '/dev/bus/usb/%s/%s' "$bus" "$dev"
}

_reset_usb() {
    local devpath
    devpath="$(_usb_dev_path)" || return 0
    echo "Reset USB ACR122U: $devpath"
    systemctl stop pcscd pcscd.socket 2>/dev/null || true
    sleep 1
    if command -v usbreset >/dev/null 2>&1 && [ -e "$devpath" ]; then
        usbreset "$devpath" 2>/dev/null || true
    fi
    sleep 2
}

_stop_pcscd() {
    systemctl stop pcscd.service 2>/dev/null || true
    systemctl stop pcscd.socket 2>/dev/null || true
    sleep 2
}

_disable_pcscd() {
    _stop_pcscd
    systemctl disable pcscd.service pcscd.socket 2>/dev/null || true
    systemctl mask pcscd.socket 2>/dev/null || true
}

_start_pcscd() {
    systemctl unmask pcscd.socket pcscd.service 2>/dev/null || true
    systemctl enable pcscd.socket 2>/dev/null || true
    systemctl restart pcscd.socket 2>/dev/null || true
    sleep 1
    systemctl restart pcscd.service 2>/dev/null || true
    sleep 4
    if command -v pcsc_scan >/dev/null 2>&1; then
        timeout 3 pcsc_scan 2>&1 | head -15 || true
    fi
}

_run_test_as() {
    local who="$1"
    local mode="$2"
    if [ "$who" = root ]; then
        "$PY" "$TEST" "$mode" 2>&1 || true
    elif [ "$mode" = pcsc ] && getent group scard >/dev/null 2>&1; then
        sudo -u "$APP_USER" sg scard -c "$PY $TEST $mode" 2>&1 || true
    else
        sudo -u "$APP_USER" "$PY" "$TEST" "$mode" 2>&1 || true
    fi
}

_try_nfcpy() {
    echo ""
    echo "--- Test nfcpy (pcscd OFF) ---"
    _stop_pcscd
    _reset_usb
    _disable_pcscd
    local out attempt
    for attempt in 1 2 3; do
        out="$(_run_test_as user nfcpy)"
        echo "$out"
        if [[ "$out" == OK:* ]]; then
            return 0
        fi
        echo "Tentativo $attempt fallito, retry..."
        _reset_usb
    done
    return 1
}

_try_pcsc() {
    echo ""
    echo "--- Test PC/SC (pcscd ON) ---"
    _start_pcscd
    local out

    echo "Test come root:"
    out="$(_run_test_as root pcsc)"
    echo "$out"

    echo "Test come $APP_USER (sg scard):"
    out="$(_run_test_as user pcsc)"
    echo "$out"
    if [[ "$out" == OK:* ]]; then
        return 0
    fi

    echo "Test come $APP_USER (diretto):"
    out="$(sudo -u "$APP_USER" "$PY" "$TEST" pcsc 2>&1 || true)"
    echo "$out"
    [[ "$out" == OK:* ]]
}

MODE=""

if [ "$NFC_MODE" = "nfcpy" ] || [ "$NFC_MODE" = "auto" ]; then
    if _try_nfcpy; then
        _set_backend "nfcpy"
        MODE="nfcpy"
        _disable_pcscd
    fi
fi

if [ -z "$MODE" ] && { [ "$NFC_MODE" = "pcsc" ] || [ "$NFC_MODE" = "auto" ]; }; then
    if _try_pcsc; then
        _set_backend "pcsc"
        MODE="pcsc"
    fi
fi

if [ -z "$MODE" ]; then
    echo ""
    echo "ERRORE: lettore non utilizzabile."
    echo ""
    echo "Diagnostica:"
    echo "  lsusb | grep 072f"
    echo "  sudo systemctl status pcscd"
    echo "  groups $APP_USER"
    echo ""
    echo "Prova:"
    echo "  1) Scollega USB, attendi 5s, ricollega"
    echo "  2) sudo reboot"
    echo "  3) sudo bash standalone/fix-nfc.sh"
    echo ""
    echo "Se PC/SC funziona solo come root, dopo fix serve: sudo reboot"
    exit 1
fi

echo ""
echo "=== OK — NFC_BACKEND=$MODE ==="
grep '^NFC_BACKEND=' "$ENV_FILE"
if [ "$MODE" = "pcsc" ]; then
    echo ""
    echo "IMPORTANTE: reboot consigliato per attivare gruppo scard:"
    echo "  sudo reboot"
fi
echo ""
echo "Riavvia kiosk:"
echo "  pkill -f run_kiosk.py || true"
echo "  bash ${APP_DIR}/standalone/launch_kiosk.sh"
