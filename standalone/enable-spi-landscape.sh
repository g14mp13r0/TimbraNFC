#!/bin/bash
# Rotazione landscape permanente display SPI 3.5" (320x480 → 480x320)
# sudo bash standalone/enable-spi-landscape.sh
#
# Su XWayland xrandr fallisce (BadMatch): serve rotazione a boot.

set -euo pipefail

CONFIG="${1:-/boot/firmware/config.txt}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Esegui con sudo"
    exit 1
fi

if [ ! -f "$CONFIG" ]; then
    CONFIG=/boot/config.txt
fi

if [ ! -f "$CONFIG" ]; then
    echo "config.txt non trovato in /boot/firmware né /boot" >&2
    exit 1
fi

cp "$CONFIG" "${CONFIG}.bak.timbranfc-$(date +%Y%m%d%H%M%S)"

# display_rotate: 0=0° 1=90° 2=180° 3=270° (Raspberry Pi firmware)
if grep -q '^display_rotate=' "$CONFIG"; then
    sed -i 's/^display_rotate=.*/display_rotate=1/' "$CONFIG"
else
    echo 'display_rotate=1' >> "$CONFIG"
fi

# Alcuni overlay SPI usano lcd_rotate (ignorato se non supportato)
if grep -q '^lcd_rotate=' "$CONFIG"; then
    sed -i 's/^lcd_rotate=.*/lcd_rotate=1/' "$CONFIG"
fi

echo "=== Rotazione SPI abilitata in $CONFIG ==="
grep -E '^display_rotate=|^lcd_rotate=' "$CONFIG" || true
echo ""
echo "Riavvia il Pi:"
echo "  sudo reboot"
echo ""
echo "Dopo reboot, da SSH:"
echo "  cd ~/TimbraNFC && bash standalone/ssh-touch-fix.sh"
