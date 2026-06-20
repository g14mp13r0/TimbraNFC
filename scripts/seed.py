#!/usr/bin/env python3
"""Inserisce sedi e dipendenti di esempio per test."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import get_db, init_db

SEDI = [
    (2, "Magazzino Nord", "MAGAZZINO", "Via Industria 12"),
    (3, "Ufficio Roma", "ROMA", "Via del Corso 100"),
]

SAMPLE = [
    ("Giuseppe", "Verdi", "041122334455", None, "Magazzino", 2),
]


def main():
    init_db()
    with get_db() as con:
        cur = con.cursor()
        for sid, nome, codice, indirizzo in SEDI:
            cur.execute(
                "INSERT OR IGNORE INTO sedi (id, nome, codice, indirizzo) VALUES (?, ?, ?, ?)",
                (sid, nome, codice, indirizzo),
            )
        for nome, cognome, uid, email, reparto, sede_id in SAMPLE:
            cur.execute(
                """
                INSERT OR IGNORE INTO dipendenti (nome, cognome, badge_uid, email, reparto, sede_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (nome, cognome, uid, email, reparto, sede_id),
            )
    print("Dati di esempio inseriti (3 sedi, 3 dipendenti).")


if __name__ == "__main__":
    main()
