import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import terminal.config as config

log = logging.getLogger("nfc_reader")


def _leggi_uid(clf) -> str | None:
    import nfc

    target = clf.sense(
        nfc.clf.RemoteTarget("106A"),
        nfc.clf.RemoteTarget("106B"),
        nfc.clf.RemoteTarget("212F"),
        nfc.clf.RemoteTarget("424F"),
        iterations=3,
        interval=0.2,
    )
    if target is None:
        return None
    tag = nfc.tag.activate(clf, target)
    if tag is None or not getattr(tag, "identifier", None):
        return None
    return tag.identifier.hex().upper()


def start_nfc_loop(callback) -> None:
    if config.MOCK_NFC:
        log.info("NFC mock — nessun lettore attivo")
        return

    try:
        import nfc
    except ImportError:
        log.error("nfcpy non installato")
        return

    log.info("Avvio lettore NFC ACR122U (USB diretto, senza pcscd)...")
    while True:
        try:
            with nfc.ContactlessFrontend("usb") as clf:
                log.info("Lettore NFC connesso")
                while True:
                    uid = _leggi_uid(clf)
                    if uid:
                        log.info("Badge rilevato: %s", uid)
                        callback(uid)
                        time.sleep(1.2)
        except Exception as e:
            err = str(e).lower()
            if "resource busy" in err or "unable to claim" in err or "access denied" in err:
                log.error(
                    "USB NFC occupato (spesso da pcscd). Esegui: sudo systemctl stop pcscd && "
                    "sudo systemctl disable pcscd && sudo systemctl restart timbranfc-kiosk"
                )
            else:
                log.warning("Errore NFC: %s — retry 5s", e)
            time.sleep(5)
