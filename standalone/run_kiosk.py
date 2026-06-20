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
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    local_queue.init_db()

    log.info("Attendo server locale %s ...", config.SERVER_URL)
    if not _attendi_server():
        log.error("Server non raggiungibile — avviare timbranfc-server.service prima del kiosk")
        sys.exit(1)

    reg = device_identity.register_device(nome_suggerito="Timbratrice locale")
    if reg:
        log.info("Dispositivo registrato id=%s", reg.get("device_id"))

    sync_agent.pull_dipendenti()
    sync_agent.avvia_sync_agent()

    ui = KioskUI()
    threading.Thread(target=start_nfc_loop, args=(ui.on_badge,), daemon=True).start()
    log.info(
        "Kiosk avviato %dx%d — display SOLO timbratrice (dashboard su altri PC: http://<ip-pi>:8080)",
        config.DISPLAY_WIDTH,
        config.DISPLAY_HEIGHT,
    )
    ui.run()


if __name__ == "__main__":
    main()
