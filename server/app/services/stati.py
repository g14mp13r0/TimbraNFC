import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.schemas import Azione, StatoDipendente
from terminal.stati import STATO_DA_AZIONE, azioni_valide, stato_da_timbrature


def stato_dipendente_oggi(azioni_oggi: list[Azione]) -> StatoDipendente:
    return stato_da_timbrature(azioni_oggi)


def calcola_ore_lavorate(timbrature: list[dict]) -> float:
    """Calcola ore da sequenza IT/IP/FP/FT."""
    totale = timedelta()
    inizio_turno = None
    inizio_pausa = None

    for t in sorted(timbrature, key=lambda x: x["timestamp"]):
        az = t["azione"]
        ts = t["timestamp"] if isinstance(t["timestamp"], datetime) else datetime.fromisoformat(str(t["timestamp"]))

        if az == "IT":
            inizio_turno = ts
            inizio_pausa = None
        elif az == "IP" and inizio_turno:
            totale += ts - inizio_turno
            inizio_pausa = ts
            inizio_turno = None
        elif az == "FP" and inizio_pausa:
            inizio_turno = ts
            inizio_pausa = None
        elif az == "FT" and inizio_turno:
            totale += ts - inizio_turno
            inizio_turno = None

    return round(totale.total_seconds() / 3600, 2)


def azioni_valide_per_badge(azioni_oggi: list[Azione]) -> list[Azione]:
    stato = stato_da_timbrature(azioni_oggi)
    return azioni_valide(stato)
