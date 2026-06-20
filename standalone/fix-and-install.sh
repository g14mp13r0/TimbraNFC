#!/bin/bash
# Ripara apt e completa installazione se install-raspberry.sh è fallito a metà
# sudo bash standalone/fix-and-install.sh

set -euo pipefail

APP_USER="${APP_USER:-${SUDO_USER:-$(logname 2>/dev/null || echo gpastorino)}}"
APP_DIR="${APP_DIR:-/home/${APP_USER}/TimbraNFC}"

echo "=== Fix apt + install TimbraNFC ==="

export DEBIAN_FRONTEND=noninteractive

# 1. Ripara dipendenze rotte
sudo apt remove --purge -y xinput-calibrator 2>/dev/null || true
sudo apt --fix-broken install -y
sudo apt update

# 2. Pacchetti necessari (NO nginx, NO libusb-dev legacy)
sudo apt install -y \
    python3 python3-venv python3-pip python3-dev git \
    pcscd libccid swig libpcsclite-dev build-essential

sudo systemctl enable --now pcscd

# 3. Install app
cd "$APP_DIR"
sudo APP_USER="$APP_USER" APP_DIR="$APP_DIR" bash standalone/install-raspberry.sh
