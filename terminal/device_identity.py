import json
import uuid
from pathlib import Path

import requests

import terminal.config as config


def get_device_uuid() -> str:
    if config.DEVICE_UUID_FILE.exists():
        return config.DEVICE_UUID_FILE.read_text(encoding="utf-8").strip()

    uid = str(uuid.uuid4())
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.DEVICE_UUID_FILE.write_text(uid, encoding="utf-8")
    return uid


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if config.API_KEY:
        h["X-API-Key"] = config.API_KEY
    return h


def register_device(nome_suggerito: str = "Varco") -> dict | None:
    device_uuid = get_device_uuid()
    try:
        r = requests.post(
            f"{config.SERVER_URL}/api/v1/devices/register",
            json={"device_uuid": device_uuid, "nome_suggerito": nome_suggerito},
            headers=_headers(),
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        _save_registration(data)
        return data
    except Exception:
        return _load_registration()


def _save_registration(data: dict) -> None:
    path = config.DATA_DIR / "device_registration.json"
    path.write_text(json.dumps(data), encoding="utf-8")


def _load_registration() -> dict | None:
    path = config.DATA_DIR / "device_registration.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def get_registration() -> dict | None:
    return _load_registration()
