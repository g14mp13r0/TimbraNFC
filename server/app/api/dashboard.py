from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session

from server.app.db import get_db
from server.app.models import DeviceComando, Dipendente, Dispositivo, Sede, Timbratura, UtenteAdmin
from server.app.services.stati import calcola_ore_lavorate, stato_dipendente_oggi

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/dipendenti")
def lista_dipendenti(db: Session = Depends(get_db)):
    oggi = datetime.now().date()
    start = datetime.combine(oggi, datetime.min.time())
    result = []
    for d in db.query(Dipendente).filter(Dipendente.attivo == True).order_by(Dipendente.cognome).all():
        rows = (
            db.query(Timbratura)
            .filter(Timbratura.dipendente_id == d.id, Timbratura.timestamp_terminale >= start)
            .order_by(Timbratura.timestamp_terminale)
            .all()
        )
        azioni = [r.azione for r in rows]
        result.append(
            {
                "id": d.id,
                "nome": d.nome,
                "cognome": d.cognome,
                "badge_uid": d.badge_uid,
                "stato": stato_dipendente_oggi(azioni),
                "reparto": d.reparto,
            }
        )
    return result


@router.get("/dispositivi")
def lista_dispositivi(db: Session = Depends(get_db)):
    now = datetime.now()
    out = []
    for d in db.query(Dispositivo).all():
        online = d.ultimo_heartbeat and (now - d.ultimo_heartbeat) < timedelta(minutes=3)
        out.append(
            {
                "id": d.id,
                "nome": d.nome,
                "device_uuid": d.device_uuid,
                "stato": "online" if online else d.stato,
                "versione_sw": d.versione_sw,
                "ultimo_heartbeat": d.ultimo_heartbeat.isoformat() if d.ultimo_heartbeat else None,
                "ip_locale": d.ip_locale,
            }
        )
    return out


@router.post("/dispositivi/{device_id}/comandi")
def invia_comando(device_id: int, tipo: str = Query(...), db: Session = Depends(get_db)):
    dev = db.query(Dispositivo).filter(Dispositivo.id == device_id).first()
    if not dev:
        raise HTTPException(404)
    cmd = DeviceComando(dispositivo_id=device_id, tipo=tipo)
    db.add(cmd)
    db.commit()
    return {"ok": True, "comando_id": cmd.id}


@router.get("/report")
def report(
    da: str = Query(...),
    a: str = Query(...),
    dipendente_id: int | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Timbratura).filter(
        Timbratura.timestamp_terminale >= datetime.fromisoformat(da),
        Timbratura.timestamp_terminale <= datetime.fromisoformat(a + "T23:59:59"),
    )
    if dipendente_id:
        q = q.filter(Timbratura.dipendente_id == dipendente_id)
    rows = q.order_by(Timbratura.timestamp_terminale).all()

    per_dip: dict[int, list] = {}
    for r in rows:
        per_dip.setdefault(r.dipendente_id, []).append(
            {"azione": r.azione, "timestamp": r.timestamp_terminale}
        )

    riepilogo = []
    for did, timbs in per_dip.items():
        dip = db.query(Dipendente).get(did)
        if dip:
            riepilogo.append(
                {
                    "id": did,
                    "nome": f"{dip.nome} {dip.cognome}",
                    "ore": calcola_ore_lavorate(timbs),
                }
            )
    return {"riepilogo": riepilogo, "timbrature": len(rows)}


@router.post("/dipendenti")
def crea_dipendente(
    nome: str,
    cognome: str,
    badge_uid: str,
    sede_id: int = 1,
    reparto: str | None = None,
    db: Session = Depends(get_db),
):
    dip = Dipendente(
        nome=nome, cognome=cognome, badge_uid=badge_uid.upper(), sede_id=sede_id, reparto=reparto
    )
    db.add(dip)
    db.commit()
    return {"id": dip.id}
