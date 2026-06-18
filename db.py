import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

import config


def init_db(db_path: Path | None = None) -> None:
    path = db_path or config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    with sqlite3.connect(path) as con:
        con.executescript(schema)
        con.commit()
    migrate_db(path)


def migrate_db(db_path: Path | None = None) -> None:
    """Aggiorna DB esistenti senza perdere dati."""
    path = db_path or config.DB_PATH
    if not path.exists():
        return

    with sqlite3.connect(path) as con:
        cur = con.cursor()

        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sedi'")
        if not cur.fetchone():
            cur.executescript("""
                CREATE TABLE sedi (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    codice TEXT UNIQUE NOT NULL,
                    indirizzo TEXT,
                    attiva INTEGER DEFAULT 1,
                    creato_il DATETIME DEFAULT (datetime('now', 'localtime'))
                );
                INSERT INTO sedi (id, nome, codice) VALUES (1, 'Sede Principale', 'PRINCIPALE');
            """)

        cur.execute("PRAGMA table_info(dipendenti)")
        cols = {row[1] for row in cur.fetchall()}
        if "sede_id" not in cols:
            cur.execute("ALTER TABLE dipendenti ADD COLUMN sede_id INTEGER REFERENCES sedi(id)")

        cur.execute("PRAGMA table_info(timbrature)")
        cols = {row[1] for row in cur.fetchall()}
        if "sede_id" not in cols:
            cur.execute("ALTER TABLE timbrature ADD COLUMN sede_id INTEGER REFERENCES sedi(id)")
            cur.execute("UPDATE timbrature SET sede_id=1 WHERE sede_id IS NULL")

        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")
        if not cur.fetchone():
            cur.executescript("""
                CREATE TABLE audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    azione TEXT NOT NULL,
                    entita TEXT NOT NULL,
                    entita_id INTEGER,
                    dettagli TEXT,
                    utente TEXT DEFAULT 'sistema',
                    timestamp DATETIME DEFAULT (datetime('now', 'localtime'))
                );
                CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
            """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_timbrature_sede ON timbrature(sede_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_dipendenti_sede ON dipendenti(sede_id)")

        cur.execute("PRAGMA table_info(timbrature)")
        cols = {row[1] for row in cur.fetchall()}
        if "sync_key" not in cols:
            cur.execute("ALTER TABLE timbrature ADD COLUMN sync_key TEXT")
            cur.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_timbrature_sync_key "
                "ON timbrature(sync_key) WHERE sync_key IS NOT NULL"
            )

        for table, sql in [
            ("utenti", """
                CREATE TABLE utenti (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    ruolo TEXT CHECK(ruolo IN ('admin', 'hr', 'lettura')) NOT NULL DEFAULT 'lettura',
                    nome TEXT NOT NULL,
                    attivo INTEGER DEFAULT 1,
                    creato_il DATETIME DEFAULT (datetime('now', 'localtime'))
                );
            """),
            ("sync_coda", """
                CREATE TABLE sync_coda (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sync_key TEXT UNIQUE NOT NULL,
                    tipo TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    tentativi INTEGER DEFAULT 0,
                    inviato_il DATETIME,
                    creato_il DATETIME DEFAULT (datetime('now', 'localtime'))
                );
            """),
            ("sync_log", """
                CREATE TABLE sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    direzione TEXT NOT NULL,
                    esito TEXT NOT NULL,
                    dettagli TEXT,
                    timestamp DATETIME DEFAULT (datetime('now', 'localtime'))
                );
            """),
            ("sync_meta", """
                CREATE TABLE sync_meta (
                    chiave TEXT PRIMARY KEY,
                    valore TEXT NOT NULL
                );
            """),
        ]:
            cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cur.fetchone():
                cur.executescript(sql)

        con.commit()


@contextmanager
def get_db(db_path: Path | None = None):
    path = db_path or config.DB_PATH
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def calcola_ore_lavorate(timbrature: list[dict]) -> float:
    totale = timedelta()
    entrata = None
    for t in timbrature:
        ts = datetime.fromisoformat(t["timestamp"])
        if t["tipo"] == "entrata":
            entrata = ts
        elif t["tipo"] == "uscita" and entrata:
            if ts > entrata:
                totale += ts - entrata
            entrata = None
    return round(totale.total_seconds() / 3600, 2)


def get_riepilogo_ore(da: str, a: str, sede_id: int | None = None, dipendente_id: int | None = None) -> list[dict]:
    query = """
        SELECT t.timestamp, t.tipo, d.id AS dipendente_id, d.nome, d.cognome
        FROM timbrature t
        JOIN dipendenti d ON d.id = t.dipendente_id
        WHERE DATE(t.timestamp) BETWEEN ? AND ?
    """
    params: list = [da, a]
    if sede_id:
        query += " AND t.sede_id=?"
        params.append(sede_id)
    if dipendente_id:
        query += " AND d.id=?"
        params.append(dipendente_id)
    query += " ORDER BY d.cognome, d.nome, t.timestamp"

    with get_db() as con:
        cur = con.cursor()
        cur.execute(query, params)
        rows = [dict(r) for r in cur.fetchall()]

    per_dip: dict[int, dict] = {}
    for r in rows:
        did = r["dipendente_id"]
        if did not in per_dip:
            per_dip[did] = {"id": did, "nome": f"{r['nome']} {r['cognome']}", "timbrature": []}
        per_dip[did]["timbrature"].append(r)

    riepilogo = []
    for info in per_dip.values():
        ore = calcola_ore_lavorate(info["timbrature"])
        riepilogo.append({"id": info["id"], "nome": info["nome"], "ore": ore})
    riepilogo.sort(key=lambda x: x["nome"])
    return riepilogo
