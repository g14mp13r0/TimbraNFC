from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from server.app.config import API_KEY
from server.app.db import get_db
from server.app.models import Dispositivo

_api_key = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(key: str | None = Security(_api_key)) -> str:
    if not API_KEY:
        return "dev"
    if not key or key != API_KEY:
        raise HTTPException(401, "API key non valida")
    return key


def get_device_by_uuid(db: Session, device_uuid: str) -> Dispositivo:
    dev = db.query(Dispositivo).filter(Dispositivo.device_uuid == device_uuid).first()
    if not dev:
        raise HTTPException(404, "Dispositivo non registrato")
    return dev
