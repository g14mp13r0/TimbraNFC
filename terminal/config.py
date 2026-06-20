import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Modalità standalone: un solo Raspberry (timbratrice + server dashboard)
STANDALONE = os.environ.get("STANDALONE", "1") == "1"

DATA_DIR = Path(os.environ.get("TIMBRANFC_DATA", ROOT / "data"))
LOCAL_DB_PATH = DATA_DIR / "local_queue.db"
DEVICE_UUID_FILE = DATA_DIR / "device_uuid"

# In standalone il server gira sullo stesso Pi (porta 8080, LAN per dashboard da altri PC)
SERVER_URL = os.environ.get("SERVER_URL", "http://127.0.0.1:8080").rstrip("/")
API_KEY = os.environ.get("API_KEY", "")

SYNC_INTERVAL_SEC = int(os.environ.get("SYNC_INTERVAL_SEC", "30"))
HEARTBEAT_INTERVAL_SEC = int(os.environ.get("HEARTBEAT_INTERVAL_SEC", "120"))
MIN_SECONDI_TRA_TIMBRATURE = int(os.environ.get("MIN_SECONDI_TRA_TIMBRATURE", "30"))

VERSIONE_SW = os.environ.get("VERSIONE_SW", "2.0.0")

# Display 3.5" landscape — solo timbratrice, mai dashboard
DISPLAY_WIDTH = int(os.environ.get("DISPLAY_WIDTH", "480"))
DISPLAY_HEIGHT = int(os.environ.get("DISPLAY_HEIGHT", "320"))

# GPIO (BCM)
LED_VERDE = int(os.environ.get("LED_VERDE", "17"))
LED_ROSSO = int(os.environ.get("LED_ROSSO", "27"))
BUZZER = int(os.environ.get("BUZZER", "22"))
MOCK_GPIO = os.environ.get("MOCK_GPIO", "0") == "1"
MOCK_NFC = os.environ.get("MOCK_NFC", "0") == "1"
# Path lettore NFC per nfcpy (ACR122U: usb:072f:2200).
# Se non funziona, fallback automatico su "usb".
NFC_DEVICE_PATH = os.environ.get("NFC_DEVICE_PATH", "usb:072f:2200")

# Sfondo kiosk (PNG). Sovrascrivibile con KIOSK_BACKGROUND=/path/al/logo.png
KIOSK_BACKGROUND = Path(
    os.environ.get(
        "KIOSK_BACKGROUND",
        Path(__file__).resolve().parent / "assets" / "kiosk-background.png",
    )
)
