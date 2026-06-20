import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import terminal.config as config

log = logging.getLogger("nfc_reader")


def start_nfc_loop(callback) -> None:
    if config.MOCK_NFC:
        log.info("NFC mock — nessun lettore attivo")
        return

    try:
        import nfc
    except ImportError:
        log.error("nfcpy non installato")
        return

    log.info("Avvio lettore NFC ACR122U...")
    while True:
        try:
            with nfc.ContactlessFrontend("usb") as clf:
                while True:
                    tag = clf.connect(rdwr={"on-connect": lambda tag: False})
                    if tag is not None:
                        uid = tag.identifier.hex().upper()
                        callback(uid)
                        time.sleep(1)
        except Exception as e:
            log.warning("Errore NFC: %s — retry 5s", e)
            time.sleep(5)
