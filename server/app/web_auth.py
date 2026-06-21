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

PUBLIC_EXACT = {"/login", "/health", "/favicon.ico"}
PUBLIC_PREFIXES = ("/static/", "/api/")


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
    ruolo = request.session.get("ruolo")
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
    request.session["ruolo"] = user.ruolo


def logout_user(request: Request) -> None:
    request.session.clear()


def authenticate(db: Session, email: str, password: str) -> UtenteAdmin | None:
    user = db.query(UtenteAdmin).filter(func.lower(UtenteAdmin.email) == email.strip().lower()).first()
    if not user or user.ruolo not in ROLES:
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
    if user["ruolo"] == ROLE_ADMIN:
        return True
    if user["ruolo"] != ROLE_CONTABILE:
        return False

    if path == "/impostazioni/sfondo-preview" and method.upper() == "GET":
        return True

    blocked_prefixes = ("/dispositivi", "/impostazioni")
    if any(path.startswith(p) for p in blocked_prefixes):
        return False
    if method.upper() == "POST" and path == "/timbrature/azzera":
        return False
    if method.upper() == "POST" and "/restart-kiosk" in path:
        return False

    allowed_prefixes = ("/", "/timbrature", "/report", "/dipendenti", "/logout")
    return any(path == p or path.startswith(f"{p}/") for p in allowed_prefixes)


def user_template_context(user: dict | None) -> dict:
    if not user:
        return {
            "current_user_email": "",
            "current_user_initials": "",
            "current_user_role": "",
            "user_is_admin": False,
        }
    return {
        "current_user_email": user["email"],
        "current_user_initials": _initials(user["email"]),
        "current_user_role": user["ruolo"],
        "user_is_admin": user["ruolo"] == ROLE_ADMIN,
    }


def login_redirect(path: str) -> RedirectResponse:
    safe = path if path.startswith("/") and not path.startswith("//") else "/"
    return RedirectResponse(f"/login?next={quote(safe)}", status_code=303)


def access_denied_redirect() -> RedirectResponse:
    return RedirectResponse("/?error=access_denied", status_code=303)
