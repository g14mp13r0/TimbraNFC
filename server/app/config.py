import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(os.environ.get("TIMBRANFC_DATA", ROOT / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

STANDALONE = os.environ.get("STANDALONE", "1") == "1"

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{DATA_DIR / 'timbranfc.db'}",
)

# 0.0.0.0 → dashboard accessibile da altri PC in LAN
SERVER_HOST = os.environ.get("SERVER_HOST", "0.0.0.0")
try:
    SERVER_PORT = int(os.environ.get("SERVER_PORT", "8080"))
except (TypeError, ValueError):
    SERVER_PORT = 8080
if not (1 <= SERVER_PORT <= 65535):
    SERVER_PORT = 8080

API_KEY = os.environ.get("API_KEY", "")
SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-in-produzione")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@local")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")
CONTABILE_EMAIL = os.environ.get("CONTABILE_EMAIL", "contabile@local")
CONTABILE_PASSWORD = os.environ.get("CONTABILE_PASSWORD", "contabile")
DEFAULT_SEDE_ID = int(os.environ.get("DEFAULT_SEDE_ID", "1"))
VERSION = "2.0.0"
