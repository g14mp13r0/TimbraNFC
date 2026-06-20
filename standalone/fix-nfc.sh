#!/bin/bash
# Configura lettore ACR122U per kiosk standalone
# sudo bash standalone/fix-nfc.sh
#
# Default: nfcpy + pcscd disabilitato (più stabile su Pi con ACR122U)

set -euo pipefail

APP_USER="${APP_USER:-${SUDO_USER:-gpastorino}}"
APP_DIR="${APP_DIR:-/home/${APP_USER}/TimbraNFC}"
ENV_FILE="${APP_DIR}/.env"
UDEV_RULE="/etc/udev/rules.d/99-timbranfc-acr122u.rules"
PY="${APP_DIR}/.venv/bin/python"
TEST="${APP_DIR}/standalone/test-nfc.py"
# nfcpy | pcsc | auto
NFC_MODE="${NFC_MODE:-nfcpy}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Esegui con sudo"
    exit 1
fi

echo "=== Fix NFC TimbraNFC (modalità richiesta: $NFC_MODE) ==="

if ! lsusb 2>/dev/null | grep -qiE '072f|acr'; then
    echo "ERRORE: ACR122U non trovato — lsusb:"
    lsusb 2>/dev/null || true
    echo "Collega il lettore USB e rilancia lo script."
    exit 1
fi
lsusb | grep -iE '072f|acr' || true

export DEBIAN_FRONTEND=noninteractive
apt-get install -y pcscd libpcsclite1 2>/dev/null || true

if ! getent group scard >/dev/null 2>&1; then
    groupadd scard 2>/dev/null || true
fi
usermod -aG scard "$APP_USER" 2>/dev/null || true

cat > "$UDEV_RULE" <<'EOF'
SUBSYSTEM=="usb", ATTRS{idVendor}=="072f", ATTRS{idProduct}=="2200", MODE="0666"
EOF
udevadm control --reload-rules
udevadm trigger
sleep 2

touch "$ENV_FILE"
chown "${APP_USER}:${APP_USER}" "$ENV_FILE"

_set_backend() {
    if grep -q '^NFC_BACKEND=' "$ENV_FILE"; then
        sed -i "s/^NFC_BACKEND=.*/NFC_BACKEND=$1/" "$ENV_FILE"
    else
        echo "NFC_BACKEND=$1" >> "$ENV_FILE"
    fi
}

_run_test() {
    local mode="$1"
    local runner=(sudo -u "$APP_USER" "$PY" "$TEST" "$mode")
    if [ "$mode" = "pcsc" ] && getent group scard >/dev/null 2>&1; then
        runner=(sudo -u "$APP_USER" sg scard -c "$PY $TEST $mode")
    fi
    "${runner[@]}" 2>&1 || true
}

_stop_pcscd() {
    systemctl stop pcscd pcscd.socket 2>/dev/null || true
    systemctl disable pcscd pcscd.socket 2>/dev/null || true
    sleep 2
}

_start_pcscd() {
    systemctl enable pcscd pcscd.socket 2>/dev/null || true
    systemctl start pcscd pcscd.socket 2>/dev/null || true
    sleep 2
}

MODE=""

if [ "$NFC_MODE" = "nfcpy" ] || [ "$NFC_MODE" = "auto" ]; then
    echo ""
    echo "--- Test nfcpy (pcscd OFF) ---"
    _stop_pcscd
    OUT="$(_run_test nfcpy)"
    echo "$OUT"
    if [[ "$OUT" == OK:* ]]; then
        _set_backend "nfcpy"
        MODE="nfcpy"
    fi
fi

if [ -z "$MODE" ] && { [ "$NFC_MODE" = "pcsc" ] || [ "$NFC_MODE" = "auto" ]; }; then
    echo ""
    echo "--- Test PC/SC (pcscd ON, gruppo scard) ---"
    _start_pcscd
    OUT="$(_run_test pcsc)"
    echo "$OUT"
    if [[ "$OUT" == OK:* ]]; then
        _set_backend "pcsc"
        MODE="pcsc"
    else
        echo "PC/SC fallito — per kiosk dedicato usa: NFC_MODE=nfcpy sudo bash standalone/fix-nfc.sh"
    fi
fi

if [ -z "$MODE" ]; then
    echo ""
    echo "ERRORE: lettore non utilizzabile."
    echo "Prova:"
    echo "  1) Scollega e ricollega USB ACR122U"
    echo "  2) sudo reboot"
    echo "  3) NFC_MODE=nfcpy sudo bash standalone/fix-nfc.sh"
    exit 1
fi

if [ "$MODE" = "nfcpy" ]; then
    _stop_pcscd
fi

echo ""
echo "=== OK — NFC_BACKEND=$MODE ==="
grep '^NFC_BACKEND=' "$ENV_FILE"
echo ""
echo "Riavvia kiosk:"
echo "  pkill -f run_kiosk.py || true"
echo "  bash ${APP_DIR}/standalone/launch_kiosk.sh"
echo "  tail -f /tmp/timbranfc-kiosk.log"
