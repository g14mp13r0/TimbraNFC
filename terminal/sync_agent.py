import logging
import os
import subprocess
import sys
import threading
import time
from datetime import datetime

import requests

import terminal.config as config
import terminal.device_identity as device_identity
import terminal.local_queue as local_queue

log = logging.getLogger("sync_agent")
_backoff_sec = config.SYNC_INTERVAL_SEC


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if config.API_KEY:
        h["X-API-Key"] = config.API_KEY
    return h


def pull_dipendenti() -> bool:
    device_uuid = device_identity.get_device_uuid()
    try:
        r = requests.get(
            f"{config.SERVER_URL}/api/v1/devices/{device_uuid}/dipendenti",
            headers=_headers(),
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        n = local_queue.upsert_dipendenti(data.get("dipendenti", []))
        log.info("Cache anagrafica aggiornata: %d dipendenti", n)
        return True
    except Exception as e:
        log.warning("Pull anagrafica fallito: %s", e)
        return False


def push_timbrature() -> int:
    global _backoff_sec
    pending = local_queue.get_pending()
    if not pending:
        _backoff_sec = config.SYNC_INTERVAL_SEC
        return 0

    device_uuid = device_identity.get_device_uuid()
    payload = {
        "device_uuid": device_uuid,
        "timbrature": [
            {
                "id_locale": p["id"],
                "badge_uid": p["badge_uid"],
                "azione": p["azione"],
                "timestamp": p["timestamp"],
            }
            for p in pending
        ],
    }
    try:
        r = requests.post(
            f"{config.SERVER_URL}/api/v1/timbrature/sync",
            json=payload,
            headers=_headers(),
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        ok_ids = [res["id_locale"] for res in data.get("risultati", []) if res.get("esito") == "ok"]
        for res in data.get("risultati", []):
            if res.get("esito") != "ok":
                local_queue.mark_error(res["id_locale"], res.get("messaggio", "errore server"))
        local_queue.mark_synced(ok_ids)
        log.info("Sync push: %d/%d timbrature", len(ok_ids), len(pending))
        _backoff_sec = config.SYNC_INTERVAL_SEC
        return len(ok_ids)
    except Exception as e:
        log.warning("Push timbrature fallito: %s", e)
        _backoff_sec = min(_backoff_sec * 2, 600)
        return 0


def send_heartbeat() -> list[dict]:
    device_uuid = device_identity.get_device_uuid()
    try:
        r = requests.post(
            f"{config.SERVER_URL}/api/v1/devices/{device_uuid}/heartbeat",
            json={
                "versione_sw": config.VERSIONE_SW,
                "queue_pending": local_queue.count_pending(),
                "ip_locale": _local_ip(),
            },
            headers=_headers(),
            timeout=15,
        )
        r.raise_for_status()
        comandi = r.json().get("comandi_pendenti", [])
        for cmd in comandi:
            _esegui_comando(cmd)
        return comandi
    except Exception as e:
        log.debug("Heartbeat fallito: %s", e)
        return []


def _local_ip() -> str:
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return ""


def _ack_comando(cmd_id: int | None) -> bool:
    if cmd_id is None:
        return False
    device_uuid = device_identity.get_device_uuid()
    try:
        r = requests.post(
            f"{config.SERVER_URL}/api/v1/devices/{device_uuid}/comandi/{cmd_id}/ack",
            headers=_headers(),
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        log.warning("Ack comando %s fallito: %s", cmd_id, e)
        return False


def _esegui_comando(cmd: dict) -> None:
    tipo = cmd.get("tipo")
    cmd_id = cmd.get("id")
    log.info("Comando ricevuto: %s (id=%s)", tipo, cmd_id)

    # ACK prima di azioni distruttive (execv non ritorna mai)
    if not _ack_comando(cmd_id):
        log.error("Comando %s (id=%s) non confermato — verrà ripetuto", tipo, cmd_id)
        return

    if tipo == "restart_kiosk":
        log.info("Riavvio kiosk richiesto dal server")
        if config.STANDALONE:
            script = config.ROOT / "standalone" / "restart-kiosk.sh"
            if not script.is_file():
                log.error("Script restart non trovato: %s", script)
                return
            env = os.environ.copy()
            env["APP_DIR"] = str(config.ROOT)
            subprocess.Popen(
                ["bash", str(script)],
                cwd=str(config.ROOT),
                env=env,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        os.execv(sys.executable, [sys.executable] + sys.argv)
    elif tipo == "restart_device":
        subprocess.run(["sudo", "reboot"], check=False)
    elif tipo == "run_diagnostics":
        log.info("Diagnostica: pending=%d", local_queue.count_pending())
    elif tipo == "reset_config":
        log.warning("reset_config richiede intervento manuale")
    elif tipo == "update_software":
        log.info("update_software: payload=%s", cmd.get("payload"))
    else:
        log.warning("Comando sconosciuto: %s", tipo)


def sync_loop(stop_event: threading.Event) -> None:
    global _backoff_sec
    time.sleep(5)
    last_heartbeat = time.time()

    while not stop_event.is_set():
        pull_dipendenti()
        push_timbrature()

        now = time.time()
        if now - last_heartbeat >= config.HEARTBEAT_INTERVAL_SEC:
            send_heartbeat()
            last_heartbeat = now

        stop_event.wait(_backoff_sec)


def avvia_sync_agent() -> threading.Event:
    stop = threading.Event()
    t = threading.Thread(target=sync_loop, args=(stop,), daemon=True, name="sync-agent")
    t.start()
    log.info("Sync agent avviato → %s", config.SERVER_URL)
    return stop
