from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from server.app.auth import get_device_by_uuid, verify_api_key
from server.app.config import DEFAULT_SEDE_ID
from server.app.db import get_db
from server.app.models import DeviceComando, DeviceLog, Dipendente, Dispositivo, Sede
from shared.schemas import (
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    DipendentiResponse,
    HeartbeatRequest,
    HeartbeatResponse,
)

router = APIRouter(prefix="/api/v1/devices", tags=["devices"], dependencies=[Depends(verify_api_key)])


@router.post("/register", response_model=DeviceRegisterResponse)
def register_device(body: DeviceRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(Dispositivo).filter(Dispositivo.device_uuid == body.device_uuid).first()
    if existing:
        return DeviceRegisterResponse(
            device_id=existing.id, sede_id=existing.sede_id, config={"sync_interval_sec": 30}
        )

    sede = db.query(Sede).filter(Sede.id == DEFAULT_SEDE_ID).first()
    if not sede:
        sede = Sede(id=DEFAULT_SEDE_ID, nome="Sede Principale")
        db.add(sede)
        db.flush()

    dev = Dispositivo(
        sede_id=sede.id,
        nome=body.nome_suggerito,
        device_uuid=body.device_uuid,
        stato="offline",
    )
    db.add(dev)
    db.commit()
    db.refresh(dev)
    return DeviceRegisterResponse(device_id=dev.id, sede_id=dev.sede_id, config={"sync_interval_sec": 30})


@router.get("/{device_uuid}/dipendenti", response_model=DipendentiResponse)
def get_dipendenti_device(device_uuid: str, db: Session = Depends(get_db)):
    dev = get_device_by_uuid(db, device_uuid)
    rows = (
        db.query(Dipendente)
        .filter(Dipendente.sede_id == dev.sede_id, Dipendente.attivo == True)
        .all()
    )
    return DipendentiResponse(
        dipendenti=[
            {"badge_uid": d.badge_uid, "nome": d.nome, "cognome": d.cognome, "attivo": d.attivo}
            for d in rows
        ]
    )


@router.post("/{device_uuid}/heartbeat", response_model=HeartbeatResponse)
def heartbeat(device_uuid: str, body: HeartbeatRequest, db: Session = Depends(get_db)):
    dev = get_device_by_uuid(db, device_uuid)
    dev.ultimo_heartbeat = datetime.now()
    dev.versione_sw = body.versione_sw
    dev.ip_locale = body.ip_locale
    dev.stato = "online"

    pending_cmds = (
        db.query(DeviceComando)
        .filter(DeviceComando.dispositivo_id == dev.id, DeviceComando.eseguito == False)
        .order_by(DeviceComando.id)
        .limit(10)
        .all()
    )

    db.add(DeviceLog(dispositivo_id=dev.id, livello="info", messaggio=f"heartbeat pending={body.queue_pending}"))
    db.commit()

    return HeartbeatResponse(
        comandi_pendenti=[{"id": c.id, "tipo": c.tipo, "payload": None} for c in pending_cmds]
    )


@router.post("/{device_uuid}/comandi/{cmd_id}/ack")
def ack_comando(device_uuid: str, cmd_id: int, db: Session = Depends(get_db)):
    dev = get_device_by_uuid(db, device_uuid)
    cmd = (
        db.query(DeviceComando)
        .filter(DeviceComando.id == cmd_id, DeviceComando.dispositivo_id == dev.id)
        .first()
    )
    if cmd:
        cmd.eseguito = True
        db.commit()
    return {"ok": True}
