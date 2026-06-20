"""Sessione temporanea per registrazione badge NFC dalla dashboard."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass

SESSION_TTL_SEC = 120


@dataclass
class EnrollmentSession:
    session_id: str
    created_at: float
    expires_at: float
    badge_uid: str | None = None
    captured_at: float | None = None
    duplicate: bool = False
    target_dipendente_id: int | None = None

    @property
    def expired(self) -> bool:
        return time.time() > self.expires_at

    def status(self) -> str:
        if self.expired and not self.badge_uid:
            return "expired"
        if self.badge_uid:
            return "captured"
        return "waiting"


_lock = threading.Lock()
_session: EnrollmentSession | None = None


def start_session(target_dipendente_id: int | None = None) -> EnrollmentSession:
    global _session
    now = time.time()
    with _lock:
        _session = EnrollmentSession(
            session_id=uuid.uuid4().hex,
            created_at=now,
            expires_at=now + SESSION_TTL_SEC,
            target_dipendente_id=target_dipendente_id,
        )
        return _session


def get_session(session_id: str | None = None) -> EnrollmentSession | None:
    global _session
    with _lock:
        if _session is None:
            return None
        if _session.expired and not _session.badge_uid:
            _session = None
            return None
        if session_id and _session.session_id != session_id:
            return None
        return _session


def is_active() -> bool:
    s = get_session()
    return s is not None and not s.expired and s.badge_uid is None


def capture_badge(badge_uid: str, *, duplicate: bool = False) -> bool:
    global _session
    uid = badge_uid.strip().upper()
    if not uid:
        return False
    with _lock:
        if _session is None or _session.expired or _session.badge_uid:
            return False
        _session.badge_uid = uid
        _session.captured_at = time.time()
        _session.duplicate = duplicate
        return True


def stop_session() -> None:
    global _session
    with _lock:
        _session = None
