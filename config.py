import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "presenze.db"

# Identificativo sede di questa timbratrice (multi-sede)
SEDE_ID = int(os.environ.get("SEDE_ID", "1"))

# Identificativo univoco dispositivo (per sync)
DEVICE_ID = os.environ.get("DEVICE_ID", f"timbratrice-{SEDE_ID}")

# API timbratrice
API_HOST = os.environ.get("API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("API_PORT", "8000"))
API_URL = f"http://{API_HOST}:{API_PORT}"
API_KEY = os.environ.get("API_KEY", "")

# Hub centralizzato: raccoglie dati da tutte le timbratrici
IS_HUB = os.environ.get("IS_HUB", "0") == "1"

# Sync verso hub (lasciare vuoto sul server hub o su installazione standalone)
SYNC_URL = os.environ.get("SYNC_URL", "").rstrip("/")
SYNC_INTERVAL = int(os.environ.get("SYNC_INTERVAL", "300"))

# Dashboard web
DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 8080
DASHBOARD_SECRET = os.environ.get("DASHBOARD_SECRET", "cambia-questa-chiave-in-produzione")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")

# GPIO (BCM) — Raspberry Pi
LED_VERDE = 17
LED_ROSSO = 27
BUZZER = 22

# Logica timbratura
MIN_SECONDI_DOPPIA_TIMBRATURA = 60

# Email report (opzionale)
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER)
REPORT_EMAIL_TO = os.environ.get("REPORT_EMAIL_TO", "")

# Modalità sviluppo senza hardware Pi/NFC
MOCK_GPIO = os.environ.get("MOCK_GPIO", "0") == "1"
MOCK_NFC = os.environ.get("MOCK_NFC", "0") == "1"
