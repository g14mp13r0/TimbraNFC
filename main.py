import logging
import threading
import time

import uvicorn
from fastapi import FastAPI

import config
from api_routes import router as api_v1_router
from db import init_db
from nfc_reader import start_nfc_loop
from sync import avvia_loop_sync
from timbratura import esegui_timbratura

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("timbratrice")

app = FastAPI(
    title="Timbratrice NFC",
    description="API per timbratura presenze, integrazioni e multi-sede",
    version="1.1.0",
)
app.include_router(api_v1_router)

_last_event: dict = {"ok": None, "nome": "", "tipo": "", "ora": "", "msg": "", "sede_id": None, "ts": 0}
_event_lock = threading.Lock()

_gpio = None


def _setup_gpio():
    global _gpio
    if config.MOCK_GPIO:
        log.info("GPIO in modalità mock")
        return

    try:
        import RPi.GPIO as GPIO

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup([config.LED_VERDE, config.LED_ROSSO, config.BUZZER], GPIO.OUT)
        _gpio = GPIO
    except (ImportError, RuntimeError) as e:
        log.warning("GPIO non disponibile (%s), uso modalità mock", e)


def feedback(ok: bool) -> None:
    if _gpio is None:
        log.info("Feedback %s", "OK" if ok else "ERRORE")
        return

    pin = config.LED_VERDE if ok else config.LED_ROSSO
    _gpio.output(pin, True)
    _gpio.output(config.BUZZER, True)

    def _off():
        _gpio.output(pin, False)
        _gpio.output(config.BUZZER, False)

    threading.Timer(0.5, _off).start()


def _set_last_event(event: dict) -> None:
    with _event_lock:
        _last_event.update(event)
        _last_event["ts"] = time.time()


def timbra(uid: str) -> dict:
    result = esegui_timbratura(uid, feedback_fn=feedback)
    _set_last_event(result)
    return result


def _on_badge_read(uid: str) -> None:
    timbra(uid)


@app.on_event("startup")
def startup() -> None:
    init_db()
    _setup_gpio()
    thread = threading.Thread(target=start_nfc_loop, args=(_on_badge_read,), daemon=True)
    thread.start()
    avvia_loop_sync()
    mode = "HUB" if config.IS_HUB else "terminale"
    log.info("Timbratrice avviata [%s] — sede %s — %s:%s", mode, config.SEDE_ID, config.API_HOST, config.API_PORT)


@app.get("/health")
def health():
    return {"status": "ok", "sede_id": config.SEDE_ID}


@app.get("/api/last-event")
def last_event():
    with _event_lock:
        return dict(_last_event)


@app.post("/timbra/{uid}")
def timbra_endpoint(uid: str):
    return timbra(uid)


if __name__ == "__main__":
    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT, log_level="info")
