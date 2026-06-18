"""Ruoli e permessi dashboard."""

from functools import wraps

from flask import flash, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import config
from db import get_db

RUOLI = ("admin", "hr", "lettura")

# Permessi per sezione/azione
PERMESSI = {
    "admin": {
        "index", "dipendenti", "sedi", "report", "export", "email",
        "audit", "utenti", "sync",
    },
    "hr": {
        "index", "dipendenti", "sedi", "report", "export", "email",
    },
    "lettura": {
        "index", "report",
    },
}


def ha_permesso(ruolo: str, permesso: str) -> bool:
    return permesso in PERMESSI.get(ruolo, set())


def autentica(username: str, password: str) -> dict | None:
    with get_db() as con:
        cur = con.cursor()
        cur.execute(
            "SELECT * FROM utenti WHERE username=? AND attivo=1",
            (username.strip().lower(),),
        )
        user = cur.fetchone()
        if user and check_password_hash(user["password_hash"], password):
            return dict(user)
    return None


def crea_utente_default() -> None:
    """Crea admin di default se la tabella utenti è vuota."""
    with get_db() as con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) AS n FROM utenti")
        if cur.fetchone()["n"] > 0:
            return
        cur.execute(
            """
            INSERT INTO utenti (username, password_hash, ruolo, nome)
            VALUES (?, ?, 'admin', 'Amministratore')
            """,
            ("admin", generate_password_hash(config.ADMIN_PASSWORD)),
        )


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated


def permesso_required(permesso: str):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("logged_in"):
                return redirect(url_for("login"))
            if not ha_permesso(session.get("ruolo", ""), permesso):
                flash("Permesso negato", "error")
                return redirect(url_for("index"))
            return f(*args, **kwargs)

        return decorated

    return decorator


def utente_corrente() -> str:
    return session.get("username", "sistema")
