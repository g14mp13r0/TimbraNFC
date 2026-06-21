"""Formattazione date per la UI (standard italiano dd/mm/yyyy)."""

from __future__ import annotations

from datetime import date, datetime

_DATE_FMT = "%d/%m/%Y"
_DATETIME_FMT = "%d/%m/%Y %H:%M"
_DATETIME_SEC_FMT = "%d/%m/%Y %H:%M:%S"

_WEEKDAY_SHORT: dict[str, list[str]] = {
    "it": ["lun", "mar", "mer", "gio", "ven", "sab", "dom"],
    "fr": ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."],
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
}


def format_kiosk_date(value: datetime | None = None, *, lang: str | None = None) -> str:
    """Data kiosk con giorno della settimana nella lingua selezionata (no locale OS)."""
    from shared.kiosk_i18n import kiosk_lang_code, normalize_lang

    dt = value or datetime.now()
    code = normalize_lang(lang) if lang else kiosk_lang_code()
    days = _WEEKDAY_SHORT.get(code, _WEEKDAY_SHORT["it"])
    return f"{days[dt.weekday()]} {dt.strftime(_DATE_FMT)}"


def format_date(value: date | datetime | str | None) -> str:
    if value is None:
        return "—"
    if isinstance(value, datetime):
        return value.date().strftime(_DATE_FMT)
    if isinstance(value, date):
        return value.strftime(_DATE_FMT)
    s = str(value).strip()
    if not s or s == "—":
        return "—"
    if len(s) >= 10 and s[4:5] == "-" and s[7:8] == "-":
        try:
            return date.fromisoformat(s[:10]).strftime(_DATE_FMT)
        except ValueError:
            pass
    return s


def format_datetime(value: date | datetime | str | None, *, seconds: bool = True) -> str:
    if value is None:
        return "—"
    if isinstance(value, datetime):
        fmt = _DATETIME_SEC_FMT if seconds else _DATETIME_FMT
        return value.strftime(fmt)
    if isinstance(value, date):
        return value.strftime(_DATE_FMT)
    s = str(value).strip()
    if not s or s == "—":
        return "—"
    normalized = s.replace(" ", "T", 1) if " " in s and "T" not in s else s
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return format_date(s)
    fmt = _DATETIME_SEC_FMT if seconds else _DATETIME_FMT
    return dt.strftime(fmt)
