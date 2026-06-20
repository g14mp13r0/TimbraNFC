"""API registrazione badge NFC — dashboard avvia, kiosk cattura."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from server.app.db import get_db
from server.app.models import Dipendente
from server.app.services import enrollment as enrollment_svc

router = APIRouter(prefix="/api/v1/enrollment", tags=["enrollment"])


class CaptureBody(BaseModel):
    badge_uid: str = Field(..., min_length=4, max_length=32)


@router.post("/start")
def start_enrollment():
    session = enrollment_svc.start_session()
    return {
        "session_id": session.session_id,
        "expires_in": enrollment_svc.SESSION_TTL_SEC,
        "status": "waiting",
    }


@router.get("/poll")
def poll_enrollment(session_id: str = Query(...)):
    session = enrollment_svc.get_session(session_id)
    if session is None:
        return {"status": "invalid", "badge_uid": None}
    return {
        "status": session.status(),
        "badge_uid": session.badge_uid,
        "duplicate": session.duplicate,
        "expires_in": max(0, int(session.expires_at - __import__("time").time())),
    }


@router.get("/active")
def enrollment_active():
    return {"active": enrollment_svc.is_active()}


@router.post("/capture")
def capture_badge(body: CaptureBody, db: Session = Depends(get_db)):
    uid = body.badge_uid.strip().upper()
    duplicate = db.query(Dipendente).filter(Dipendente.badge_uid == uid).first() is not None
    if not enrollment_svc.capture_badge(uid, duplicate=duplicate):
        raise HTTPException(status_code=409, detail="Nessuna sessione di registrazione attiva")
    return {"ok": True, "badge_uid": uid, "duplicate": duplicate}


@router.post("/stop")
def stop_enrollment():
    enrollment_svc.stop_session()
    return {"ok": True}
