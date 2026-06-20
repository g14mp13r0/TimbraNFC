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
        samples = [
            ("Mario", "Rossi", "04A1B2C3D4E5", "Produzione"),
            ("Laura", "Bianchi", "04F6E5D4C3B2", "HR"),
        ]
        for nome, cognome, uid, rep in samples:
            if not db.query(Dipendente).filter(Dipendente.badge_uid == uid).first():
                db.add(Dipendente(nome=nome, cognome=cognome, badge_uid=uid, sede_id=1, reparto=rep))
        db.commit()
        print("Server seed OK")
    finally:
        db.close()


if __name__ == "__main__":
    main()
