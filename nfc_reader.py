import logging
import time

import config

log = logging.getLogger("nfc_reader")


def start_nfc_loop(callback) -> None:
    if config.MOCK_NFC:
        log.info("NFC in modalità mock — nessun lettore attivo")
        return

    try:
        import nfc
    except ImportError:
        log.error("nfcpy non installato. Esegui: pip install nfcpy")
        return

    log.info("Avvio lettore NFC (ACR122U via USB)...")

    while True:
        try:
            with nfc.ContactlessFrontend("usb") as clf:
                log.info("Lettore NFC connesso")
                while True:
                    tag = clf.connect(rdwr={"on-connect": lambda tag: False})
                    if tag is not None:
                        uid = tag.identifier.hex().upper()
                        log.debug("Badge rilevato: %s", uid)
                        callback(uid)
                        time.sleep(1)
        except Exception as e:
            log.warning("Errore lettore NFC: %s — riprovo tra 5s", e)
            time.sleep(5)
