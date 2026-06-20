"""Contratti API condivisi terminale ↔ server."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Azione = Literal["IT", "IP", "FP", "FT"]
StatoDipendente = Literal["FUORI_TURNO", "IN_TURNO", "IN_PAUSA"]
EsitoSync = Literal["ok", "error"]
RuoloAdmin = Literal["admin", "hr", "readonly"]
TipoComando = Literal["restart_kiosk", "restart_device", "update_software", "run_diagnostics", "reset_config"]


class DeviceRegisterRequest(BaseModel):
    device_uuid: str
    nome_suggerito: str = "Varco"


class DeviceRegisterResponse(BaseModel):
    device_id: int
    sede_id: int
    config: dict = Field(default_factory=lambda: {"sync_interval_sec": 30})


class DipendenteCacheItem(BaseModel):
    badge_uid: str
    nome: str
    cognome: str
    attivo: bool = True


class DipendentiResponse(BaseModel):
    dipendenti: list[DipendenteCacheItem]


class TimbraturaSyncItem(BaseModel):
    id_locale: int
    badge_uid: str
    azione: Azione
    timestamp: datetime


class TimbraturaSyncRequest(BaseModel):
    device_uuid: str
    timbrature: list[TimbraturaSyncItem]


class TimbraturaSyncResult(BaseModel):
    id_locale: int
    esito: EsitoSync
    messaggio: Optional[str] = None


class TimbraturaSyncResponse(BaseModel):
    risultati: list[TimbraturaSyncResult]


class HeartbeatRequest(BaseModel):
    versione_sw: str
    queue_pending: int = 0
    ip_locale: Optional[str] = None


class ComandoPendente(BaseModel):
    id: int
    tipo: TipoComando
    payload: Optional[dict] = None


class HeartbeatResponse(BaseModel):
    comandi_pendenti: list[ComandoPendente] = Field(default_factory=list)


class StatoDipendenteResponse(BaseModel):
    badge_uid: str
    nome: str
    cognome: str
    stato: StatoDipendente
    azioni_valide: list[Azione]
