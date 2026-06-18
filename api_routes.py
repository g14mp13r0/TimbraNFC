from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api_auth import verify_api_key
from audit import log_audit
from db import get_db, get_riepilogo_ore
from timbratura import esegui_timbratura

from sync import get_anagrafiche_per_pull, ricevi_push

router = APIRouter(prefix="/api/v1", tags=["API v1"], dependencies=[Depends(verify_api_key)])


class DipendenteCreate(BaseModel):
    nome: str
    cognome: str
    badge_uid: str
    email: Optional[str] = None
    reparto: Optional[str] = None
    sede_id: Optional[int] = None


class SedeCreate(BaseModel):
    nome: str
    codice: str
    indirizzo: Optional[str] = None


@router.get("/health")
def api_health():
    return {"status": "ok", "version": "1.0"}


@router.get("/sedi")
def lista_sedi():
    with get_db() as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM sedi ORDER BY nome")
        return [dict(r) for r in cur.fetchall()]


@router.post("/sedi", status_code=201)
def crea_sede(sede: SedeCreate):
    with get_db() as con:
        cur = con.cursor()
        try:
            cur.execute(
                "INSERT INTO sedi (nome, codice, indirizzo) VALUES (?, ?, ?)",
                (sede.nome, sede.codice.upper(), sede.indirizzo),
            )
            sede_id = cur.lastrowid
        except Exception:
            raise HTTPException(status_code=400, detail="Codice sede già esistente")
    log_audit("creazione", "sedi", sede_id, f"{sede.nome} ({sede.codice})", utente="api")
    return {"id": sede_id, **sede.model_dump()}


@router.get("/dipendenti")
def lista_dipendenti(attivo: Optional[bool] = None, sede_id: Optional[int] = None):
    query = "SELECT d.*, s.nome AS sede_nome FROM dipendenti d LEFT JOIN sedi s ON s.id=d.sede_id WHERE 1=1"
    params: list = []
    if attivo is not None:
        query += " AND d.attivo=?"
        params.append(1 if attivo else 0)
    if sede_id:
        query += " AND d.sede_id=?"
        params.append(sede_id)
    query += " ORDER BY d.cognome, d.nome"
    with get_db() as con:
        cur = con.cursor()
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]


@router.get("/dipendenti/{dip_id}")
def get_dipendente(dip_id: int):
    with get_db() as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT d.*, s.nome AS sede_nome FROM dipendenti d
            LEFT JOIN sedi s ON s.id=d.sede_id WHERE d.id=?
            """,
            (dip_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Dipendente non trovato")
        return dict(row)


@router.post("/dipendenti", status_code=201)
def crea_dipendente(dip: DipendenteCreate):
    with get_db() as con:
        cur = con.cursor()
        try:
            cur.execute(
                """
                INSERT INTO dipendenti (nome, cognome, badge_uid, email, reparto, sede_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    dip.nome.strip(),
                    dip.cognome.strip(),
                    dip.badge_uid.strip().upper(),
                    dip.email,
                    dip.reparto,
                    dip.sede_id,
                ),
            )
            dip_id = cur.lastrowid
        except Exception:
            raise HTTPException(status_code=400, detail="Badge UID già registrato")
    log_audit("creazione", "dipendenti", dip_id, f"{dip.nome} {dip.cognome}", utente="api")
    return {"id": dip_id, **dip.model_dump()}


@router.get("/timbrature")
def lista_timbrature(
    da: str = Query(default_factory=lambda: date.today().replace(day=1).isoformat()),
    a: str = Query(default_factory=lambda: date.today().isoformat()),
    dipendente_id: Optional[int] = None,
    sede_id: Optional[int] = None,
    limit: int = Query(default=500, le=5000),
):
    query = """
        SELECT t.*, d.nome, d.cognome, d.badge_uid, s.nome AS sede_nome
        FROM timbrature t
        JOIN dipendenti d ON d.id = t.dipendente_id
        LEFT JOIN sedi s ON s.id = t.sede_id
        WHERE DATE(t.timestamp) BETWEEN ? AND ?
    """
    params: list = [da, a]
    if dipendente_id:
        query += " AND t.dipendente_id=?"
        params.append(dipendente_id)
    if sede_id:
        query += " AND t.sede_id=?"
        params.append(sede_id)
    query += " ORDER BY t.timestamp DESC LIMIT ?"
    params.append(limit)

    with get_db() as con:
        cur = con.cursor()
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]


@router.get("/report/ore")
def report_ore(
    da: str = Query(default_factory=lambda: date.today().replace(day=1).isoformat()),
    a: str = Query(default_factory=lambda: date.today().isoformat()),
    sede_id: Optional[int] = None,
    dipendente_id: Optional[int] = None,
):
    return {
        "periodo": {"da": da, "a": a},
        "riepilogo": get_riepilogo_ore(da, a, sede_id, dipendente_id),
    }


@router.post("/timbra/{uid}")
def timbra_api(uid: str, sede_id: Optional[int] = None):
    return esegui_timbratura(uid, sede_id=sede_id)


@router.get("/audit")
def audit_log(limit: int = Query(default=100, le=1000)):
    with get_db() as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]


class SyncPushBody(BaseModel):
    device_id: str
    timbrature: list[dict]


@router.post("/sync/push")
def sync_push(body: SyncPushBody):
    return ricevi_push(body.device_id, body.timbrature)


@router.get("/sync/pull")
def sync_pull(since: str = "1970-01-01 00:00:00"):
    return get_anagrafiche_per_pull(since)
