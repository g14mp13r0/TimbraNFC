"""Gestione utenti dashboard web (admin / contabile)."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash

from server.app.models import UtenteAdmin
from server.app.web_auth import ROLE_ADMIN, ROLE_CONTABILE, ROLES, normalize_ruolo


class UtenteWebError(Exception):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message
        super().__init__(message or code)


def _normalizza_email(email: str) -> str:
    return email.strip().lower()


def _count_admins(db: Session) -> int:
    n = 0
    for row in db.query(UtenteAdmin).all():
        if normalize_ruolo(row.ruolo) == ROLE_ADMIN:
            n += 1
    return n


def email_gia_usata(db: Session, email: str, escludi_id: int | None = None) -> bool:
    addr = _normalizza_email(email)
    q = db.query(UtenteAdmin).filter(func.lower(UtenteAdmin.email) == addr)
    if escludi_id is not None:
        q = q.filter(UtenteAdmin.id != escludi_id)
    return q.first() is not None


def lista_utenti(db: Session) -> list[UtenteAdmin]:
    return db.query(UtenteAdmin).order_by(UtenteAdmin.email).all()


def crea_utente(
    db: Session,
    *,
    email: str,
    password: str,
    ruolo: str,
) -> UtenteAdmin:
    addr = _normalizza_email(email)
    if not addr:
        raise UtenteWebError("email_vuota")
    if not password.strip():
        raise UtenteWebError("password_vuota")
    ruolo_norm = normalize_ruolo(ruolo)
    if ruolo_norm not in ROLES:
        raise UtenteWebError("ruolo_invalido")
    if email_gia_usata(db, addr):
        raise UtenteWebError("email_duplicato")

    user = UtenteAdmin(
        email=addr,
        password_hash=generate_password_hash(password),
        ruolo=ruolo_norm,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def aggiorna_utente(
    db: Session,
    user_id: int,
    *,
    email: str,
    password: str | None = None,
    ruolo: str,
) -> UtenteAdmin:
    user = db.query(UtenteAdmin).filter(UtenteAdmin.id == user_id).first()
    if not user:
        raise UtenteWebError("non_trovato")

    addr = _normalizza_email(email)
    if not addr:
        raise UtenteWebError("email_vuota")
    ruolo_norm = normalize_ruolo(ruolo)
    if ruolo_norm not in ROLES:
        raise UtenteWebError("ruolo_invalido")
    if email_gia_usata(db, addr, escludi_id=user_id):
        raise UtenteWebError("email_duplicato")

    era_admin = normalize_ruolo(user.ruolo) == ROLE_ADMIN
    if era_admin and ruolo_norm != ROLE_ADMIN and _count_admins(db) <= 1:
        raise UtenteWebError("ultimo_admin")

    user.email = addr
    user.ruolo = ruolo_norm
    if password is not None and password.strip():
        user.password_hash = generate_password_hash(password)
    db.commit()
    db.refresh(user)
    return user


def elimina_utente(db: Session, user_id: int, *, current_user_id: int) -> None:
    if user_id == current_user_id:
        raise UtenteWebError("se_stesso")

    user = db.query(UtenteAdmin).filter(UtenteAdmin.id == user_id).first()
    if not user:
        raise UtenteWebError("non_trovato")

    if normalize_ruolo(user.ruolo) == ROLE_ADMIN and _count_admins(db) <= 1:
        raise UtenteWebError("ultimo_admin")

    db.delete(user)
    db.commit()
