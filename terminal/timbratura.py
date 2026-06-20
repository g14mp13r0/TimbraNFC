"""Logica timbratura locale — scrive sempre in coda prima di qualunque rete."""

import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import terminal.config as config
import terminal.local_queue as local_queue
from terminal.stati import AZIONI_LABEL, azione_automatica, azioni_valide, stato_da_timbrature, transizione_valida

log = logging.getLogger("timbratura")


def processa_badge(badge_uid: str) -> dict:
    """Ritorna info dipendente + stato + azioni valide (offline-first)."""
    uid = badge_uid.strip().upper()
    dip = local_queue.get_dipendente(uid)
    if not dip:
        return {"ok": False, "msg": "Badge non riconosciuto"}

    azioni_oggi = local_queue.get_azioni_oggi(uid)
    stato = stato_da_timbrature(azioni_oggi)
    return {
        "ok": True,
        "badge_uid": uid,
        "nome": dip["nome"],
        "cognome": dip["cognome"],
        "stato": stato,
        "azioni_valide": azioni_valide(stato),
    }


def registra_timbratura(badge_uid: str, azione: str, feedback_fn=None) -> dict:
    uid = badge_uid.strip().upper()
    info = processa_badge(uid)

    def fb(ok: bool):
        if feedback_fn:
            feedback_fn(ok)

    if not info.get("ok"):
        fb(False)
        return info

    if azione not in info["azioni_valide"]:
        fb(False)
        return {
            "ok": False,
            "msg": f"Azione {azione} non valida per stato {info['stato']}",
            "nome": f"{info['nome']} {info['cognome']}",
        }

    if not transizione_valida(info["stato"], azione):
        fb(False)
        return {"ok": False, "msg": "Transizione non valida"}

    ultima = local_queue.ultima_timbratura(uid)
    if ultima:
        diff = datetime.now() - datetime.fromisoformat(ultima["timestamp"])
        if diff.total_seconds() < config.MIN_SECONDI_TRA_TIMBRATURE:
            fb(False)
            return {"ok": False, "msg": "Attendere prima di timbrare di nuovo", "nome": f"{info['nome']} {info['cognome']}"}

    id_locale = local_queue.enqueue_timbratura(uid, azione)
    ora = datetime.now().strftime("%H:%M")
    fb(True)
    log.info("Timbratura locale #%s: %s %s — %s", id_locale, info["nome"], info["cognome"], azione)

    # Standalone: sincronizza subito verso il server locale (stesso Raspberry)
    if config.STANDALONE:
        try:
            from terminal import sync_agent
            sync_agent.push_timbrature()
        except Exception as e:
            log.warning("Sync immediata fallita (resta in coda): %s", e)

    return {
        "ok": True,
        "id_locale": id_locale,
        "nome": f"{info['nome']} {info['cognome']}",
        "azione": azione,
        "label": AZIONI_LABEL[azione],
        "ora": ora,
    }


def registra_timbratura_auto(badge_uid: str, feedback_fn=None) -> dict:
    """Timbratura automatica: primo passaggio IT, secondo FT (senza touch)."""
    uid = badge_uid.strip().upper()
    info = processa_badge(uid)
    if not info.get("ok"):
        if feedback_fn:
            feedback_fn(False)
        return info

    azione = azione_automatica(info["stato"])
    if not azione:
        if feedback_fn:
            feedback_fn(False)
        return {
            "ok": False,
            "msg": f"Stato {info['stato']} — timbratura non disponibile",
            "nome": f"{info['nome']} {info['cognome']}",
        }

    return registra_timbratura(uid, azione, feedback_fn=feedback_fn)
