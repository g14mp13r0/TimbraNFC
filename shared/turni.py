"""Calcolo turni da sequenza timbrature IT/IP/FP/FT."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def parse_timestamp(ts: datetime | str) -> datetime:
    if isinstance(ts, datetime):
        return ts
    return datetime.fromisoformat(str(ts))


def normalizza_azione(azione: str) -> str:
    mapping = {"entrata": "IT", "uscita": "FT"}
    return mapping.get(azione, azione)


def stato_turno_aperto(
    timbrature: list[dict[str, Any]],
) -> tuple[datetime | None, datetime | None, timedelta]:
    """Stato macchina a stati dopo l'ultima timbratura (turno eventualmente aperto)."""
    inizio_turno: datetime | None = None
    segment_start: datetime | None = None
    durata = timedelta()

    for t in sorted(timbrature, key=lambda x: parse_timestamp(x["timestamp"])):
        az = normalizza_azione(t.get("azione") or t.get("tipo", ""))
        ts = parse_timestamp(t["timestamp"])

        if az == "IT":
            inizio_turno = ts
            segment_start = ts
            durata = timedelta()
        elif az == "IP" and segment_start:
            durata += ts - segment_start
            segment_start = None
        elif az == "FP" and inizio_turno and segment_start is None:
            segment_start = ts
        elif az == "FT" and inizio_turno:
            if segment_start:
                durata += ts - segment_start
            inizio_turno = None
            segment_start = None
            durata = timedelta()

    return inizio_turno, segment_start, durata


def _append_turno(
    turni: list[dict[str, Any]],
    *,
    inizio_turno: datetime | None,
    fine: datetime,
    durata: timedelta,
    aperto: bool,
    incompleto: bool = False,
) -> None:
    sec = int(durata.total_seconds())
    data_ref = inizio_turno if inizio_turno else fine
    turni.append(
        {
            "data": data_ref.date().isoformat(),
            "ora_inizio": inizio_turno.strftime("%H:%M:%S") if inizio_turno else None,
            "ora_fine": None if aperto else fine.strftime("%H:%M:%S"),
            "durata_secondi": sec,
            "durata": "—" if incompleto else format_durata(sec),
            "aperto": aperto,
            "incompleto": incompleto,
        }
    )


def format_durata(secondi: int) -> str:
    if secondi < 0:
        secondi = 0
    ore, resto = divmod(secondi, 3600)
    minuti, sec = divmod(resto, 60)
    if ore:
        return f"{ore}h {minuti:02d}m"
    if minuti:
        return f"{minuti}m {sec:02d}s"
    return f"{sec}s"


def calcola_turni(
    timbrature: list[dict[str, Any]],
    *,
    includi_aperti: bool = False,
    inizio_turno_aperto: datetime | None = None,
    segment_start_aperto: datetime | None = None,
    durata_aperto: timedelta | None = None,
) -> list[dict[str, Any]]:
    """Ricava turni completi (IT→FT) da timbrature ordinate per timestamp."""
    turni: list[dict[str, Any]] = []
    inizio_turno = inizio_turno_aperto
    segment_start = segment_start_aperto
    durata = durata_aperto if durata_aperto is not None else timedelta()
    if inizio_turno and segment_start is None and durata == timedelta():
        segment_start = inizio_turno

    for t in sorted(timbrature, key=lambda x: parse_timestamp(x["timestamp"])):
        az = normalizza_azione(t.get("azione") or t.get("tipo", ""))
        ts = parse_timestamp(t["timestamp"])

        if az == "IT":
            inizio_turno = ts
            segment_start = ts
            durata = timedelta()
        elif az == "IP" and segment_start:
            durata += ts - segment_start
            segment_start = None
        elif az == "FP" and inizio_turno and segment_start is None:
            segment_start = ts
        elif az == "FT":
            if inizio_turno:
                if segment_start:
                    durata += ts - segment_start
                _append_turno(
                    turni,
                    inizio_turno=inizio_turno,
                    fine=ts,
                    durata=durata,
                    aperto=False,
                )
                inizio_turno = None
                segment_start = None
                durata = timedelta()
            else:
                _append_turno(
                    turni,
                    inizio_turno=None,
                    fine=ts,
                    durata=timedelta(),
                    aperto=False,
                    incompleto=True,
                )

    if includi_aperti and inizio_turno:
        now = datetime.now()
        fine = now if segment_start else inizio_turno
        if segment_start:
            durata += now - segment_start
        _append_turno(
            turni,
            inizio_turno=inizio_turno,
            fine=fine,
            durata=durata,
            aperto=True,
        )

    return turni


def calcola_ore_lavorate(timbrature: list[dict[str, Any]]) -> float:
    turni = calcola_turni(timbrature)
    totale = sum(t["durata_secondi"] for t in turni if not t.get("aperto"))
    return round(totale / 3600, 2)


def riepilogo_da_turni(turni: list[dict[str, Any]]) -> dict[str, Any]:
    """Totali per dipendente a partire da turni già arricchiti con metadati dipendente."""
    if not turni:
        return {"n_turni": 0, "giorni": 0, "ore": 0.0, "durata_totale": "0s"}

    giorni = len({t["data"] for t in turni})
    secondi = sum(t["durata_secondi"] for t in turni if not t.get("aperto") and not t.get("incompleto"))
    return {
        "n_turni": len([t for t in turni if not t.get("aperto") and not t.get("incompleto")]),
        "giorni": giorni,
        "ore": round(secondi / 3600, 2),
        "durata_totale": format_durata(secondi),
    }
