#!/bin/bash
# Rimuove driver kernel NFC che bloccano ACR122U (072f:2200)
# sudo bash standalone/fix-acr122u-kernel.sh

set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)/modprobe.d/blacklist-timbranfc-nfc.conf"

if [ "$(id -u)" -ne 0 ]; then
    echo "Esegui con sudo"
    exit 1
fi

echo "=== Fix kernel ACR122U (blacklist pn533/nfc) ==="

cp "$SRC" /etc/modprobe.d/blacklist-timbranfc-nfc.conf

for mod in pn533_usb pn533 nfc; do
    if lsmod | awk '{print $1}' | grep -qx "$mod"; then
        echo "Rimuovo modulo $mod..."
        modprobe -r "$mod" 2>/dev/null || rmmod "$mod" 2>/dev/null || true
    fi
done

echo ""
echo "Moduli NFC kernel:"
lsmod | grep -E 'pn533|^nfc' || echo "(nessuno — OK)"

if lsusb 2>/dev/null | grep -qi 072f:2200; then
    echo ""
    echo "ACR122U su USB: OK"
    echo "Consigliato: scollega e ricollega USB, poi:"
    echo "  sudo bash $(dirname "$0")/pcscd-on.sh"
else
    echo ""
    echo "ACR122U non su USB — collega il lettore"
fi

echo ""
echo "Per rendere permanente dopo reboot: già in /etc/modprobe.d/"
echo "Se ancora non funziona: sudo reboot"
