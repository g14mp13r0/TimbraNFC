#!/usr/bin/env python3
"""Seed dati di test per server."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from server.app.db import Base, SessionLocal, engine
from server.app.models import Dipendente, Sede, UtenteAdmin
from werkzeug.security import generate_password_hash


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(Sede).first():
            db.add(Sede(id=1, nome="Sede Principale", indirizzo="Via Roma 1"))
        if not db.query(UtenteAdmin).first():
            db.add(UtenteAdmin(email="admin@local", password_hash=generate_password_hash("admin"), ruolo="admin"))
        db.commit()
        print("Server seed OK")
    finally:
        db.close()


if __name__ == "__main__":
    main()
