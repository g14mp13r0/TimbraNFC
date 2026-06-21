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
    # --- Rete LAN (IP del Raspberry) ---
    {
        "key": "NETWORK_MODE",
        "label": "Configurazione IP",
        "section": "network_lan",
        "type": "choice",
        "choices": [("dhcp", "DHCP (automatico)"), ("manual", "IP statico (manuale)")],
        "default": "dhcp",
        "hint": "DHCP: indirizzo assegnato dal router. Manuale: IP, maschera e gateway fissi.",
    },
    {
        "key": "LAN_IP",
        "label": "Indirizzo IP (LAN)",
        "section": "network_lan",
        "type": "text",
        "default": "",
        "hint": "Es. 192.168.178.124 — indirizzo da usare nel browser da altri PC",
    },
    {
        "key": "LAN_SUBNET",
        "label": "Maschera di sottorete",
        "section": "network_lan",
        "type": "text",
        "default": "255.255.255.0",
    },
    {
        "key": "LAN_GATEWAY",
        "label": "Gateway (router)",
        "section": "network_lan",
        "type": "text",
        "default": "",
        "hint": "Es. 192.168.178.1",
    },
    {
        "key": "LAN_DNS",
        "label": "DNS (opzionale)",
        "section": "network_lan",
        "type": "text",
        "default": "",
        "hint": "Lasciare vuoto per usare il gateway come DNS",
    },
    {
        "key": "DASHBOARD_URL",
        "label": "URL dashboard (da altri PC)",
        "section": "network_lan",
        "type": "readonly",
        "default": "http://127.0.0.1:8080",
        "hint": "Aprire questo indirizzo dal browser su PC/tablet in rete locale",
    },
    {
        "key": "LAN_INTERFACE",
        "label": "Interfaccia di rete",
        "section": "network_lan",
        "type": "readonly",
        "default": "",
    },
    # --- Dashboard e sync ---
    {
        "key": "SERVER_PORT",
        "label": "Porta dashboard",
        "section": "network_app",
        "type": "int",
        "default": "8080",
    },
    {
        "key": "SERVER_URL",
        "label": "URL API kiosk (locale)",
        "section": "network_app",
        "type": "readonly",
        "default": "http://127.0.0.1:8080",
        "hint": "Il kiosk sulla stessa Pi usa sempre 127.0.0.1 — non è l'IP LAN",
    },
    {
        "key": "SERVER_HOST",
        "label": "Bind server (tecnico)",
        "section": "network_app",
        "type": "readonly",
        "default": "0.0.0.0",
        "hint": "0.0.0.0 = il server ascolta su tutte le interfacce (corretto per LAN)",
    },
    {
        "key": "API_KEY",
        "label": "API Key",
        "section": "network_app",
        "type": "password",
        "default": "",
        "hint": "Opzionale in LAN chiusa; lasciare vuoto per non cambiare",
    },
    {
        "key": "SYNC_INTERVAL_SEC",
        "label": "Intervallo sync anagrafica (sec)",
        "section": "network_app",
        "type": "int",
        "default": "30",
    },
    {
        "key": "HEARTBEAT_INTERVAL_SEC",
        "label": "Intervallo heartbeat (sec)",
        "section": "network_app",
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
    "network_lan": "Rete LAN (Raspberry Pi)",
    "network_app": "Dashboard e sincronizzazione",
    "system": "Sistema e sicurezza",
    "backup": "Backup",
}

NETWORK_KEYS = frozenset({"NETWORK_MODE", "LAN_IP", "LAN_SUBNET", "LAN_GATEWAY", "LAN_DNS"})


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


def read_settings(*, with_network: bool = False) -> dict[str, str]:
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

    if with_network:
        return enrich_settings(merged)
    port = merged.get("SERVER_PORT", "8080")
    merged["SERVER_URL"] = f"http://127.0.0.1:{port}"
    merged["SERVER_HOST"] = merged.get("SERVER_HOST") or "0.0.0.0"
    return merged


