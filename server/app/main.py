import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from werkzeug.security import check_password_hash, generate_password_hash

from server.app.api import dashboard as dashboard_api
from server.app.api import devices as devices_api
from server.app.api import enrollment as enrollment_api
from server.app.api import timbrature as timbrature_api
from server.app.config import SECRET_KEY, VERSION
from server.app.db import Base, engine, get_db
from server.app.models import Dipendente, Dispositivo, Sede, Timbratura, UtenteAdmin

app = FastAPI(title="TimbraNFC Server", version=VERSION)

app.include_router(devices_api.router)
app.include_router(timbrature_api.router)
app.include_router(dashboard_api.router)
app.include_router(enrollment_api.router)

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
        .options(joinedload(Timbratura.dipendente), joinedload(Timbratura.dispositivo))
        .order_by(Timbratura.ricevuto_il.desc())
        .limit(10)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "n_dip": n_dip,
            "n_timb": n_timb,
            "n_dev": n_dev,
            "recenti": recenti,
            "active_page": "home",
            "sidebar_n_dip": n_dip,
            "sidebar_n_dev": n_dev,
        },
    )


@app.get("/dispositivi", response_class=HTMLResponse)
def page_dispositivi(request: Request, db: Session = Depends(get_db)):
    now = datetime.now()
    devices = []
    for d in db.query(Dispositivo).all():
        online = d.ultimo_heartbeat and (now - d.ultimo_heartbeat) < timedelta(minutes=3)
        devices.append({**d.__dict__, "online": online})
    return templates.TemplateResponse(
        request,
        "dispositivi.html",
        {"devices": devices, "active_page": "dispositivi", "sidebar_n_dev": len(devices)},
    )


@app.post("/dispositivi/{device_id}/restart-kiosk")
def restart_kiosk(device_id: int, db: Session = Depends(get_db)):
    from server.app.models import DeviceComando

    db.add(DeviceComando(dispositivo_id=device_id, tipo="restart_kiosk"))
    db.commit()
    return RedirectResponse("/dispositivi", status_code=303)


@app.get("/dipendenti", response_class=HTMLResponse)
def page_dipendenti(request: Request, db: Session = Depends(get_db), msg: str = "", error: str = ""):
    dips = db.query(Dipendente).order_by(Dipendente.cognome, Dipendente.nome).all()
    return templates.TemplateResponse(
        request,
        "dipendenti.html",
        {
            "dipendenti": dips,
            "msg": msg,
            "error": error,
            "active_page": "dipendenti",
            "sidebar_n_dip": len(dips),
        },
    )


@app.post("/dipendenti/add")
def add_dipendente(
    nome: str = Form(...),
    cognome: str = Form(...),
    badge_uid: str = Form(...),
    reparto: str = Form(""),
    email: str = Form(""),
    db: Session = Depends(get_db),
):
    from server.app.services import dipendenti as dip_svc
    from server.app.services import enrollment as enrollment_svc

    try:
        dip_svc.crea_dipendente(
            db, nome=nome, cognome=cognome, badge_uid=badge_uid, reparto=reparto or None, email=email or None
        )
    except dip_svc.DipendenteError as exc:
        return RedirectResponse(f"/dipendenti?error={exc.code}", status_code=303)

    enrollment_svc.stop_session()
    return RedirectResponse("/dipendenti?msg=aggiunto", status_code=303)


@app.get("/dipendenti/{dip_id}/modifica", response_class=HTMLResponse)
def page_modifica_dipendente(dip_id: int, request: Request, db: Session = Depends(get_db), error: str = ""):
    dip = db.query(Dipendente).filter(Dipendente.id == dip_id).first()
    if not dip:
        return RedirectResponse("/dipendenti?error=non_trovato", status_code=303)
    return templates.TemplateResponse(
        request, "dipendente_modifica.html", {"dipendente": dip, "error": error, "active_page": "dipendenti"}
    )


