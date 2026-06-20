from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from server.app.auth import get_device_by_uuid, verify_api_key
from server.app.db import get_db
from server.app.models import Dipendente, Dispositivo, Timbratura
from server.app.services.stati import azioni_valide_per_badge, stato_dipendente_oggi
from shared.schemas import StatoDipendenteResponse, TimbraturaSyncRequest, TimbraturaSyncResponse, TimbraturaSyncResult

router = APIRouter(prefix="/api/v1", tags=["timbrature"], dependencies=[Depends(verify_api_key)])


@router.post("/timbrature/sync", response_model=TimbraturaSyncResponse)
def sync_timbrature(body: TimbraturaSyncRequest, db: Session = Depends(get_db)):
    dev = get_device_by_uuid(db, body.device_uuid)
    risultati: list[TimbraturaSyncResult] = []

    for item in body.timbrature:
        existing = (
            db.query(Timbratura)
            .filter(Timbratura.dispositivo_id == dev.id, Timbratura.id_locale_origine == item.id_locale)
            .first()
        )
        if existing:
            risultati.append(TimbraturaSyncResult(id_locale=item.id_locale, esito="ok"))
            continue

        dip = db.query(Dipendente).filter(Dipendente.badge_uid == item.badge_uid.upper()).first()
        if not dip:
            risultati.append(
                TimbraturaSyncResult(id_locale=item.id_locale, esito="error", messaggio="Badge sconosciuto")
            )
            continue

        ts = item.timestamp if isinstance(item.timestamp, datetime) else datetime.fromisoformat(str(item.timestamp))
        t = Timbratura(
            dipendente_id=dip.id,
            dispositivo_id=dev.id,
            azione=item.azione,
            timestamp_terminale=ts,
            id_locale_origine=item.id_locale,
        )
        db.add(t)
        db.flush()
        risultati.append(TimbraturaSyncResult(id_locale=item.id_locale, esito="ok"))

    db.commit()
    return TimbraturaSyncResponse(risultati=risultati)


@router.get("/stato/{badge_uid}", response_model=StatoDipendenteResponse)
def stato_badge(badge_uid: str, db: Session = Depends(get_db)):
    dip = db.query(Dipendente).filter(Dipendente.badge_uid == badge_uid.upper()).first()
    if not dip:
        from fastapi import HTTPException
        raise HTTPException(404, "Badge non riconosciuto")

    oggi = datetime.now().date()
    rows = (
        db.query(Timbratura)
        .filter(
            Timbratura.dipendente_id == dip.id,
            Timbratura.timestamp_terminale >= datetime.combine(oggi, datetime.min.time()),
        )
        .order_by(Timbratura.timestamp_terminale)
        .all()
    )
    azioni = [r.azione for r in rows]
    stato = stato_dipendente_oggi(azioni)
    return StatoDipendenteResponse(
        badge_uid=dip.badge_uid,
        nome=dip.nome,
        cognome=dip.cognome,
        stato=stato,
        azioni_valide=azioni_valide_per_badge(azioni),
    )
