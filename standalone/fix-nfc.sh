#!/bin/bash
# Configura lettore ACR122U per kiosk standalone
# sudo bash standalone/fix-nfc.sh
#
# Prova PC/SC (pcscd + gruppo scard); se fallisce → nfcpy con pcscd disattivato.

set -euo pipefail

APP_USER="${APP_USER:-${SUDO_USER:-gpastorino}}"
APP_DIR="${APP_DIR:-/home/${APP_USER}/TimbraNFC}"
ENV_FILE="${APP_DIR}/.env"
UDEV_RULE="/etc/udev/rules.d/99-timbranfc-acr122u.rules"
PY="${APP_DIR}/.venv/bin/python"

if [ "$(id -u)" -ne 0 ]; then
    echo "Esegui con sudo"
    exit 1
fi

echo "=== Fix NFC TimbraNFC ==="

if ! lsusb 2>/dev/null | grep -qiE '072f|acr'; then
    echo "ATTENZIONE: ACR122U non trovato su USB (lsusb)"
    echo "Controlla cavo USB e alimentazione Pi"
fi

export DEBIAN_FRONTEND=noninteractive
apt-get install -y pcscd libpcsclite1 2>/dev/null || true

# Gruppo scard (creato da pcscd su Debian; fallback manuale)
if ! getent group scard >/dev/null 2>&1; then
    groupadd scard 2>/dev/null || true
fi
usermod -aG scard "$APP_USER" 2>/dev/null || true
echo "Gruppi $APP_USER: $(id -nG "$APP_USER" 2>/dev/null | tr ' ' ',')"

cat > "$UDEV_RULE" <<'EOF'
# ACR122U — accesso lettore NFC
SUBSYSTEM=="usb", ATTRS{idVendor}=="072f", ATTRS{idProduct}=="2200", MODE="0664", GROUP="scard"
EOF
udevadm control --reload-rules
udevadm trigger

systemctl enable pcscd pcscd.socket 2>/dev/null || true
systemctl restart pcscd pcscd.socket 2>/dev/null || true
sleep 1

touch "$ENV_FILE"
chown "${APP_USER}:${APP_USER}" "$ENV_FILE"

_test_pcsc() {
    sudo -u "$APP_USER" sg scard -c "$PY" <<PY 2>&1
import sys, time
sys.path.insert(0, "${APP_DIR}")
from smartcard.System import readers
r = readers()
if not r:
    print("FAIL:no_reader")
    sys.exit(1)
conn = r[0].createConnection()
conn.connect()
d, s1, s2 = conn.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
conn.disconnect()
if s1 == 0x90 and d:
    print("OK:" + "".join(f"{b:02X}" for b in d))
else:
    print("OK:reader_ready")
PY
}

_test_nfcpy() {
    sudo -u "$APP_USER" "$PY" <<PY 2>&1
import sys
sys.path.insert(0, "${APP_DIR}")
import nfc
for path in ("usb:072f:2200", "usb"):
    try:
        with nfc.ContactlessFrontend(path) as clf:
            print(f"OK:{path}")
            sys.exit(0)
    except Exception as e:
        print(f"FAIL:{path}:{e}")
print("FAIL:all")
sys.exit(1)
PY
}

_set_backend() {
    local mode="$1"
    if grep -q '^NFC_BACKEND=' "$ENV_FILE"; then
        sed -i "s/^NFC_BACKEND=.*/NFC_BACKEND=${mode}/" "$ENV_FILE"
    else
        echo "NFC_BACKEND=${mode}" >> "$ENV_FILE"
    fi
}

echo ""
echo "--- Test PC/SC (gruppo scard) ---"
PCSC_OUT=""
PCSC_OUT="$(_test_pcsc)" || PCSC_OUT="FAIL:${PCSC_OUT}"
echo "$PCSC_OUT"

if [[ "$PCSC_OUT" == OK:* ]]; then
    _set_backend "pcsc"
    echo ""
    echo "Configurato: NFC_BACKEND=pcsc (pcscd attivo)"
    MODE="pcsc"
else
    echo ""
    echo "PC/SC non disponibile ($PCSC_OUT) — passo a nfcpy"
    systemctl stop pcscd pcscd.socket 2>/dev/null || true
    systemctl disable pcscd pcscd.socket 2>/dev/null || true
    sleep 1

    echo ""
    echo "--- Test nfcpy (pcscd OFF) ---"
    NFCPY_OUT=""
    NFCPY_OUT="$(_test_nfcpy)" || NFCPY_OUT="FAIL"
    echo "$NFCPY_OUT"

    if [[ "$NFCPY_OUT" == OK:* ]]; then
        _set_backend "nfcpy"
        echo ""
        echo "Configurato: NFC_BACKEND=nfcpy (pcscd disabilitato)"
        MODE="nfcpy"
    else
        _set_backend "auto"
        echo ""
        echo "ERRORE: né PC/SC né nfcpy funzionano."
        echo "Controlla: lsusb | grep 072f"
        echo "Riavvia il Pi e riesegui: sudo bash standalone/fix-nfc.sh"
        exit 1
    fi
fi

echo ""
echo "=== Fatto (modalità: $MODE) ==="
grep '^NFC_BACKEND=' "$ENV_FILE"
echo ""
echo "Riavvia kiosk:"
echo "  pkill -f run_kiosk.py || true"
echo "  bash ${APP_DIR}/standalone/launch_kiosk.sh"
echo "  tail -f /tmp/timbranfc-kiosk.log"
echo ""
if [ "$MODE" = "pcsc" ]; then
    echo "Nota: dopo usermod serve reboot o nuovo login desktop per gruppo scard."
    echo "Il kiosk usa 'sg scard' se necessario."
fi