@app.post("/dipendenti/{dip_id}/modifica")
def modifica_dipendente(
    dip_id: int,
    nome: str = Form(...),
    cognome: str = Form(...),
    reparto: str = Form(""),
    email: str = Form(""),
    db: Session = Depends(get_db),
):
    from server.app.services import dipendenti as dip_svc

    try:
        dip_svc.aggiorna_dipendente(
            db, dip_id, nome=nome, cognome=cognome, reparto=reparto or None, email=email or None
        )
    except dip_svc.DipendenteError as exc:
        return RedirectResponse(f"/dipendenti/{dip_id}/modifica?error={exc.code}", status_code=303)
    return RedirectResponse("/dipendenti?msg=modificato", status_code=303)


@app.get("/dipendenti/{dip_id}/badge", response_class=HTMLResponse)
def page_badge_dipendente(dip_id: int, request: Request, db: Session = Depends(get_db), error: str = ""):
    dip = db.query(Dipendente).filter(Dipendente.id == dip_id).first()
    if not dip:
        return RedirectResponse("/dipendenti?error=non_trovato", status_code=303)
    return templates.TemplateResponse(
        request, "dipendente_badge.html", {"dipendente": dip, "error": error, "active_page": "dipendenti"}
    )


@app.post("/dipendenti/{dip_id}/badge")
def riassegna_badge_dipendente(
    dip_id: int,
    badge_uid: str = Form(...),
    db: Session = Depends(get_db),
):
    from server.app.services import dipendenti as dip_svc
    from server.app.services import enrollment as enrollment_svc

    try:
        dip_svc.riassegna_badge(db, dip_id, badge_uid)
    except dip_svc.DipendenteError as exc:
        return RedirectResponse(f"/dipendenti/{dip_id}/badge?error={exc.code}", status_code=303)

    enrollment_svc.stop_session()
    return RedirectResponse("/dipendenti?msg=badge_aggiornato", status_code=303)


@app.post("/dipendenti/{dip_id}/toggle")
def toggle_dipendente(dip_id: int, db: Session = Depends(get_db)):
    from server.app.services import dipendenti as dip_svc

    try:
        dip = dip_svc.toggle_attivo(db, dip_id)
    except dip_svc.DipendenteError:
        return RedirectResponse("/dipendenti?error=non_trovato", status_code=303)

    msg = "riattivato" if dip.attivo else "disattivato"
    return RedirectResponse(f"/dipendenti?msg={msg}", status_code=303)


@app.post("/dipendenti/{dip_id}/elimina")
def elimina_dipendente_route(dip_id: int, db: Session = Depends(get_db)):
    from server.app.services import dipendenti as dip_svc

    try:
        esito = dip_svc.elimina_dipendente(db, dip_id)
    except dip_svc.DipendenteError:
        return RedirectResponse("/dipendenti?error=non_trovato", status_code=303)
    return RedirectResponse(f"/dipendenti?msg={esito}", status_code=303)


@app.get("/timbrature", response_class=HTMLResponse)
def page_timbrature(
    request: Request,
    db: Session = Depends(get_db),
    da: str | None = None,
    a: str | None = None,
    mese: str | None = None,
    dipendente_id: int | None = None,
    msg: str = "",
    error: str = "",
):
    from server.app.services.report import lista_timbrature, resolve_period

    da, a, mese = resolve_period(da, a, mese)
    timbrature = lista_timbrature(db, da, a, dipendente_id)
    dipendenti = db.query(Dipendente).filter(Dipendente.attivo == True).order_by(Dipendente.cognome).all()
    n_totale = db.query(Timbratura).count()
    return templates.TemplateResponse(
        request,
        "timbrature.html",
        {
            "timbrature": timbrature,
            "dipendenti": dipendenti,
            "da": da,
            "a": a,
            "mese": mese,
            "dipendente_id": dipendente_id,
            "n_totale": n_totale,
            "msg": msg,
            "error": error,
            "active_page": "timbrature",
            "sidebar_n_timb": n_totale,
        },
    )


