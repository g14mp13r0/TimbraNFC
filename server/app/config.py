import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "server" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{DATA_DIR / 'timbranfc.db'}",
)
API_KEY = os.environ.get("API_KEY", "")
SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-in-produzione")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@local")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")
DEFAULT_SEDE_ID = int(os.environ.get("DEFAULT_SEDE_ID", "1"))
VERSION = "2.0.0"
