"""Autenticazione dashboard web (sessione cookie + ruoli)."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash

from server.app.models import UtenteAdmin

ROLE_ADMIN = "admin"
ROLE_CONTABILE = "contabile"
ROLES = {ROLE_ADMIN, ROLE_CONTABILE}

ROLE_ALIASES = {
    "admin": ROLE_ADMIN,
    "amministratore": ROLE_ADMIN,
    "administrator": ROLE_ADMIN,
    "contabile": ROLE_CONTABILE,
    "accountant": ROLE_CONTABILE,
    "comptable": ROLE_CONTABILE,
}

PUBLIC_EXACT = {"/login", "/health", "/favicon.ico", "/logout"}
PUBLIC_PREFIXES = ("/static/", "/api/")

CONTABILE_EXACT = {
    "/",
    "/timbrature",
    "/report",
    "/dipendenti",
    "/timbrature/export.csv",
    "/timbrature/export.pdf",
    "/report/export.csv",
    "/report/export.pdf",
    "/dipendenti/export.csv",
    "/impostazioni/sfondo-preview",
}
CONTABILE_PREFIXES = ("/dipendenti/", "/timbrature/", "/report/")


def normalize_ruolo(ruolo: str | None) -> str | None:
    if not ruolo:
        return None
    key = ruolo.strip().lower()
    return ROLE_ALIASES.get(key, key if key in ROLES else None)


def _initials(email: str) -> str:
    local = email.split("@", 1)[0]
    parts = [p for p in local.replace(".", " ").replace("_", " ").split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return (local[:2] or "??").upper()


def get_session_user(request: Request) -> dict | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    ruolo = normalize_ruolo(request.session.get("ruolo"))
    if ruolo not in ROLES:
        return None
    return {
        "id": int(user_id),
        "email": request.session.get("email") or "",
        "ruolo": ruolo,
    }


def login_user(request: Request, user: UtenteAdmin) -> None:
    request.session.clear()
    request.session["user_id"] = user.id
    request.session["email"] = user.email
    request.session["ruolo"] = normalize_ruolo(user.ruolo) or ROLE_ADMIN


def logout_user(request: Request) -> None:
    request.session.clear()


def authenticate(db: Session, email: str, password: str) -> UtenteAdmin | None:
    user = db.query(UtenteAdmin).filter(func.lower(UtenteAdmin.email) == email.strip().lower()).first()
    if not user or normalize_ruolo(user.ruolo) not in ROLES:
        return None
    if not check_password_hash(user.password_hash, password):
        return None
    return user


def is_public_path(path: str) -> bool:
    if path in PUBLIC_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)


def can_access(user: dict | None, path: str, method: str) -> bool:
    if user is None:
        return False
    ruolo = normalize_ruolo(user.get("ruolo"))
    if ruolo == ROLE_ADMIN:
        return True
    if ruolo != ROLE_CONTABILE:
        return False

    if path in CONTABILE_EXACT:
        return True
    if any(path.startswith(prefix) for prefix in CONTABILE_PREFIXES):
        return True
    if method.upper() == "POST" and path == "/timbrature/azzera":
        return False
    if method.upper() == "POST" and "/restart-kiosk" in path:
        return False
    if path.startswith("/dispositivi") or path.startswith("/impostazioni"):
        return False
    return False


def user_template_context(user: dict | None) -> dict:
    if not user:
        return {
            "current_user_email": "",
            "current_user_initials": "",
            "current_user_role": "",
            "user_is_admin": False,
        }
    ruolo = normalize_ruolo(user.get("ruolo")) or ""
    return {
        "current_user_email": user["email"],
        "current_user_initials": _initials(user["email"]),
        "current_user_role": ruolo,
        "user_is_admin": ruolo == ROLE_ADMIN,
    }


def login_redirect(path: str) -> RedirectResponse:
    safe = path if path.startswith("/") and not path.startswith("//") else "/"
    return RedirectResponse(f"/login?next={quote(safe)}", status_code=303)


def access_denied_redirect() -> RedirectResponse:
    return RedirectResponse("/?error=access_denied", status_code=303)
