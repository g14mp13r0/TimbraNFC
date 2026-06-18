#!/usr/bin/env python3
"""Crea utenti di esempio: admin, hr, lettura."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from werkzeug.security import generate_password_hash

from auth import crea_utente_default
from db import get_db, init_db

UTENTI = [
    ("hr", "hr123", "hr", "Responsabile HR"),
    ("lettura", "lettura123", "lettura", "Sola Lettura"),
]


def main():
    init_db()
    crea_utente_default()
    with get_db() as con:
        cur = con.cursor()
        for username, password, ruolo, nome in UTENTI:
            cur.execute(
                """
                INSERT OR IGNORE INTO utenti (username, password_hash, ruolo, nome)
                VALUES (?, ?, ?, ?)
                """,
                (username, generate_password_hash(password), ruolo, nome),
            )
    print("Utenti: admin/admin, hr/hr123, lettura/lettura123")


if __name__ == "__main__":
    main()
