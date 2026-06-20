import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from server.app.api import dashboard as dashboard_api
from server.app.api import devices as devices_api
from server.app.api import timbrature as timbrature_api
from server.app.config import SECRET_KEY, VERSION
from server.app.db import Base, engine, get_db
from server.app.models import Dipendente, Dispositivo, Sede, Timbratura, UtenteAdmin

app = FastAPI(title="TimbraNFC Server", version=VERSION)

app.include_router(devices_api.router)
app.include_router(timbrature_api.router)
app.include_router(dashboard_api.router)

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

_sessions: dict[str, dict] = {}


def _init_db():
    Base.metadata.create_all(bind=engine)
    from server.app.db import SessionLocal

    db = SessionLocal()
    try:
        if not db.query(Sede).first():
            db.add(Sede(id=1, nome="Sede Principale"))
        if not db.query(UtenteAdmin).first():
            from server.app.config import ADMIN_EMAIL, ADMIN_PASSWORD

            db.add(
                UtenteAdmin(
                    email=ADMIN_EMAIL,
                    password_hash=generate_password_hash(ADMIN_PASSWORD),
                    ruolo="admin",
                )
            )
        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def startup():
    _init_db()


@app.get("/health")
def health():
    return {"status": "ok", "version": VERSION}


# --- Dashboard web (Jinja2) ---

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    oggi = datetime.now().date()
    n_dip = db.query(Dipendente).filter(Dipendente.attivo == True).count()
    n_timb = (
        db.query(Timbratura)
        .filter(Timbratura.timestamp_terminale >= datetime.combine(oggi, datetime.min.time()))
        .count()
    )
    n_dev = db.query(Dispositivo).count()
    recenti = (
        db.query(Timbratura)
        .order_by(Timbratura.ricevuto_il.desc())
        .limit(10)
        .all()
    )
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "n_dip": n_dip, "n_timb": n_timb, "n_dev": n_dev, "recenti": recenti},
    )


@app.get("/dispositivi", response_class=HTMLResponse)
def page_dispositivi(request: Request, db: Session = Depends(get_db)):
    now = datetime.now()
    devices = []
    for d in db.query(Dispositivo).all():
        online = d.ultimo_heartbeat and (now - d.ultimo_heartbeat) < timedelta(minutes=3)
        devices.append({**d.__dict__, "online": online})
    return templates.TemplateResponse("dispositivi.html", {"request": request, "devices": devices})


@app.post("/dispositivi/{device_id}/restart-kiosk")
def restart_kiosk(device_id: int, db: Session = Depends(get_db)):
    from server.app.models import DeviceComando

    db.add(DeviceComando(dispositivo_id=device_id, tipo="restart_kiosk"))
    db.commit()
    return RedirectResponse("/dispositivi", status_code=303)


@app.get("/dipendenti", response_class=HTMLResponse)
def page_dipendenti(request: Request, db: Session = Depends(get_db)):
    dips = db.query(Dipendente).order_by(Dipendente.cognome).all()
    return templates.TemplateResponse("dipendenti.html", {"request": request, "dipendenti": dips})


@app.post("/dipendenti/add")
def add_dipendente(
    nome: str = Form(...),
    cognome: str = Form(...),
    badge_uid: str = Form(...),
    reparto: str = Form(""),
    db: Session = Depends(get_db),
):
    db.add(Dipendente(nome=nome, cognome=cognome, badge_uid=badge_uid.upper(), sede_id=1, reparto=reparto or None))
    db.commit()
    return RedirectResponse("/dipendenti", status_code=303)


if __name__ == "__main__":
    import uvicorn
    from server.app.config import SERVER_HOST, SERVER_PORT

    uvicorn.run("server.app.main:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)
