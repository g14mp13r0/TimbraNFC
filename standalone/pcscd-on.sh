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
apt-get install -y pcscd libpcsclite1 libccid pcsc-tools 2>/dev/null || true

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
    echo "--- pcsc_scan (5s) ---"
    timeout 5 pcsc_scan 2>&1 | head -20 || true
    echo ""
fi

echo "--- test-nfc.py pcsc ---"
"$PY" "$TEST" pcsc 2>&1 || true
