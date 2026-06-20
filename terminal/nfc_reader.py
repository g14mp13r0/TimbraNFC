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

    device_paths = [config.NFC_DEVICE_PATH, "usb"]
    # Dedup mantenendo ordine
    seen: set[str] = set()
    device_paths = [p for p in device_paths if not (p in seen or seen.add(p))]

    log.info(
        "Avvio lettore NFC ACR122U (USB diretto, senza pcscd). Path tentati: %s",
        ", ".join(device_paths),
    )
    while True:
        last_error: Exception | None = None
        connected = False
        for device_path in device_paths:
            try:
                with nfc.ContactlessFrontend(device_path) as clf:
                    connected = True
                    log.info("Lettore NFC connesso su path: %s", device_path)
                    while True:
                        uid = _leggi_uid(clf)
                        if uid:
                            log.info("Badge rilevato: %s", uid)
                            callback(uid)
                            time.sleep(1.2)
            except Exception as e:
                last_error = e
                log.warning("Apertura NFC fallita su %s: %s", device_path, e)

        if not connected:
            err = str(last_error or "").lower()
            if "resource busy" in err or "unable to claim" in err or "access denied" in err:
                log.error(
                    "USB NFC occupato (spesso da pcscd/socket). Esegui: "
                    "sudo systemctl stop pcscd pcscd.socket && "
                    "sudo systemctl disable pcscd pcscd.socket && "
                    "sudo systemctl restart timbranfc-kiosk"
                )
            elif "no such device" in err:
                log.error(
                    "Lettore visto da USB ma non inizializzabile via nfcpy. "
                    "Prova scollega/ricollega ACR122U e riavvia kiosk."
                )
            else:
                log.warning("Errore NFC: %s — retry 5s", last_error)
            time.sleep(5)
