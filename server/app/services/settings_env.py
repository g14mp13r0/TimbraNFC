"""Lettura/scrittura .env e backup dati TimbraNFC."""

from __future__ import annotations

import io
import os
import re
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from server.app.config import DATA_DIR, ROOT

ENV_PATH = ROOT / ".env"
UPLOADS_DIR = DATA_DIR / "uploads"
DEFAULT_KIOSK_BG = ROOT / "terminal" / "assets" / "kiosk-background.png"

# Chiavi gestite dalla pagina Impostazioni (ordine = sezioni UI)
SETTINGS_FIELDS: list[dict[str, Any]] = [
    # --- Kiosk ---
    {
        "key": "KIOSK_LANG",
        "label": "Lingua (dashboard + kiosk)",
        "section": "kiosk",
        "type": "choice",
        "choices": [("it", "Italiano"), ("fr", "Français"), ("en", "English")],
        "default": "it",
        "hint": "Pagina web e touchscreen timbratrice",
    },
    {
        "key": "KIOSK_BACKGROUND",
        "label": "Sfondo kiosk (path)",
        "section": "kiosk",
        "type": "readonly",
        "default": str(DEFAULT_KIOSK_BG),
    },
    {
        "key": "DISPLAY_WIDTH",
        "label": "Larghezza display",
        "section": "kiosk",
        "type": "int",
        "default": "480",
    },
    {
        "key": "DISPLAY_HEIGHT",
        "label": "Altezza display",
        "section": "kiosk",
        "type": "int",
        "default": "320",
    },
    {
        "key": "KIOSK_CONFIRM_MS",
        "label": "Durata messaggio conferma (ms)",
        "section": "kiosk",
        "type": "int",
        "default": "4000",
    },
    {
        "key": "NFC_AUTO_TIMBRATURA",
        "label": "Timbratura automatica NFC",
        "section": "kiosk",
        "type": "bool",
        "default": "1",
        "hint": "1° passaggio = entrata, 2° = uscita (senza pulsanti touch)",
    },
    {
        "key": "MIN_SECONDI_TRA_TIMBRATURE",
        "label": "Secondi minimi tra timbrature",
        "section": "kiosk",
        "type": "int",
        "default": "30",
    },
    {
        "key": "NFC_BACKEND",
        "label": "Backend NFC",
        "section": "kiosk",
        "type": "choice",
        "choices": [("auto", "Auto (nfcpy → pcsc)"), ("pcsc", "PC/SC"), ("nfcpy", "nfcpy")],
        "default": "auto",
    },
    {
        "key": "NFC_DEVICE_PATH",
        "label": "Path dispositivo NFC",
        "section": "kiosk",
        "type": "text",
        "default": "usb:072f:2200",
    },
    {
        "key": "MOCK_NFC",
        "label": "Modalità mock NFC (test)",
        "section": "kiosk",
        "type": "bool",
        "default": "0",
    },
    {
        "key": "MOCK_GPIO",
        "label": "Modalità mock GPIO (test)",
        "section": "kiosk",
        "type": "bool",
        "default": "0",
    },
    # --- Rete ---
    {
        "key": "SERVER_URL",
        "label": "URL server (kiosk → API)",
        "section": "network",
        "type": "text",
        "default": "http://127.0.0.1:8080",
    },
    {
        "key": "SERVER_HOST",
        "label": "Host dashboard",
        "section": "network",
        "type": "text",
        "default": "0.0.0.0",
        "hint": "0.0.0.0 = accessibile da altri PC in LAN",
    },
    {
        "key": "SERVER_PORT",
        "label": "Porta dashboard",
        "section": "network",
        "type": "int",
        "default": "8080",
    },
    {
        "key": "API_KEY",
        "label": "API Key",
        "section": "network",
        "type": "password",
        "default": "",
        "hint": "Opzionale in LAN chiusa; lasciare vuoto per non cambiare",
    },
    {
        "key": "SYNC_INTERVAL_SEC",
        "label": "Intervallo sync anagrafica (sec)",
        "section": "network",
        "type": "int",
        "default": "30",
    },
    {
        "key": "HEARTBEAT_INTERVAL_SEC",
        "label": "Intervallo heartbeat (sec)",
        "section": "network",
        "type": "int",
        "default": "120",
    },
    # --- Sistema ---
    {
        "key": "TIMBRANFC_DATA",
        "label": "Cartella dati",
        "section": "system",
        "type": "text",
        "default": str(DATA_DIR),
    },
    {
        "key": "ADMIN_EMAIL",
        "label": "Email amministratore",
        "section": "system",
        "type": "text",
        "default": "admin@local",
    },
    {
        "key": "ADMIN_PASSWORD",
        "label": "Password amministratore",
        "section": "system",
        "type": "password",
        "default": "",
        "hint": "Lasciare vuoto per non modificare",
    },
    {
        "key": "SECRET_KEY",
        "label": "Secret key sessioni",
        "section": "system",
        "type": "password",
        "default": "",
        "hint": "Lasciare vuoto per non modificare",
    },
]

SECTION_LABELS = {
    "kiosk": "Kiosk / Timbratrice",
    "network": "Rete e sincronizzazione",
    "system": "Sistema e sicurezza",
    "backup": "Backup",
}


def _unquote_env_value(val: str) -> str:
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
        inner = val[1:-1]
        return inner.replace('\\"', '"').replace("\\\\", "\\")
    return val


