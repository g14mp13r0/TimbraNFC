import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

import terminal.config as config

SCHEMA = """
CREATE TABLE IF NOT EXISTS timbrature_locali (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    badge_uid TEXT NOT NULL,
    azione TEXT NOT NULL CHECK(azione IN ('IT','IP','FP','FT')),
    timestamp TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    stato_sync TEXT NOT NULL DEFAULT 'pending' CHECK(stato_sync IN ('pending','synced','error')),
    sync_tentativi INTEGER NOT NULL DEFAULT 0,
    sync_ultimo_errore TEXT,
    synced_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_locali_stato_sync ON timbrature_locali(stato_sync);
CREATE INDEX IF NOT EXISTS idx_locali_badge_data ON timbrature_locali(badge_uid, timestamp);

CREATE TABLE IF NOT EXISTS dipendenti_cache (
    badge_uid TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    cognome TEXT NOT NULL,
    attivo INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);
"""


def init_db() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(config.LOCAL_DB_PATH) as con:
        con.executescript(SCHEMA)
        con.commit()


@contextmanager
def get_db():
    con = sqlite3.connect(config.LOCAL_DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def get_dipendente(badge_uid: str) -> dict | None:
    with get_db() as con:
        row = con.execute(
            "SELECT * FROM dipendenti_cache WHERE badge_uid=? AND attivo=1",
            (badge_uid.upper(),),
        ).fetchone()
        return dict(row) if row else None


def remove_dipendente(badge_uid: str) -> bool:
    uid = badge_uid.strip().upper()
    with get_db() as con:
        cur = con.execute("DELETE FROM dipendenti_cache WHERE badge_uid=?", (uid,))
        return cur.rowcount > 0


def upsert_dipendenti(dipendenti: list[dict]) -> int:
    """Sincronizza la cache locale con l'elenco server (rimuove badge eliminati/disattivati)."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    badges_server = [d["badge_uid"].upper() for d in dipendenti]
    n = 0
    with get_db() as con:
        if badges_server:
            placeholders = ",".join("?" * len(badges_server))
            con.execute(
                f"DELETE FROM dipendenti_cache WHERE badge_uid NOT IN ({placeholders})",
                badges_server,
            )
        else:
            con.execute("DELETE FROM dipendenti_cache")

        for d in dipendenti:
            con.execute(
                """
                INSERT INTO dipendenti_cache (badge_uid, nome, cognome, attivo, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(badge_uid) DO UPDATE SET
                    nome=excluded.nome, cognome=excluded.cognome,
                    attivo=excluded.attivo, updated_at=excluded.updated_at
                """,
                (d["badge_uid"].upper(), d["nome"], d["cognome"], 1 if d.get("attivo", True) else 0, now),
            )
            n += 1
    return n


def enqueue_timbratura(badge_uid: str, azione: str) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as con:
        cur = con.execute(
            """
            INSERT INTO timbrature_locali (badge_uid, azione, timestamp, stato_sync)
            VALUES (?, ?, ?, 'pending')
            """,
            (badge_uid.upper(), azione, now),
        )
        return cur.lastrowid


def get_azioni_oggi(badge_uid: str) -> list[str]:
    oggi = date.today().isoformat()
    with get_db() as con:
        rows = con.execute(
            """
            SELECT azione FROM timbrature_locali
            WHERE badge_uid=? AND date(timestamp)=?
            ORDER BY timestamp, id
            """,
            (badge_uid.upper(), oggi),
        ).fetchall()
    return [r["azione"] for r in rows]


def ultima_timbratura(badge_uid: str) -> dict | None:
    with get_db() as con:
        row = con.execute(
            "SELECT * FROM timbrature_locali WHERE badge_uid=? ORDER BY timestamp DESC, id DESC LIMIT 1",
            (badge_uid.upper(),),
        ).fetchone()
        return dict(row) if row else None


def get_pending(limit: int = 50) -> list[dict]:
    with get_db() as con:
        rows = con.execute(
            """
            SELECT * FROM timbrature_locali
            WHERE stato_sync='pending' OR (stato_sync='error' AND sync_tentativi < 10)
            ORDER BY id LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_synced(ids_ok: list[int]) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as con:
        for lid in ids_ok:
            con.execute(
                "UPDATE timbrature_locali SET stato_sync='synced', synced_at=? WHERE id=?",
                (now, lid),
            )


def mark_error(id_locale: int, errore: str) -> None:
    with get_db() as con:
        con.execute(
            """
            UPDATE timbrature_locali
            SET stato_sync='error', sync_tentativi=sync_tentativi+1, sync_ultimo_errore=?
            WHERE id=?
            """,
            (errore[:500], id_locale),
        )


def count_pending() -> int:
    with get_db() as con:
        return con.execute(
            "SELECT COUNT(*) AS n FROM timbrature_locali WHERE stato_sync IN ('pending','error')"
        ).fetchone()["n"]
