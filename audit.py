from db import get_db


def log_audit(azione: str, entita: str, entita_id: int | None = None, dettagli: str = "", utente: str = "sistema"):
    with get_db() as con:
        con.execute(
            """
            INSERT INTO audit_log (azione, entita, entita_id, dettagli, utente)
            VALUES (?, ?, ?, ?, ?)
            """,
            (azione, entita, entita_id, dettagli, utente),
        )