def parse_env_file(path: Path | None = None) -> dict[str, str]:
    path = path or ENV_PATH
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = _unquote_env_value(val.split("#", 1)[0])
        out[key] = val
    return out


def read_settings() -> dict[str, str]:
    """Valori effettivi: .env + variabili d'ambiente del processo + default."""
    env = parse_env_file()
    merged: dict[str, str] = {}
    for field in SETTINGS_FIELDS:
        key = field["key"]
        if key in env:
            merged[key] = env[key]
        elif key in os.environ and os.environ[key] != "":
            merged[key] = os.environ[key]
        else:
            merged[key] = str(field.get("default", ""))

        if field["type"] == "bool":
            v = str(merged[key]).strip().lower()
            merged[key] = "1" if v in ("1", "true", "yes", "on") else "0"
        elif field["type"] in ("int", "text", "choice", "readonly"):
            merged[key] = str(merged[key]).strip()

    return merged


def apply_env_to_process(updates: dict[str, str]) -> None:
    """Aggiorna os.environ (es. lingua dashboard senza riavvio server)."""
    for key, val in updates.items():
        os.environ[key] = val


def localized_fields(lang: str | None = None) -> list[dict[str, Any]]:
    from shared.kiosk_i18n import field_hint, field_label, lang_label, normalize_lang

    code = normalize_lang(lang)
    out: list[dict[str, Any]] = []
    for field in SETTINGS_FIELDS:
        fc = dict(field)
        fc["label"] = field_label(field["key"], field.get("label", ""), code)
        if field.get("hint"):
            fc["hint"] = field_hint(field["key"], field["hint"], code)
        if field["type"] == "choice" and field["key"] == "KIOSK_LANG":
            fc["choices"] = [(v, lang_label(v)) for v, _ in field["choices"]]
        out.append(fc)
    return out


def localized_sections(lang: str | None = None) -> list[tuple[str, str]]:
    from shared.kiosk_i18n import normalize_lang, section_label

    code = normalize_lang(lang)
    return [
        (sid, section_label(sid, fallback, code))
        for sid, fallback in SECTION_LABELS.items()
        if sid != "backup"
    ]


def restart_kiosk() -> tuple[bool, str]:
    script = ROOT / "standalone" / "restart-kiosk.sh"
    if not script.is_file():
        return False, f"Script non trovato: {script}"
    try:
        subprocess.Popen(
            ["bash", str(script)],
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True, "Kiosk in riavvio"
    except OSError as exc:
        return False, str(exc)


def _env_quote(value: str) -> str:
    if re.search(r'[\s#"\'\\]', value):
        return f'"{value.replace(chr(92), chr(92) * 2)}"'
    return value


def update_env_file(updates: dict[str, str], path: Path | None = None) -> None:
    """Aggiorna o aggiunge chiavi nel file .env."""
    path = path or ENV_PATH
    lines: list[str] = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

    seen: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={_env_quote(updates[key])}\n")
                seen.add(key)
                continue
        new_lines.append(line if line.endswith("\n") else line + "\n")

    for key, val in updates.items():
        if key not in seen:
            new_lines.append(f"{key}={_env_quote(val)}\n")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(new_lines), encoding="utf-8")


def save_settings(form: dict[str, str]) -> dict[str, str]:
    """Salva impostazioni dal form; password vuote = non modificare."""
    current = parse_env_file()
    updates: dict[str, str] = {}

    for field in SETTINGS_FIELDS:
        key = field["key"]
        if field["type"] == "readonly":
            continue
        if field["type"] == "password":
            val = form.get(key, "").strip()
            if val:
                updates[key] = val
            continue

        raw = form.get(key, "").strip()
        if field["type"] == "bool":
            updates[key] = "1" if raw in ("1", "true", "on", "yes") else "0"
        elif raw or key not in current:
            updates[key] = raw if raw else str(field.get("default", ""))

    if updates:
        update_env_file(updates)
        apply_env_to_process(updates)
    return updates


def kiosk_background_path() -> Path:
    env = parse_env_file()
    raw = env.get("KIOSK_BACKGROUND", str(DEFAULT_KIOSK_BG))
    p = Path(raw)
    if p.is_file():
        return p
    return DEFAULT_KIOSK_BG if DEFAULT_KIOSK_BG.is_file() else p


def save_kiosk_background(content: bytes, filename: str = "kiosk-background.png") -> Path:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOADS_DIR / filename
    dest.write_bytes(content)
    # Copia anche nell'asset predefinito per compatibilità
    DEFAULT_KIOSK_BG.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_KIOSK_BG.write_bytes(content)
    update_env_file({"KIOSK_BACKGROUND": str(dest.resolve())})
    return dest


def create_backup_zip() -> io.BytesIO:
    """Zip con DB, coda locale, .env e sfondo kiosk."""
    buf = io.BytesIO()
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidates = [
        (DATA_DIR / "timbranfc.db", f"data/timbranfc.db"),
        (DATA_DIR / "local_queue.db", f"data/local_queue.db"),
        (DATA_DIR / "device_uuid", f"data/device_uuid"),
        (ENV_PATH, ".env"),
        (kiosk_background_path(), "kiosk-background.png"),
    ]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.txt", f"TimbraNFC backup {ts}\nRipristino: estrarre in cartella progetto.\n")
        for src, arc in candidates:
            if src.is_file():
                zf.write(src, arcname=arc)
    buf.seek(0)
    return buf