def enrich_settings(merged: dict[str, str]) -> dict[str, str]:
    """Aggiunge IP rilevato, URL dashboard e valori derivati."""
    from server.app.services.network_config import detect_lan

    lan = detect_lan()
    mode = str(merged.get("NETWORK_MODE", "")).strip().lower()
    if mode not in ("dhcp", "manual"):
        mode = lan.get("mode", "dhcp") or "dhcp"
    merged["NETWORK_MODE"] = mode

    if mode == "manual":
        if not merged.get("LAN_SUBNET"):
            merged["LAN_SUBNET"] = "255.255.255.0"
    else:
        merged["LAN_IP"] = lan.get("ip", merged.get("LAN_IP", ""))
        merged["LAN_SUBNET"] = lan.get("subnet", merged.get("LAN_SUBNET", "255.255.255.0"))
        merged["LAN_GATEWAY"] = lan.get("gateway", merged.get("LAN_GATEWAY", ""))
        if not merged.get("LAN_DNS"):
            merged["LAN_DNS"] = lan.get("dns", merged.get("LAN_GATEWAY", ""))

    port = merged.get("SERVER_PORT", "8080")
    ip = merged.get("LAN_IP") or lan.get("ip") or "127.0.0.1"
    merged["DASHBOARD_URL"] = f"http://{ip}:{port}"
    merged["LAN_INTERFACE"] = lan.get("interface", "")
    merged["SERVER_HOST"] = merged.get("SERVER_HOST") or "0.0.0.0"
    merged["SERVER_URL"] = f"http://127.0.0.1:{port}"
    return merged


def apply_env_to_process(updates: dict[str, str]) -> None:
    """Aggiorna os.environ (es. lingua dashboard senza riavvio server)."""
    for key, val in updates.items():
        os.environ[key] = val


def localized_fields(lang: str | None = None) -> list[dict[str, Any]]:
    from shared.kiosk_i18n import field_hint, field_label, lang_label, normalize_lang, t

    code = normalize_lang(lang)
    out: list[dict[str, Any]] = []
    for field in SETTINGS_FIELDS:
        fc = dict(field)
        fc["label"] = field_label(field["key"], field.get("label", ""), code)
        if field.get("hint"):
            fc["hint"] = field_hint(field["key"], field["hint"], code)
        if field["type"] == "choice" and field["key"] == "KIOSK_LANG":
            fc["choices"] = [(v, lang_label(v)) for v, _ in field["choices"]]
        elif field["type"] == "choice" and field["key"] == "NETWORK_MODE":
            fc["choices"] = [(v, t(f"network_mode_{v}", code)) for v, _ in field["choices"]]
        if field["key"] in NETWORK_KEYS and field["key"] != "NETWORK_MODE":
            fc["network_manual"] = True
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
    import pwd
    from datetime import datetime

    script = ROOT / "standalone" / "restart-kiosk.sh"
    if not script.is_file():
        return False, f"Script non trovato: {script}"

    log_path = DATA_DIR / "kiosk-restart.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["APP_DIR"] = str(ROOT)
    try:
        env["APP_USER"] = pwd.getpwuid(ROOT.stat().st_uid).pw_name
    except (ImportError, KeyError, OSError):
        env.setdefault("APP_USER", "gpastorino")

    try:
        with open(log_path, "a", encoding="utf-8") as logf:
            logf.write(f"\n=== {datetime.now().isoformat()} ===\n")
            result = subprocess.run(
                ["bash", str(script)],
                cwd=str(ROOT),
                env=env,
                stdout=logf,
                stderr=subprocess.STDOUT,
                timeout=120,
                check=False,
            )
    except subprocess.TimeoutExpired:
        return False, "Timeout riavvio kiosk (120s)"
    except OSError as exc:
        return False, str(exc)

    if result.returncode != 0:
        try:
            tail = log_path.read_text(encoding="utf-8")[-1200:]
            last = [ln for ln in tail.splitlines() if ln.strip()][-1]
        except OSError:
            last = "restart-kiosk fallito"
        return False, last

    return True, "Kiosk in riavvio"


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


def save_settings(form: dict[str, str]) -> tuple[dict[str, str], tuple[bool, str] | None]:
    """Salva impostazioni dal form; password vuote = non modificare."""
    from server.app.services.network_config import apply_lan_network, validate_manual_network

    current = read_settings(with_network=True)
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

    merged = {**current, **updates}
    if "SERVER_PORT" in updates:
        updates["SERVER_URL"] = f"http://127.0.0.1:{updates['SERVER_PORT']}"
        merged["SERVER_URL"] = updates["SERVER_URL"]

    err = validate_manual_network(merged)
    if err:
        raise ValueError(err)

    if updates:
        update_env_file(updates)
        apply_env_to_process(updates)

    network_result: tuple[bool, str] | None = None
    if updates.keys() & NETWORK_KEYS:
        network_result = apply_lan_network(enrich_settings({**current, **updates}))

    return updates, network_result


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
