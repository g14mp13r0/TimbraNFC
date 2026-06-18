import logging
from datetime import datetime

import config
from audit import log_audit
from db import get_db
from sync import accoda_timbratura

log = logging.getLogger("timbratura")


def esegui_timbratura(uid: str, sede_id: int | None = None, feedback_fn=None) -> dict:
    uid = uid.strip().upper()
    sede = sede_id if sede_id is not None else config.SEDE_ID

    def _feedback(ok: bool):
        if feedback_fn:
            feedback_fn(ok)

    with get_db() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT id, nome, cognome, badge_uid FROM dipendenti WHERE badge_uid=? AND attivo=1",
            (uid,),
        )
        dip = cur.fetchone()
        if not dip:
            _feedback(False)
            result = {"ok": False, "msg": "Badge non riconosciuto", "nome": "", "tipo": "", "ora": "", "sede_id": sede}
            log_audit("timbratura_rifiutata", "badge", dettagli=f"UID sconosciuto: {uid}")
            return result

        dip_id = dip["id"]
        nome, cognome, badge_uid = dip["nome"], dip["cognome"], dip["badge_uid"]

        cur.execute(
            """
            SELECT timestamp FROM timbrature
            WHERE dipendente_id=?
            ORDER BY timestamp DESC LIMIT 1
            """,
            (dip_id,),
        )
        ultima = cur.fetchone()
        if ultima:
            diff = datetime.now() - datetime.fromisoformat(ultima["timestamp"])
            if diff.total_seconds() < config.MIN_SECONDI_DOPPIA_TIMBRATURA:
                _feedback(False)
                result = {
                    "ok": False,
                    "msg": "Timbratura già registrata",
                    "nome": f"{nome} {cognome}",
                    "tipo": "",
                    "ora": "",
                    "sede_id": sede,
                }
                return result

        cur.execute(
            """
            SELECT tipo FROM timbrature
            WHERE dipendente_id=? AND DATE(timestamp)=DATE('now', 'localtime')
            ORDER BY timestamp DESC LIMIT 1
            """,
            (dip_id,),
        )
        ultima_oggi = cur.fetchone()
        tipo = "uscita" if ultima_oggi and ultima_oggi["tipo"] == "entrata" else "entrata"

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "INSERT INTO timbrature (dipendente_id, sede_id, tipo, timestamp) VALUES (?, ?, ?, ?)",
            (dip_id, sede, tipo, now),
        )
        timbratura_id = cur.lastrowid

    ora = datetime.now().strftime("%H:%M")
    _feedback(True)
    result = {
        "ok": True,
        "nome": f"{nome} {cognome}",
        "tipo": tipo,
        "ora": ora,
        "msg": "",
        "sede_id": sede,
        "timbratura_id": timbratura_id,
    }
    log_audit(
        "timbratura",
        "timbrature",
        entita_id=timbratura_id,
        dettagli=f"{nome} {cognome} — {tipo} — sede {sede}",
    )
    log.info("Timbratura: %s — %s alle %s (sede %s)", result["nome"], tipo, ora, sede)
    accoda_timbratura(timbratura_id, badge_uid, tipo, now, sede)
    return result
