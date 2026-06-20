#!/bin/bash
# Installa TimbraNFC sulla rootfs Raspberry montata da PC Linux
#
# Prerequisito: SD con Raspberry Pi OS già flashato (Pi Imager)
#
# Uso:
#   1. Collega SD via USB
#   2. Monta la partizione root (ext4), es. /media/$USER/rootfs
#   3. sudo bash standalone/install-on-sd.sh /media/$USER/rootfs
#
# Oppure monta manualmente:
#   sudo mkdir -p /mnt/rpi-root /mnt/rpi-boot
#   sudo mount /dev/sdX2 /mnt/rpi-root    # root ext4
#   sudo mount /dev/sdX1 /mnt/rpi-boot     # boot vfat
#   sudo bash standalone/install-on-sd.sh /mnt/rpi-root /mnt/rpi-boot

set -euo pipefail

ROOTFS="${1:?Usage: $0 /path/to/rootfs [/path/to/boot]}"
BOOTFS="${2:-}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Esegui con sudo: sudo bash $0 $ROOTFS"
    exit 1
fi

if [ ! -f "$ROOTFS/etc/os-release" ]; then
    echo "Errore: $ROOTFS non sembra una rootfs Raspberry Pi OS (manca /etc/os-release)"
    exit 1
fi

APP_DIR="$ROOTFS/home/pi/TimbraNFC"
REPO_SRC="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Install TimbraNFC su SD ==="
echo "Rootfs: $ROOTFS"
echo "Sorgente repo: $REPO_SRC"

# Abilita SSH al primo boot (opzionale)
if [ -n "$BOOTFS" ] && [ -d "$BOOTFS" ]; then
    touch "$BOOTFS/ssh"
    echo "SSH abilitato al boot (file ssh in boot)"
fi

# Copia progetto sulla SD
mkdir -p "$APP_DIR"
rsync -a --delete \
    --exclude '.venv' --exclude 'data' --exclude '__pycache__' --exclude '.git' \
    "$REPO_SRC/" "$APP_DIR/"
# Mantieni .git se presente (utile per aggiornamenti)
if [ -d "$REPO_SRC/.git" ]; then
    rsync -a "$REPO_SRC/.git" "$APP_DIR/"
fi

chown -R 1000:1000 "$APP_DIR" 2>/dev/null || chroot "$ROOTFS" chown -R pi:pi /home/pi/TimbraNFC

# Config
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.standalone.example" "$APP_DIR/.env"
    chown 1000:1000 "$APP_DIR/.env" 2>/dev/null || chroot "$ROOTFS" chown pi:pi /home/pi/TimbraNFC/.env
fi
mkdir -p "$APP_DIR/data"
chown 1000:1000 "$APP_DIR/data" 2>/dev/null || chroot "$ROOTFS" chown pi:pi /home/pi/TimbraNFC/data

# Script first-boot (esegue install completa al primo avvio del Pi)
cat > "$ROOTFS/etc/systemd/system/timbranfc-firstboot.service" <<'UNIT'
[Unit]
Description=TimbraNFC first-boot install
After=network-online.target
Wants=network-online.target
ConditionPathExists=/home/pi/TimbraNFC/.firstboot_pending

[Service]
Type=oneshot
User=pi
WorkingDirectory=/home/pi/TimbraNFC
ExecStart=/home/pi/TimbraNFC/standalone/install-raspberry.sh
ExecStartPost=/bin/rm -f /home/pi/TimbraNFC/.firstboot_pending
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
UNIT

touch "$APP_DIR/.firstboot_pending"
chown 1000:1000 "$APP_DIR/.firstboot_pending" 2>/dev/null || true

# Abilita first-boot in chroot
mount --bind /dev "$ROOTFS/dev" 2>/dev/null || true
mount --bind /proc "$ROOTFS/proc" 2>/dev/null || true
mount --bind /sys "$ROOTFS/sys" 2>/dev/null || true
mount --bind /dev/pts "$ROOTFS/dev/pts" 2>/dev/null || true

if [ -f "$ROOTFS/usr/bin/qemu-arm-static" ] || command -v qemu-arm-static &>/dev/null; then
    # ARM chroot da PC x86 (opzionale, se qemu-user-static installato)
    if ! [ -f "$ROOTFS/usr/bin/qemu-arm-static" ]; then
        cp "$(which qemu-arm-static)" "$ROOTFS/usr/bin/" 2>/dev/null || true
    fi
    echo "Tentativo installazione completa in chroot ARM..."
    chroot "$ROOTFS" bash -c "cd /home/pi/TimbraNFC && bash standalone/install-raspberry.sh" && rm -f "$APP_DIR/.firstboot_pending" || \
        echo "Chroot fallito — installazione al primo boot del Pi (timbranfc-firstboot.service)"
else
    echo "qemu-arm-static non trovato — installazione completa al PRIMO BOOT del Raspberry"
fi

chroot "$ROOTFS" systemctl enable timbranfc-firstboot.service 2>/dev/null || \
    ln -sf /etc/systemd/system/timbranfc-firstboot.service "$ROOTFS/etc/systemd/system/multi-user.target.wants/timbranfc-firstboot.service" 2>/dev/null || true

# Cleanup mounts
umount "$ROOTFS/dev/pts" 2>/dev/null || true
umount "$ROOTFS/dev" 2>/dev/null || true
umount "$ROOTFS/proc" 2>/dev/null || true
umount "$ROOTFS/sys" 2>/dev/null || true

echo ""
echo "=== SD pronta ==="
echo "1. Smonta in sicurezza la SD ed inseriscila nel Raspberry"
echo "2. Collega Ethernet (consigliato al primo boot per apt/pip)"
echo "3. Al primo avvio parte l'installazione automatica (~5-10 min)"
echo "4. Dashboard: http://<ip-raspberry>:8080"
echo ""
echo "Monitora dal Pi: journalctl -u timbranfc-firstboot -f"
