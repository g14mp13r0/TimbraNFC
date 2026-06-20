"""Operazioni anagrafica dipendenti."""

from __future__ import annotations

from sqlalchemy.orm import Session

from server.app.models import Dipendente, Timbratura


class DipendenteError(Exception):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message
        super().__init__(message or code)


def _normalizza_badge(badge_uid: str) -> str:
    return badge_uid.strip().upper()


def badge_gia_usato(db: Session, badge_uid: str, escludi_id: int | None = None) -> bool:
    uid = _normalizza_badge(badge_uid)
    q = db.query(Dipendente).filter(Dipendente.badge_uid == uid)
    if escludi_id is not None:
        q = q.filter(Dipendente.id != escludi_id)
    return q.first() is not None


def crea_dipendente(
    db: Session,
    *,
    nome: str,
    cognome: str,
    badge_uid: str,
    reparto: str | None = None,
    email: str | None = None,
    sede_id: int = 1,
) -> Dipendente:
    uid = _normalizza_badge(badge_uid)
    if not uid:
        raise DipendenteError("badge_vuoto")
    if badge_gia_usato(db, uid):
        raise DipendenteError("badge_duplicato")

    dip = Dipendente(
        nome=nome.strip(),
        cognome=cognome.strip(),
        badge_uid=uid,
        sede_id=sede_id,
        reparto=reparto.strip() if reparto else None,
        email=email.strip() if email else None,
    )
    db.add(dip)
    db.commit()
    db.refresh(dip)
    return dip


def aggiorna_dipendente(
    db: Session,
    dip_id: int,
    *,
    nome: str,
    cognome: str,
    reparto: str | None = None,
    email: str | None = None,
) -> Dipendente:
    dip = db.query(Dipendente).filter(Dipendente.id == dip_id).first()
    if not dip:
        raise DipendenteError("non_trovato")

    dip.nome = nome.strip()
    dip.cognome = cognome.strip()
    dip.reparto = reparto.strip() if reparto else None
    dip.email = email.strip() if email else None
    db.commit()
    db.refresh(dip)
    return dip


def riassegna_badge(db: Session, dip_id: int, badge_uid: str) -> Dipendente:
    dip = db.query(Dipendente).filter(Dipendente.id == dip_id).first()
    if not dip:
        raise DipendenteError("non_trovato")

    uid = _normalizza_badge(badge_uid)
    if not uid:
        raise DipendenteError("badge_vuoto")
    if badge_gia_usato(db, uid, escludi_id=dip_id):
        raise DipendenteError("badge_duplicato")

    dip.badge_uid = uid
    db.commit()
    db.refresh(dip)
    return dip


def toggle_attivo(db: Session, dip_id: int) -> Dipendente:
    dip = db.query(Dipendente).filter(Dipendente.id == dip_id).first()
    if not dip:
        raise DipendenteError("non_trovato")
    dip.attivo = not dip.attivo
    db.commit()
    db.refresh(dip)
    return dip


def elimina_dipendente(db: Session, dip_id: int) -> str:
    """Elimina o disattiva se esistono timbrature. Restituisce esito: eliminato | disattivato."""
    dip = db.query(Dipendente).filter(Dipendente.id == dip_id).first()
    if not dip:
        raise DipendenteError("non_trovato")

    ha_timbrature = db.query(Timbratura).filter(Timbratura.dipendente_id == dip_id).first() is not None
    if ha_timbrature:
        dip.attivo = False
        db.commit()
    return "disattivato_per_timbrature"

    db.delete(dip)
    db.commit()
    return "eliminato"
