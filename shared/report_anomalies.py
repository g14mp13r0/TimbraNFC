"""Rilevamento anomalie sui turni (turni brevi, ravvicinati, aperti)."""

from __future__ import annotations

from datetime import datetime

MIN_SHIFT_SECONDS = 10 * 60
MIN_GAP_SECONDS = 5 * 60

ANOMALY_BREVE = "breve"
ANOMALY_RAVVICINATO = "ravvicinato"
ANOMALY_APERTO = "aperto"


def _shift_start(t: dict) -> datetime | None:
    if not t.get("data") or not t.get("ora_inizio"):
        return None
    return datetime.fromisoformat(f"{t['data']}T{t['ora_inizio']}")


def _shift_end(t: dict) -> datetime | None:
    if t.get("aperto") or not t.get("ora_fine"):
        return None
    return datetime.fromisoformat(f"{t['data']}T{t['ora_fine']}")


def annota_anomalie_turni(turni: list[dict]) -> list[dict]:
    """Aggiunge campo `anomalie` (lista codici) a ogni turno."""
    if not turni:
        return turni

    ordered = sorted(
        turni,
        key=lambda t: (t.get("dipendente_id", 0), t.get("data", ""), t.get("ora_inizio") or ""),
    )
    last_chiuso: dict[tuple[int, str], dict] = {}

    for t in ordered:
        flags: list[str] = []
        if t.get("aperto"):
            flags.append(ANOMALY_APERTO)
        if not t.get("aperto") and not t.get("incompleto"):
            sec = int(t.get("durata_secondi") or 0)
            if sec < MIN_SHIFT_SECONDS:
                flags.append(ANOMALY_BREVE)

        did = t.get("dipendente_id")
        data = t.get("data", "")
        key = (did, data) if did is not None else None
        prev = last_chiuso.get(key) if key else None
        start = _shift_start(t)
        prev_end = _shift_end(prev) if prev else None
        if prev and start and prev_end and not t.get("aperto"):
            gap = (start - prev_end).total_seconds()
            if 0 <= gap < MIN_GAP_SECONDS:
                flags.append(ANOMALY_RAVVICINATO)

        t["anomalie"] = flags
        if not t.get("aperto") and not t.get("incompleto") and t.get("ora_fine") and key:
            last_chiuso[key] = t

    return turni


def _anomalie_sospette(anomalie: list[str]) -> list[str]:
    return [c for c in anomalie if c in (ANOMALY_BREVE, ANOMALY_RAVVICINATO)]


def conta_anomalie(turni: list[dict]) -> int:
    return sum(1 for t in turni if _anomalie_sospette(t.get("anomalie", [])))


def totale_per_reparto(turni: list[dict]) -> list[dict]:
    from shared.turni import format_durata

    agg: dict[str, dict] = {}
    for t in turni:
        if t.get("incompleto"):
            continue
        rep = t.get("reparto") or "—"
        bucket = agg.setdefault(rep, {"reparto": rep, "secondi": 0, "dip_ids": set()})
        bucket["secondi"] += int(t.get("durata_secondi") or 0)
        if t.get("dipendente_id") is not None:
            bucket["dip_ids"].add(t["dipendente_id"])

    rows = []
    for rep in sorted(agg.keys(), key=lambda x: x.lower()):
        v = agg[rep]
        rows.append(
            {
                "reparto": rep,
                "n_dipendenti": len(v["dip_ids"]),
                "durata_totale": format_durata(v["secondi"]),
            }
        )
    return rows


def riepilogo_tempo(turni: list[dict]) -> dict:
    from shared.turni import format_durata

    secondi = sum(int(t.get("durata_secondi") or 0) for t in turni if not t.get("incompleto"))
    n_aperti = sum(1 for t in turni if t.get("aperto"))
    n_turni = len([t for t in turni if not t.get("incompleto")])
    return {
        "durata_totale": format_durata(secondi),
        "n_turni": n_turni,
        "n_aperti": n_aperti,
    }


def short_name(cognome_nome: str) -> str:
    parts = cognome_nome.strip().split(maxsplit=1)
    if len(parts) == 2:
        return f"{parts[0]} {parts[1][0]}."
    return cognome_nome


def nota_anomalie(turni: list[dict], *, lang: str = "it") -> str | None:
    from shared.kiosk_i18n import t

    flagged = [
        t
        for t in turni
        if t.get("anomalie")
        and (ANOMALY_BREVE in t["anomalie"] or ANOMALY_RAVVICINATO in t["anomalie"])
    ]
    if not flagged:
        flagged = [t for t in turni if t.get("anomalie")]
    if not flagged:
        return None

    starts = [_shift_start(t) for t in flagged]
    ends = [_shift_end(t) or _shift_start(t) for t in flagged]
    starts = [s for s in starts if s]
    ends = [e for e in ends if e]
    if not starts:
        return None

    da_ora = min(starts).strftime("%H:%M")
    a_ora = max(ends).strftime("%H:%M") if ends else da_ora
    return t("report_anomaly_note", lang).format(
        n=conta_anomalie(turni),
        da_ora=da_ora,
        a_ora=a_ora,
    )
