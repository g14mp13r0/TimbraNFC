#!/bin/bash
# Diagnostica lettore NFC ACR122U sul Raspberry Pi
# bash standalone/diagnose-nfc.sh

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "=== Diagnostica NFC TimbraNFC ==="
echo ""

echo "--- USB ---"
lsusb 2>/dev/null | grep -iE '072f|acr|nfc|smart' || echo "(ACR122U non trovato su USB — controlla cavo)"
echo ""

echo "--- pcscd (deve essere inactive per nfcpy) ---"
systemctl is-active pcscd 2>&1 || true
echo ""

echo "--- MOCK_NFC in .env ---"
grep -E '^MOCK_NFC=' "$APP_DIR/.env" 2>/dev/null || echo "MOCK_NFC non impostato (default 0)"
echo ""

echo "--- servizi ---"
systemctl is-active timbranfc-kiosk 2>&1 || true
systemctl is-active timbranfc-server 2>&1 || true
echo ""

echo "--- log kiosk (NFC) ---"
journalctl -u timbranfc-kiosk -n 25 --no-pager 2>/dev/null | grep -iE 'nfc|badge|usb|pcscd|errore|error' || journalctl -u timbranfc-kiosk -n 10 --no-pager
echo ""

echo "--- test nfcpy (3 secondi, avvicina badge) ---"
if [ -f "$APP_DIR/.venv/bin/python" ]; then
    "$APP_DIR/.venv/bin/python" <<'PY' || true
import sys
sys.path.insert(0, ".")
try:
    import nfc
    print("nfcpy OK")
    with nfc.ContactlessFrontend("usb") as clf:
        print("Lettore USB aperto — avvicina badge entro 3s...")
        target = clf.sense(nfc.clf.RemoteTarget("106A"), iterations=15, interval=0.2)
        if target is None:
            print("Nessun badge rilevato (timeout)")
        else:
            tag = nfc.tag.activate(clf, target)
            if tag and tag.identifier:
                print("UID:", tag.identifier.hex().upper())
            else:
                print("Badge rilevato ma UID non letto")
except Exception as e:
    print("ERRORE:", e)
    if "busy" in str(e).lower() or "claim" in str(e).lower():
        print("→ Prova: sudo systemctl stop pcscd && sudo systemctl disable pcscd")
PY
else
    echo "venv non trovato in $APP_DIR/.venv"
fi

echo ""
echo "Fix rapido:"
echo "  sudo systemctl stop pcscd"
echo "  sudo systemctl disable pcscd"
echo "  sudo systemctl restart timbranfc-kiosk"
