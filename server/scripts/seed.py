#!/usr/bin/env python3
"""Seed dati di test per server."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import func

from server.app.config import ADMIN_EMAIL, ADMIN_PASSWORD, CONTABILE_EMAIL, CONTABILE_PASSWORD
from server.app.db import Base, SessionLocal, engine
from server.app.models import Dipendente, Sede, UtenteAdmin
from server.app.web_auth import ROLE_ADMIN, ROLE_CONTABILE
from werkzeug.security import generate_password_hash


def _ensure_user(db, email: str, password: str, ruolo: str) -> None:
    if not db.query(UtenteAdmin).filter(func.lower(UtenteAdmin.email) == email.lower()).first():
        db.add(UtenteAdmin(email=email, password_hash=generate_password_hash(password), ruolo=ruolo))


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(Sede).first():
            db.add(Sede(id=1, nome="Sede Principale", indirizzo="Via Roma 1"))
        _ensure_user(db, ADMIN_EMAIL, ADMIN_PASSWORD, ROLE_ADMIN)
        _ensure_user(db, CONTABILE_EMAIL, CONTABILE_PASSWORD, ROLE_CONTABILE)
        db.commit()
        print("Server seed OK")
    finally:
        db.close()


if __name__ == "__main__":
    main()
