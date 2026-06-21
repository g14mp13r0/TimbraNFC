"""Export HTML report turni (stampa / archivio)."""

from __future__ import annotations

import base64
import mimetypes
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from server.app.config import ROOT
from shared.dates import format_date, format_datetime
from shared.kiosk_i18n import normalize_lang, t
from shared.report_anomalies import (
    ANOMALY_APERTO,
    ANOMALY_BREVE,
    ANOMALY_RAVVICINATO,
    annota_anomalie_turni,
    conta_anomalie,
    nota_anomalie,
    riepilogo_tempo,
    short_name,
    totale_per_reparto,
)

_TPL_DIR = Path(__file__).resolve().parent.parent / "templates"
_JINJA = Environment(
    loader=FileSystemLoader(str(_TPL_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}


def _path_to_data_uri(path: Path) -> str | None:
    if not path.is_file():
        return None
    mime, _ = mimetypes.guess_type(str(path))
    if not mime:
        mime = "image/png"
    try:
        data = base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return None
    return f"data:{mime};base64,{data}"


def _resolve_logo_path(raw: str) -> Path | None:
    if not raw:
        return None
    p = Path(raw)
    if not p.is_file():
        p = ROOT / raw
    if p.is_file() and p.suffix.lower() in _IMAGE_SUFFIXES:
        return p
    return None


def _report_brand() -> dict:
    try:
        from server.app.services.settings_env import kiosk_background_path, parse_env_file

        env = parse_env_file()
        name = (env.get("REPORT_BRAND_NAME") or env.get("SEDE_NOME") or "TimbraNFC").strip()
        tagline = (env.get("REPORT_BRAND_TAGLINE") or t("report_brand_tagline_default")).strip()
        custom = (env.get("REPORT_BRAND_LOGO") or "").strip()

        logo_path = _resolve_logo_path(custom)
        if not logo_path:
            bg = kiosk_background_path()
            if bg.is_file():
                logo_path = bg

        logo_uri = _path_to_data_uri(logo_path) if logo_path else None
        if logo_uri:
            logo_letter = ""
        elif custom and len(custom) <= 2:
            logo_letter = custom[:1].upper()
        else:
            logo_letter = (name[:1] or "T").upper()

        return {"name": name, "tagline": tagline, "logo_letter": logo_letter, "logo_uri": logo_uri}
    except Exception:
        return {"name": "TimbraNFC", "tagline": t("report_brand_tagline_default"), "logo_letter": "T", "logo_uri": None}


def _anomaly_label(code: str, lang: str) -> str:
    key = {
        ANOMALY_BREVE: "report_flag_breve",
        ANOMALY_RAVVICINATO: "report_flag_ravvicinato",
        ANOMALY_APERTO: "report_flag_aperto",
    }.get(code, code)
    return t(key, lang)


def build_report_context(
    data: dict,
    da: str,
    a: str,
    *,
    lang: str | None = None,
    dipendente_id: int | None = None,
) -> dict:
    code = normalize_lang(lang)
    turni = annota_anomalie_turni(list(data.get("turni", [])))
    riepilogo = sorted(data.get("riepilogo", []), key=lambda r: r["dipendente"].lower())
    stats = riepilogo_tempo(turni)
    reparti = totale_per_reparto(turni)
    n_anomalie = conta_anomalie(turni)
    brand = _report_brand()

    if dipendente_id and riepilogo:
        focus = next((r for r in riepilogo if r.get("dipendente_id") == dipendente_id), riepilogo[0])
        card_dipendente = short_name(focus["dipendente"])
        card_hint = f"{t('col_department', code)} {focus.get('reparto') or '—'}"
    elif len(riepilogo) == 1:
        focus = riepilogo[0]
        card_dipendente = short_name(focus["dipendente"])
        card_hint = f"{t('col_department', code)} {focus.get('reparto') or '—'}"
    else:
        card_dipendente = t("report_all_employees", code)
        card_hint = t("report_n_employees", code).format(n=len(riepilogo))

    hint_aperti = ""
    if stats["n_aperti"]:
        hint_aperti = t("report_includes_open", code).format(n=stats["n_aperti"])

    detail_rows = []
    for row in sorted(turni, key=lambda r: (r["dipendente"].lower(), r["data"], r.get("ora_inizio") or "")):
        flags = [_anomaly_label(c, code) for c in row.get("anomalie", []) if c != ANOMALY_APERTO]
        if row.get("aperto"):
            fine_display = _anomaly_label(ANOMALY_APERTO, code)
            fine_live = True
        else:
            fine_display = row.get("ora_fine") or "—"
            fine_live = False
        detail_rows.append(
            {
                "dipendente": row["dipendente"],
                "reparto": row.get("reparto") or "—",
                "data": format_date(row["data"]),
                "ora_inizio": row.get("ora_inizio") or "—",
                "ora_fine": fine_display,
                "fine_live": fine_live,
                "durata": row.get("durata") or "—",
                "flags": flags,
                "flagged": any(c in row.get("anomalie", []) for c in (ANOMALY_BREVE, ANOMALY_RAVVICINATO)),
            }
        )

    return {
        "lang": code,
        "title": f"TimbraNFC — {t('nav_report', code)}",
        "brand_name": brand["name"],
        "brand_tagline": brand["tagline"],
        "logo_letter": brand["logo_letter"],
        "logo_uri": brand["logo_uri"],
        "generated_at": format_datetime(datetime.now(), seconds=False),
        "period_da": format_date(da),
        "period_a": format_date(a),
        "card_dipendente": card_dipendente,
        "card_hint": card_hint,
        "durata_totale": stats["durata_totale"],
        "hint_aperti": hint_aperti,
        "n_turni": stats["n_turni"],
        "n_anomalie": n_anomalie,
        "reparti": reparti,
        "turni": detail_rows,
        "anomaly_note": nota_anomalie(turni, lang=code),
        "labels": {
            "summary": t("report_html_summary", code),
            "employee": t("lbl_employee", code),
            "total_time": t("col_total_time", code),
            "shifts": t("col_n_shifts", code),
            "anomalies": t("report_anomalies", code),
            "in_period": t("report_in_period", code),
            "suspicious": t("report_suspicious", code),
            "dept_totals": t("report_dept_totals", code),
            "department": t("col_department", code),
            "employees": t("report_employees_count", code),
            "dept_hours": t("report_dept_hours", code),
            "detail": t("report_detail", code),
            "legend_open": t("report_legend_open", code),
            "legend_warn": t("report_legend_warn", code),
            "date": t("col_date", code),
            "start": t("shift_start", code),
            "end": t("shift_end", code),
            "footer": t("report_html_footer", code),
            "page": t("report_page", code),
            "anomaly_title": t("report_anomaly_title", code),
            "generated": t("report_generated", code),
            "period": t("report_period_label", code),
        },
    }


def report_turni_html(data: dict, da: str, a: str, lang: str | None = None, dipendente_id: int | None = None) -> str:
    ctx = build_report_context(data, da, a, lang=lang, dipendente_id=dipendente_id)
    return _JINJA.get_template("report_export.html").render(**ctx)


def report_turni_pdf(
    data: dict,
    da: str,
    a: str,
    lang: str | None = None,
    dipendente_id: int | None = None,
) -> bytes:
    """Genera PDF dal template HTML del report (WeasyPrint)."""
    html = report_turni_html(data, da, a, lang=lang, dipendente_id=dipendente_id)
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise RuntimeError(
            "WeasyPrint non installato: pip install weasyprint "
            "(su Raspberry Pi servono anche libpango e libgdk-pixbuf)"
        ) from exc
    return HTML(string=html, base_url=str(_TPL_DIR)).write_pdf()
