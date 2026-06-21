#!/usr/bin/env python3
"""Kiosk timbratrice — solo display locale, nessuna dashboard."""

import logging
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import requests

import terminal.config as config
import terminal.device_identity as device_identity
import terminal.local_queue as local_queue
import terminal.sync_agent as sync_agent
from shared.kiosk_i18n import t
from terminal.kiosk_ui import KioskUI
from terminal.nfc_reader import start_nfc_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("kiosk")


def _attendi_server(timeout: int = 90) -> bool:
    url = f"{config.SERVER_URL}/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=2)
            if r.ok:
                return True
        except requests.RequestException:
            pass
        time.sleep(2)
    return False


def main():
    import os

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    local_queue.init_db()

    lock = os.environ.get("TIMBRANFC_KIOSK_LOCK", "/tmp/timbranfc-kiosk.lock")
    try:
        with open(lock, "w") as f:
            f.write(str(os.getpid()))
    except OSError:
        pass

    log.info("DISPLAY=%s XAUTHORITY=%s", os.environ.get("DISPLAY"), os.environ.get("XAUTHORITY"))

    log.info("Attendo server locale %s ...", config.SERVER_URL)
    if not _attendi_server(timeout=120):
        log.error("Server non raggiungibile su %s — verifica: systemctl status timbranfc-server", config.SERVER_URL)
        sys.exit(1)

    reg = device_identity.register_device(nome_suggerito="Timbratrice locale")
    if reg:
        log.info("Dispositivo registrato id=%s", reg.get("device_id"))

    sync_agent.pull_dipendenti()
    sync_agent.avvia_sync_agent()

    try:
        ui = KioskUI()
    except Exception as e:
        log.error("Impossibile aprire interfaccia grafica: %s", e)
        log.error("Installa: sudo apt install python3-tk")
        log.error("Avvia dopo login desktop, oppure usa autostart (standalone/autostart/)")
        sys.exit(1)

    def on_badge(uid: str) -> None:
        log.info("Lettura badge: %s", uid)
        enrollment_attiva = False
        try:
            r = requests.get(f"{config.SERVER_URL}/api/v1/enrollment/active", timeout=2)
            enrollment_attiva = r.ok and r.json().get("active")
        except requests.RequestException as exc:
            log.debug("Enrollment check fallito: %s", exc)

        if enrollment_attiva:
            try:
                cap = requests.post(
                    f"{config.SERVER_URL}/api/v1/enrollment/capture",
                    json={"badge_uid": uid},
                    timeout=2,
                )
                if cap.ok:
                    data = cap.json()
                    if data.get("duplicate"):
                        ui.mostra_enrollment_msg(t("enrollment_duplicate"), uid, ok=False)
                    else:
                        ui.mostra_enrollment_msg(t("enrollment_ok"), uid, ok=True)
                    return
                log.warning("Enrollment capture fallita (%s) — timbratura normale", cap.status_code)
            except requests.RequestException as exc:
                log.warning("Enrollment capture errore: %s — timbratura normale", exc)

        ui.on_badge(uid)

    threading.Thread(target=start_nfc_loop, args=(on_badge,), daemon=True).start()
    log.info(
        "Kiosk avviato %dx%d — display SOLO timbratrice (dashboard su altri PC: http://<ip-pi>:8080)",
        config.DISPLAY_WIDTH,
        config.DISPLAY_HEIGHT,
    )
    try:
        ui.run()
    except Exception:
        log.exception("Kiosk UI terminata con errore")
        raise


if __name__ == "__main__":
    main()
