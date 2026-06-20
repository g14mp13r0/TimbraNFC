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

    backend = config.NFC_BACKEND
    if backend == "nfcpy":
        _run_nfcpy(callback)
        return
    if backend == "pcsc":
        _run_pcsc(callback)
        return

    # auto: tenta nfcpy, poi fallback a pcsc (piu stabile su ACR122U)
    if _run_nfcpy(callback, once=True):
        return
    log.warning("Fallback al backend PC/SC")
    _run_pcsc(callback)


def _run_nfcpy(callback, once: bool = False) -> bool:
    try:
        import nfc
    except ImportError:
        log.error("nfcpy non installato")
        return False

    device_paths = [config.NFC_DEVICE_PATH, "usb"]
    seen: set[str] = set()
    device_paths = [p for p in device_paths if not (p in seen or seen.add(p))]
    log.info("Backend NFC: nfcpy (path: %s)", ", ".join(device_paths))

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

        if connected:
            continue
        if once:
            return False

        err = str(last_error or "").lower()
        if "resource busy" in err or "unable to claim" in err or "access denied" in err:
            log.error(
                "USB NFC occupato — ferma pcscd: sudo systemctl stop pcscd pcscd.socket "
                "oppure usa NFC_BACKEND=auto in .env"
            )
        elif "no such device" in err:
            log.error(
                "Lettore non raggiungibile via nfcpy — controlla USB (lsusb), "
                "cavo, oppure: bash standalone/fix-nfc.sh"
            )
        else:
            log.warning("Errore NFC: %s — retry 5s", last_error)
        time.sleep(5)


def _run_pcsc(callback) -> None:
    try:
        from smartcard.Exceptions import CardConnectionException, NoCardException
        from smartcard.System import readers
    except ImportError:
        log.error("pyscard non installato (pip install pyscard)")
        return

    log.info("Backend NFC: PC/SC (ACR122U via pcscd)")
    last_uid = None
    last_emit = 0.0
    cooldown = 1.2

    while True:
        try:
            rlist = readers()
            if not rlist:
                log.warning("Nessun reader PC/SC disponibile — retry 3s")
                time.sleep(3)
                continue
            reader = rlist[0]
            conn = reader.createConnection()
            try:
                conn.connect()
                data, sw1, sw2 = conn.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
                if sw1 == 0x90 and sw2 == 0x00 and data:
                    uid = "".join(f"{b:02X}" for b in data)
                    now = time.time()
                    if uid != last_uid or (now - last_emit) > cooldown:
                        last_uid = uid
                        last_emit = now
                        log.info("Badge rilevato (PC/SC): %s", uid)
                        callback(uid)
                else:
                    # Nessuna carta o APDU non pronto: non floodare log
                    pass
            except (NoCardException, CardConnectionException):
                pass
            except Exception as e:
                log.warning("Errore PC/SC lettura badge: %s", e)
            finally:
                try:
                    conn.disconnect()
                except Exception:
                    pass
            time.sleep(0.25)
        except Exception as e:
            log.warning("Errore backend PC/SC: %s — retry 2s", e)
            time.sleep(2)
