#!/bin/bash
# Avvia pcscd e attende rilevamento ACR122U
# sudo bash standalone/pcscd-on.sh

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PY="${APP_DIR}/.venv/bin/python"
TEST="${APP_DIR}/standalone/test-nfc.py"

if [ "$(id -u)" -ne 0 ]; then
    echo "Esegui con sudo"
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get install -y pcscd libpcsclite1 libccid libacsccid1 pcsc-tools 2>/dev/null || true

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
bash "$APP_DIR/standalone/fix-acr122u-kernel.sh"

# Scollega/ricollega consigliato: reset USB dopo blacklist
if command -v usbreset >/dev/null 2>&1; then
    _bus="$(lsusb -d 072f:2200 2>/dev/null | awk '{print $2}' | head -1)"
    _dev="$(lsusb -d 072f:2200 2>/dev/null | awk '{print $4}' | tr -d ':' | head -1)"
    if [ -n "$_bus" ] && [ -n "$_dev" ] && [ -e "/dev/bus/usb/${_bus}/${_dev}" ]; then
        usbreset "/dev/bus/usb/${_bus}/${_dev}" 2>/dev/null || true
        sleep 2
    fi
fi

systemctl unmask pcscd.socket pcscd.service 2>/dev/null || true
systemctl enable pcscd.socket 2>/dev/null || true
systemctl restart pcscd.socket 2>/dev/null || true
sleep 1
systemctl restart pcscd.service 2>/dev/null || true
sleep 4

echo "Stato pcscd:"
systemctl is-active pcscd.service pcscd.socket 2>&1 || true
echo ""

if command -v pcsc_scan >/dev/null 2>&1; then
    echo "--- pcsc_scan (15s — avvicina badge) ---"
    timeout 15 pcsc_scan 2>&1 | head -25 || true
    echo ""
fi

echo "--- test-nfc.py pcsc ---"
"$PY" "$TEST" pcsc 2>&1 || true
