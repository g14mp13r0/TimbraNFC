"""Operazioni sui terminali registrati."""

from __future__ import annotations

from sqlalchemy.orm import Session

from server.app.models import Dispositivo


class DispositivoError(Exception):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message
        super().__init__(message or code)


def aggiorna_nome(db: Session, device_id: int, nome: str) -> Dispositivo:
    dev = db.query(Dispositivo).filter(Dispositivo.id == device_id).first()
    if not dev:
        raise DispositivoError("non_trovato")

    label = nome.strip()
    if not label:
        raise DispositivoError("nome_vuoto")

    dev.nome = label[:100]
    db.commit()
    db.refresh(dev)
    return dev
