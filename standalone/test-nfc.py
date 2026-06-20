#!/usr/bin/env python3
"""Test lettore NFC — usato da fix-nfc.sh"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

mode = sys.argv[1] if len(sys.argv) > 1 else "all"


def test_pcsc() -> int:
    try:
        from smartcard.System import readers
    except ImportError as e:
        print(f"FAIL:pyscard:{e}")
        return 1
    try:
        r = readers()
    except Exception as e:
        print(f"FAIL:pcsc_context:{e}")
        return 1
    if not r:
        print("FAIL:no_reader")
        return 1
    try:
        conn = r[0].createConnection()
        conn.connect()
        data, sw1, sw2 = conn.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
        conn.disconnect()
        if sw1 == 0x90 and sw2 == 0x00 and data:
            uid = "".join(f"{b:02X}" for b in data)
            print(f"OK:uid:{uid}")
        else:
            print("OK:reader_ready")
        return 0
    except Exception as e:
        print(f"FAIL:read:{e}")
        return 1


def test_nfcpy() -> int:
    try:
        import nfc
    except ImportError as e:
        print(f"FAIL:nfcpy_import:{e}")
        return 1
    paths = ["usb:072f:2200", "usb"]
    last_err = ""
    for path in paths:
        try:
            with nfc.ContactlessFrontend(path) as clf:
                print(f"OK:path:{path}")
                return 0
        except Exception as e:
            last_err = f"{path}:{e}"
            print(f"WARN:{last_err}", file=sys.stderr)
    print(f"FAIL:nfcpy:{last_err or 'no_path'}")
    return 1


if __name__ == "__main__":
    if mode == "pcsc":
        sys.exit(test_pcsc())
    if mode == "nfcpy":
        sys.exit(test_nfcpy())
    if test_nfcpy() == 0:
        sys.exit(0)
    sys.exit(test_pcsc())
