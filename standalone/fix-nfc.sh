#!/bin/bash
# Configura lettore ACR122U per kiosk standalone
# sudo bash standalone/fix-nfc.sh
#
# Modalità consigliata: NFC_BACKEND=auto (nfcpy → fallback pcsc)

set -euo pipefail

APP_USER="${APP_USER:-${SUDO_USER:-gpastorino}}"
APP_DIR="${APP_DIR:-/home/${APP_USER}/TimbraNFC}"
ENV_FILE="${APP_DIR}/.env"

if [ "$(id -u)" -ne 0 ]; then
    echo "Esegui con sudo"
    exit 1
fi

echo "=== Fix NFC TimbraNFC ==="

if ! lsusb 2>/dev/null | grep -qiE '072f|acr'; then
    echo "ATTENZIONE: ACR122U non trovato su USB (lsusb)"
    echo "Controlla cavo USB e alimentazione Pi"
fi

# Gruppo scard per PC/SC
if getent group scard >/dev/null 2>&1; then
    usermod -aG scard "$APP_USER" 2>/dev/null || true
    echo "Utente $APP_USER nel gruppo scard"
fi

systemctl enable pcscd pcscd.socket 2>/dev/null || true
systemctl start pcscd pcscd.socket 2>/dev/null || true

touch "$ENV_FILE"
if grep -q '^NFC_BACKEND=' "$ENV_FILE"; then
    sed -i 's/^NFC_BACKEND=.*/NFC_BACKEND=auto/' "$ENV_FILE"
else
    echo "NFC_BACKEND=auto" >> "$ENV_FILE"
fi
chown "${APP_USER}:${APP_USER}" "$ENV_FILE"

echo ""
echo "NFC_BACKEND=auto in $ENV_FILE"
echo ""
echo "Test PC/SC (5s — avvicina badge):"
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/python" <<PY || true
import sys, time
sys.path.insert(0, "${APP_DIR}")
try:
    from smartcard.System import readers
    r = readers()
    print("Reader PC/SC:", r[0] if r else "NESSUNO")
    if r:
        conn = r[0].createConnection()
        t = time.time() + 5
        while time.time() < t:
            try:
                conn.connect()
                d, s1, s2 = conn.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
                conn.disconnect()
                if s1 == 0x90 and d:
                    print("UID OK:", "".join(f"{b:02X}" for b in d))
                    break
            except Exception:
                pass
            time.sleep(0.3)
        else:
            print("(nessun badge in 5s — normale se non avvicinato)")
except Exception as e:
    print("PC/SC errore:", e)
PY

echo ""
echo "Riavvia kiosk:"
echo "  pkill -f run_kiosk.py || true"
echo "  sudo -u $APP_USER bash ${APP_DIR}/standalone/launch_kiosk.sh"
echo ""
echo "Se nfcpy serve esplicitamente (pcscd OFF):"
echo "  sudo systemctl stop pcscd pcscd.socket"
echo "  sed -i 's/^NFC_BACKEND=.*/NFC_BACKEND=nfcpy/' ${ENV_FILE}"
