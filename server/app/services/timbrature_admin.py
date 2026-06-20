"""Azzeramento timbrature — server e coda locale terminale."""

from __future__ import annotations

import sqlite3

from sqlalchemy.orm import Session

from server.app.models import Timbratura


def clear_timbrature_server(db: Session) -> int:
    n = db.query(Timbratura).delete()
    db.commit()
    return n


def clear_timbrature_locali(local_db_path) -> int:
    path = str(local_db_path)
    if not path or not __import__("pathlib").Path(path).exists():
        return 0
    with sqlite3.connect(path) as con:
        cur = con.execute("DELETE FROM timbrature_locali")
        con.commit()
        return cur.rowcount
