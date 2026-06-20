#!/usr/bin/env python3
"""Entry point terminale TimbraNFC."""

import logging
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import terminal.config as config
import terminal.device_identity as device_identity
import terminal.local_queue as local_queue
import terminal.sync_agent as sync_agent
from terminal.kiosk_ui import KioskUI
from terminal.nfc_reader import start_nfc_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("terminal")


def main():
    local_queue.init_db()
    reg = device_identity.register_device()
    if reg:
        log.info("Device registrato: id=%s sede=%s", reg.get("device_id"), reg.get("sede_id"))
    else:
        log.warning("Registrazione server non riuscita — modalità offline")

    sync_agent.avvia_sync_agent()

    ui = KioskUI()
    threading.Thread(target=start_nfc_loop, args=(ui.on_badge,), daemon=True).start()
    log.info("Terminale avviato %dx%d → %s", config.DISPLAY_WIDTH, config.DISPLAY_HEIGHT, config.SERVER_URL)
    ui.run()


if __name__ == "__main__":
    main()
