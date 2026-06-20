#!/bin/bash
# Ferma pcscd completamente (socket + service) per liberare ACR122U a nfcpy
# sudo bash standalone/pcscd-off.sh

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Esegui con sudo"
    exit 1
fi

echo "Fermo pcscd (service + socket)..."
systemctl stop pcscd.service 2>/dev/null || true
systemctl stop pcscd.socket 2>/dev/null || true
sleep 2

if systemctl is-active --quiet pcscd.socket 2>/dev/null; then
    echo "pcscd.socket ancora attivo — mask temporaneo"
    systemctl mask pcscd.socket 2>/dev/null || true
    systemctl stop pcscd.socket 2>/dev/null || true
fi

echo "Stato:"
systemctl is-active pcscd.service 2>&1 || true
systemctl is-active pcscd.socket 2>&1 || true
echo ""
echo "Ora test nfcpy:"
echo "  ~/TimbraNFC/.venv/bin/python ~/TimbraNFC/standalone/test-nfc.py nfcpy"