@app.post("/timbrature/azzera")
def azzera_timbrature(confirm: str = Form(...), db: Session = Depends(get_db)):
    from server.app.services.timbrature_admin import clear_timbrature_locali, clear_timbrature_server

    if confirm.strip().upper() != "AZZERA":
        return RedirectResponse("/timbrature?error=conferma_richiesta", status_code=303)

    n_server = clear_timbrature_server(db)
    n_local = 0
    try:
        import terminal.config as terminal_config

        n_local = clear_timbrature_locali(terminal_config.LOCAL_DB_PATH)
    except Exception:
        pass

    return RedirectResponse(
        f"/timbrature?msg=azzerate&n={n_server}&nl={n_local}",
        status_code=303,
    )


@app.get("/timbrature/export.csv")
def export_timbrature_csv(
    db: Session = Depends(get_db),
    da: str | None = None,
    a: str | None = None,
    mese: str | None = None,
    dipendente_id: int | None = None,
):
    from server.app.services.report import lista_timbrature, resolve_period

    da, a, _mese = resolve_period(da, a, mese)
    rows = lista_timbrature(db, da, a, dipendente_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "ID", "Data", "Ora", "Dipendente", "Badge", "Reparto",
        "Azione", "Codice", "Terminale", "Ricevuto server",
    ])
    for t in rows:
        writer.writerow([
            t["id"], t["data"], t["ora"], t["dipendente"], t["badge_uid"],
            t["reparto"], t["azione_label"], t["azione"], t["dispositivo"], t["ricevuto_il"],
        ])
    buf.seek(0)
    filename = f"timbrature_{da}_{a}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/report", response_class=HTMLResponse)
def page_report(
    request: Request,
    db: Session = Depends(get_db),
    da: str | None = None,
    a: str | None = None,
    mese: str | None = None,
    dipendente_id: int | None = None,
):
    from server.app.services.report import report_turni, resolve_period

    da, a, mese = resolve_period(da, a, mese)
    data = report_turni(db, da, a, dipendente_id)
    dipendenti = db.query(Dipendente).filter(Dipendente.attivo == True).order_by(Dipendente.cognome).all()
    return templates.TemplateResponse(
        request,
        "report.html",
        {
            "turni": data["turni"],
            "riepilogo": data["riepilogo"],
            "dipendenti": dipendenti,
            "da": da,
            "a": a,
            "mese": mese,
            "dipendente_id": dipendente_id,
            "active_page": "report",
        },
    )


@app.get("/report/export.csv")
def export_report_csv(
    db: Session = Depends(get_db),
    da: str | None = None,
    a: str | None = None,
    mese: str | None = None,
    dipendente_id: int | None = None,
):
    from server.app.services.report import report_turni, resolve_period

    da, a, _mese = resolve_period(da, a, mese)
    data = report_turni(db, da, a, dipendente_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Dipendente", "Data", "Ora inizio", "Ora fine", "Tempo totale", "Ore"])
    for t in data["turni"]:
        ore = round(t["durata_secondi"] / 3600, 2)
        writer.writerow([t["dipendente"], t["data"], t["ora_inizio"], t["ora_fine"] or "", t["durata"], ore])
    writer.writerow([])
    writer.writerow(["Riepilogo", "Giorni", "N. turni", "Ore totali", "Tempo totale", ""])
    for r in data["riepilogo"]:
        writer.writerow([r["dipendente"], r["giorni"], r["n_turni"], r["ore"], r["durata_totale"], ""])
    buf.seek(0)
    filename = f"report_turni_{da}_{a}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


if __name__ == "__main__":
    import uvicorn
    from server.app.config import SERVER_HOST, SERVER_PORT

    uvicorn.run("server.app.main:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)
