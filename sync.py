import json
import logging
import threading
import time
from datetime import datetime

import requests

import config
from audit import log_audit
from db import get_db

log = logging.getLogger("sync")


def sync_attivo() -> bool:
    return bool(config.SYNC_URL) and not config.IS_HUB


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if config.API_KEY:
        h["X-API-Key"] = config.API_KEY
    return h


def accoda_timbratura(timbratura_id: int, badge_uid: str, tipo: str, timestamp: str, sede_id: int) -> None:
    if config.IS_HUB or not config.SYNC_URL:
        return

    sync_key = f"{config.DEVICE_ID}:t:{timbratura_id}"
    payload = {
        "sync_key": sync_key,
        "device_id": config.DEVICE_ID,
        "badge_uid": badge_uid,
        "tipo": tipo,
        "timestamp": timestamp,
        "sede_id": sede_id,
    }
    with get_db() as con:
        con.execute(
            """
            INSERT OR IGNORE INTO sync_coda (sync_key, tipo, payload)
            VALUES (?, 'timbratura', ?)
            """,
            (sync_key, json.dumps(payload)),
        )


def invia_coda() -> dict:
    """Invia record in coda verso l'hub."""
    if not sync_attivo():
        return {"ok": True, "inviati": 0, "msg": "sync disattivato"}

    with get_db() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT id, sync_key, payload FROM sync_coda WHERE inviato_il IS NULL ORDER BY id LIMIT 50"
        )
        pending = [dict(r) for r in cur.fetchall()]

    if not pending:
        return {"ok": True, "inviati": 0}

    timbrature = [json.loads(r["payload"]) for r in pending]
    try:
        r = requests.post(
            f"{config.SYNC_URL}/api/v1/sync/push",
            json={"device_id": config.DEVICE_ID, "timbrature": timbrature},
            headers=_headers(),
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning("Sync push fallito: %s", e)
        _log_sync("push", "errore", str(e))
        with get_db() as con:
            for item in pending:
                con.execute(
                    "UPDATE sync_coda SET tentativi = tentativi + 1 WHERE id=?",
                    (item["id"],),
                )
        return {"ok": False, "msg": str(e)}

    accettate = set(data.get("accettate", []))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as con:
        for item in pending:
            if item["sync_key"] in accettate:
                con.execute(
                    "UPDATE sync_coda SET inviato_il=? WHERE id=?",
                    (now, item["id"]),
                )

    msg = f"{len(accettate)}/{len(pending)} timbrature sincronizzate"
    _log_sync("push", "ok", msg)
    log.info("Sync push: %s", msg)
    return {"ok": True, "inviati": len(accettate), "msg": msg}


def scarica_anagrafiche() -> dict:
    """Scarica dipendenti e sedi dall'hub (hub = fonte verità anagrafica)."""
    if not sync_attivo():
        return {"ok": True, "msg": "sync disattivato"}

    since = _ultimo_pull()
    try:
        r = requests.get(
            f"{config.SYNC_URL}/api/v1/sync/pull",
            params={"since": since},
            headers=_headers(),
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning("Sync pull fallito: %s", e)
        _log_sync("pull", "errore", str(e))
        return {"ok": False, "msg": str(e)}

    n_sedi = _merge_sedi(data.get("sedi", []))
    n_dip = _merge_dipendenti(data.get("dipendenti", []))
    _salva_ultimo_pull()
    msg = f"pull: {n_sedi} sedi, {n_dip} dipendenti"
    _log_sync("pull", "ok", msg)
    log.info("Sync %s", msg)
    return {"ok": True, "sedi": n_sedi, "dipendenti": n_dip, "msg": msg}


def ricevi_push(device_id: str, timbrature: list[dict]) -> dict:
    """Hub: riceve timbrature da un terminale remoto."""
    accettate = []
    with get_db() as con:
        cur = con.cursor()
        for t in timbrature:
            sync_key = t.get("sync_key")
            if not sync_key:
                continue
            cur.execute("SELECT id FROM timbrature WHERE sync_key=?", (sync_key,))
            if cur.fetchone():
                accettate.append(sync_key)
                continue

            cur.execute(
                "SELECT id FROM dipendenti WHERE badge_uid=? AND attivo=1",
                (t["badge_uid"],),
            )
            dip = cur.fetchone()
            if not dip:
                log.warning("Sync: badge %s sconosciuto su hub", t["badge_uid"])
                continue

            cur.execute(
                """
                INSERT INTO timbrature (dipendente_id, sede_id, tipo, timestamp, sync_key)
                VALUES (?, ?, ?, ?, ?)
                """,
                (dip["id"], t.get("sede_id"), t["tipo"], t["timestamp"], sync_key),
            )
            accettate.append(sync_key)

    log_audit("sync_push", "timbrature", dettagli=f"{device_id}: {len(accettate)} record", utente=device_id)
    return {"ok": True, "accettate": accettate}


def get_anagrafiche_per_pull(since: str) -> dict:
    """Hub: restituisce sedi e dipendenti aggiornati."""
    with get_db() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT * FROM sedi WHERE attiva=1 AND creato_il >= ? OR id IN (SELECT sede_id FROM dipendenti WHERE creato_il >= ?)",
            (since, since),
        )
        sedi = [dict(r) for r in cur.fetchall()]
        if not sedi:
            cur.execute("SELECT * FROM sedi WHERE attiva=1")
            sedi = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT id, nome, cognome, badge_uid, email, reparto, sede_id, attivo, creato_il
            FROM dipendenti WHERE creato_il >= ? OR attivo=1
            """,
            (since,),
        )
        dipendenti = [dict(r) for r in cur.fetchall()]

    return {"sedi": sedi, "dipendenti": dipendenti, "since": since}


def stato_sync() -> dict:
    with get_db() as con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) AS n FROM sync_coda WHERE inviato_il IS NULL")
        in_coda = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) AS n FROM sync_coda WHERE inviato_il IS NOT NULL")
        inviati = cur.fetchone()["n"]
        cur.execute("SELECT * FROM sync_log ORDER BY timestamp DESC LIMIT 10")
        log_recenti = [dict(r) for r in cur.fetchall()]
    return {
        "attivo": sync_attivo(),
        "is_hub": config.IS_HUB,
        "device_id": config.DEVICE_ID,
        "sync_url": config.SYNC_URL,
        "in_coda": in_coda,
        "inviati": inviati,
        "log": log_recenti,
    }


def esegui_sync_completa() -> dict:
    pull = scarica_anagrafiche()
    push = invia_coda()
    return {"pull": pull, "push": push}


def avvia_loop_sync() -> None:
    if config.IS_HUB or not config.SYNC_URL:
        return

    def _loop():
        time.sleep(10)
        while True:
            try:
                scarica_anagrafiche()
                invia_coda()
            except Exception as e:
                log.error("Errore loop sync: %s", e)
            time.sleep(config.SYNC_INTERVAL)

    threading.Thread(target=_loop, daemon=True, name="sync-loop").start()
    log.info("Loop sync avviato → %s ogni %ss", config.SYNC_URL, config.SYNC_INTERVAL)


def _merge_sedi(sedi: list[dict]) -> int:
    n = 0
    with get_db() as con:
        cur = con.cursor()
        for s in sedi:
            cur.execute("SELECT id FROM sedi WHERE codice=?", (s["codice"],))
            if cur.fetchone():
                cur.execute(
                    "UPDATE sedi SET nome=?, indirizzo=?, attiva=? WHERE codice=?",
                    (s["nome"], s.get("indirizzo"), s.get("attivo", 1), s["codice"]),
                )
            else:
                cur.execute(
                    "INSERT INTO sedi (id, nome, codice, indirizzo, attiva) VALUES (?, ?, ?, ?, ?)",
                    (s["id"], s["nome"], s["codice"], s.get("indirizzo"), s.get("attivo", 1)),
                )
            n += 1
    return n


def _merge_dipendenti(dipendenti: list[dict]) -> int:
    n = 0
    with get_db() as con:
        cur = con.cursor()
        for d in dipendenti:
            cur.execute("SELECT id FROM dipendenti WHERE badge_uid=?", (d["badge_uid"],))
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    """
                    UPDATE dipendenti SET nome=?, cognome=?, email=?, reparto=?, sede_id=?, attivo=?
                    WHERE badge_uid=?
                    """,
                    (d["nome"], d["cognome"], d.get("email"), d.get("reparto"), d.get("sede_id"), d.get("attivo", 1), d["badge_uid"]),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO dipendenti (nome, cognome, badge_uid, email, reparto, sede_id, attivo)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (d["nome"], d["cognome"], d["badge_uid"], d.get("email"), d.get("reparto"), d.get("sede_id"), d.get("attivo", 1)),
                )
            n += 1
    return n


def _ultimo_pull() -> str:
    with get_db() as con:
        cur = con.cursor()
        cur.execute("SELECT valore FROM sync_meta WHERE chiave='ultimo_pull'")
        row = cur.fetchone()
        return row["valore"] if row else "1970-01-01 00:00:00"


def _salva_ultimo_pull() -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as con:
        con.execute(
            "INSERT OR REPLACE INTO sync_meta (chiave, valore) VALUES ('ultimo_pull', ?)",
            (now,),
        )


def _log_sync(direzione: str, esito: str, dettagli: str) -> None:
    with get_db() as con:
        con.execute(
            "INSERT INTO sync_log (direzione, esito, dettagli) VALUES (?, ?, ?)",
            (direzione, esito, dettagli),
        )
