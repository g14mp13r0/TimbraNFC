"""Testi kiosk multilingua (it, fr, en)."""

from __future__ import annotations

import os

Lang = str

_DEFAULT_LANG = "it"
_SUPPORTED = frozenset({"it", "fr", "en"})

_STRINGS: dict[str, dict[Lang, str]] = {
    "badge_not_found": {
        "it": "Badge non riconosciuto",
        "fr": "Badge non reconnu",
        "en": "Badge not recognized",
    },
    "wait_before_stamp": {
        "it": "Attendere prima di timbrare di nuovo",
        "fr": "Veuillez patienter avant de pointer à nouveau",
        "en": "Please wait before clocking in again",
    },
    "invalid_action": {
        "it": "Azione non valida",
        "fr": "Action non valide",
        "en": "Invalid action",
    },
    "invalid_transition": {
        "it": "Transizione non valida",
        "fr": "Transition non valide",
        "en": "Invalid transition",
    },
    "no_action_available": {
        "it": "Nessuna azione disponibile",
        "fr": "Aucune action disponible",
        "en": "No action available",
    },
    "state_unavailable": {
        "it": "Timbratura non disponibile",
        "fr": "Pointage non disponible",
        "en": "Clock-in not available",
    },
    "error_generic": {
        "it": "Errore",
        "fr": "Erreur",
        "en": "Error",
    },
    "cancel": {
        "it": "Annulla",
        "fr": "Annuler",
        "en": "Cancel",
    },
    "state_label": {
        "it": "Stato",
        "fr": "Statut",
        "en": "Status",
    },
    "enrollment_ok": {
        "it": "Badge registrato",
        "fr": "Badge enregistré",
        "en": "Badge registered",
    },
    "enrollment_duplicate": {
        "it": "Badge già in uso",
        "fr": "Badge déjà utilisé",
        "en": "Badge already in use",
    },
    "action_IT": {
        "it": "Inizio Turno",
        "fr": "Début de poste",
        "en": "Shift start",
    },
    "action_IP": {
        "it": "Inizio Pausa",
        "fr": "Début de pause",
        "en": "Break start",
    },
    "action_FP": {
        "it": "Fine Pausa",
        "fr": "Fin de pause",
        "en": "Break end",
    },
    "action_FT": {
        "it": "Fine Turno",
        "fr": "Fin de poste",
        "en": "Shift end",
    },
    "stato_FUORI_TURNO": {
        "it": "Fuori turno",
        "fr": "Hors poste",
        "en": "Off shift",
    },
    "stato_IN_TURNO": {
        "it": "In turno",
        "fr": "En poste",
        "en": "On shift",
    },
    "stato_IN_PAUSA": {
        "it": "In pausa",
        "fr": "En pause",
        "en": "On break",
    },
}

_LOCALE_MAP = {
    "it": "it_IT.UTF-8",
    "fr": "fr_FR.UTF-8",
    "en": "en_GB.UTF-8",
}


def normalize_lang(lang: str | None) -> Lang:
    if not lang:
        return _DEFAULT_LANG
    code = lang.strip().lower()[:2]
    return code if code in _SUPPORTED else _DEFAULT_LANG


def current_lang() -> Lang:
    return normalize_lang(os.environ.get("KIOSK_LANG", _DEFAULT_LANG))


def t(key: str, lang: Lang | None = None) -> str:
    code = normalize_lang(lang) if lang else current_lang()
    bucket = _STRINGS.get(key, {})
    return bucket.get(code) or bucket.get(_DEFAULT_LANG) or key


def action_label(azione: str, lang: Lang | None = None) -> str:
    return t(f"action_{azione}", lang)


def stato_label(stato: str, lang: Lang | None = None) -> str:
    return t(f"stato_{stato}", lang)


def locale_name(lang: Lang | None = None) -> str:
    code = normalize_lang(lang) if lang else current_lang()
    return _LOCALE_MAP.get(code, "it_IT.UTF-8")
