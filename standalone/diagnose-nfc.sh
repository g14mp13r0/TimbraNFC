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

echo "--- pcscd/socket (devono essere active per backend pcsc) ---"
systemctl is-active pcscd 2>&1 || true
systemctl is-active pcscd.socket 2>&1 || true
echo ""

echo "--- MOCK_NFC/NFC_BACKEND in .env ---"
grep -E '^(MOCK_NFC|NFC_BACKEND)=' "$APP_DIR/.env" 2>/dev/null || echo "MOCK_NFC/NFC_BACKEND non impostati"
echo ""

echo "--- servizi ---"
systemctl is-active timbranfc-kiosk 2>&1 || true
systemctl is-active timbranfc-server 2>&1 || true
echo ""

echo "--- log kiosk (NFC) ---"
journalctl -u timbranfc-kiosk -n 25 --no-pager 2>/dev/null | grep -iE 'nfc|badge|usb|pcscd|errore|error' || journalctl -u timbranfc-kiosk -n 10 --no-pager
echo ""

echo "--- test PC/SC (5 secondi, avvicina badge) ---"
if [ -f "$APP_DIR/.venv/bin/python" ]; then
    "$APP_DIR/.venv/bin/python" <<'PY' || true
import sys
sys.path.insert(0, ".")
try:
    from smartcard.System import readers
    print("pyscard OK")
    r = readers()
    if not r:
        print("Nessun reader PC/SC")
    else:
        print("Reader:", r[0])
        conn = r[0].createConnection()
        import time
        deadline = time.time() + 5
        got = False
        while time.time() < deadline:
            try:
                conn.connect()
                data, sw1, sw2 = conn.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
                conn.disconnect()
                if sw1 == 0x90 and sw2 == 0x00 and data:
                    print("UID:", "".join(f"{b:02X}" for b in data))
                    got = True
                    break
            except Exception:
                pass
            time.sleep(0.3)
        if not got:
            print("Nessun badge rilevato (timeout)")
except Exception as e:
    print("ERRORE:", e)
    print("→ Prova: sudo systemctl enable --now pcscd pcscd.socket")
PY
else
    echo "venv non trovato in $APP_DIR/.venv"
fi

echo ""
echo "Fix rapido:"
echo "  sudo systemctl enable --now pcscd pcscd.socket"
echo "  sudo systemctl restart timbranfc-kiosk"
