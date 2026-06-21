"""Report presenze: turni per dipendente e riepilogo periodo."""

from __future__ import annotations

import calendar
from datetime import date, datetime

from sqlalchemy.orm import Session

from server.app.models import Dipendente, Dispositivo, Timbratura
from shared.kiosk_i18n import action_label
from shared.turni import calcola_turni, riepilogo_da_turni


def resolve_period(
    da: str | None = None,
    a: str | None = None,
    mese: str | None = None,
) -> tuple[str, str, str]:
    """Restituisce (da, a, mese) con mese in formato YYYY-MM."""
    oggi = date.today()

    if mese:
        year_s, month_s = mese.split("-", 1)[:2]
        year, month = int(year_s), int(month_s)
        last_day = calendar.monthrange(year, month)[1]
        return (
            f"{year:04d}-{month:02d}-01",
            f"{year:04d}-{month:02d}-{last_day:02d}",
            f"{year:04d}-{month:02d}",
        )

    if da and a:
        return da, a, da[:7] if da[:7] == a[:7] else ""

    m = oggi.strftime("%Y-%m")
    last_day = calendar.monthrange(oggi.year, oggi.month)[1]
    return (
        oggi.replace(day=1).isoformat(),
        oggi.replace(day=last_day).isoformat(),
        m,
    )


def _range_datetime(da: str, a: str) -> tuple[datetime, datetime]:
    start = datetime.fromisoformat(da)
    end = datetime.fromisoformat(a + "T23:59:59")
    return start, end


def report_turni(
    db: Session,
    da: str,
    a: str,
    dipendente_id: int | None = None,
) -> dict:
    start, end = _range_datetime(da, a)

    q = db.query(Timbratura).filter(
        Timbratura.timestamp_terminale >= start,
        Timbratura.timestamp_terminale <= end,
    )
    if dipendente_id:
        q = q.filter(Timbratura.dipendente_id == dipendente_id)

    rows = q.order_by(Timbratura.timestamp_terminale).all()
    if not rows:
        return {"turni": [], "riepilogo": []}

    dip_cache: dict[int, Dipendente] = {}
    per_dip: dict[int, list[dict]] = {}

    for r in rows:
        per_dip.setdefault(r.dipendente_id, []).append(
            {"azione": r.azione, "timestamp": r.timestamp_terminale}
        )

    turni: list[dict] = []
    riepilogo: list[dict] = []

    for did, timbs in per_dip.items():
        if did not in dip_cache:
            dip_cache[did] = db.query(Dipendente).get(did)
        dip = dip_cache[did]
        if not dip:
            continue

        nome = f"{dip.cognome} {dip.nome}"
        turni_dip = calcola_turni(timbs)
        for t in turni_dip:
            turni.append(
                {
                    **t,
                    "dipendente_id": did,
                    "dipendente": nome,
                }
            )

        stats = riepilogo_da_turni(turni_dip)
        riepilogo.append(
            {
                "dipendente_id": did,
                "dipendente": nome,
                **stats,
            }
        )

    turni.sort(key=lambda x: (x["data"], x["dipendente"], x["ora_inizio"]))
    riepilogo.sort(key=lambda x: x["dipendente"])
    return {"turni": turni, "riepilogo": riepilogo}



def lista_timbrature(
    db: Session,
    da: str,
    a: str,
    dipendente_id: int | None = None,
) -> list[dict]:
    start, end = _range_datetime(da, a)

    q = (
        db.query(Timbratura, Dipendente, Dispositivo)
        .join(Dipendente, Timbratura.dipendente_id == Dipendente.id)
        .join(Dispositivo, Timbratura.dispositivo_id == Dispositivo.id)
        .filter(
            Timbratura.timestamp_terminale >= start,
            Timbratura.timestamp_terminale <= end,
        )
    )
    if dipendente_id:
        q = q.filter(Timbratura.dipendente_id == dipendente_id)

    rows = q.order_by(Timbratura.timestamp_terminale.desc()).all()
    out: list[dict] = []
    for t, dip, dev in rows:
        ts = t.timestamp_terminale
        out.append(
            {
                "id": t.id,
                "dipendente_id": dip.id,
                "dipendente": f"{dip.cognome} {dip.nome}",
                "badge_uid": dip.badge_uid,
                "reparto": dip.reparto or "—",
                "data": ts.date().isoformat(),
                "ora": ts.strftime("%H:%M:%S"),
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "ricevuto_il": t.ricevuto_il.strftime("%Y-%m-%d %H:%M:%S") if t.ricevuto_il else "—",
                "azione": t.azione,
                "azione_label": action_label(t.azione),
                "dispositivo": dev.nome,
            }
        )
    return out
