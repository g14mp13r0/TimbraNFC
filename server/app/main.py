import csv
import io
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from datetime import date, datetime, timedelta

from fastapi import Depends, FastAPI, File, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
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

from shared.kiosk_i18n import current_lang as _current_lang
from shared.kiosk_i18n import enrollment_js_strings
from shared.kiosk_i18n import t as _translate

from markupsafe import Markup

templates.env.globals["t"] = lambda key: _translate(key, _current_lang())
templates.env.globals["lang"] = lambda: _current_lang()
templates.env.globals["enrollment_js_strings"] = enrollment_js_strings


def _tojson_filter(value) -> Markup:
    return Markup(json.dumps(value, ensure_ascii=False))


templates.env.filters["tojson"] = _tojson_filter

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


def _sidebar_counts(db: Session, *, n_timb: int | None = None) -> dict:
    n_dip = db.query(func.count(Dipendente.id)).filter(Dipendente.attivo == True).scalar() or 0
    n_dev = db.query(func.count(Dispositivo.id)).scalar() or 0
    if n_timb is None:
        oggi_start = datetime.combine(date.today(), datetime.min.time())
        n_timb = (
            db.query(func.count(Timbratura.id))
            .filter(Timbratura.timestamp_terminale >= oggi_start)
            .scalar()
            or 0
        )
    return {"sidebar_n_dip": n_dip, "sidebar_n_dev": n_dev, "sidebar_n_timb": n_timb}


def _device_dict(d: Dispositivo, online: bool) -> dict:
    return {
        "id": d.id,
        "nome": d.nome,
        "device_uuid": d.device_uuid or "",
        "versione_sw": d.versione_sw,
        "ultimo_heartbeat": d.ultimo_heartbeat,
        "online": online,
    }


@app.get("/health")
def health():
    return {"status": "ok", "version": VERSION}


# --- Dashboard web (Jinja2) ---

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    counts = _sidebar_counts(db)
    recenti = (
        db.query(Timbratura)
        .options(joinedload(Timbratura.dipendente), joinedload(Timbratura.dispositivo))
        .order_by(Timbratura.ricevuto_il.desc())
        .limit(10)
        .all()
    )
    ctx = {
        "n_dip": counts["sidebar_n_dip"],
        "n_timb": counts["sidebar_n_timb"],
        "n_dev": counts["sidebar_n_dev"],
        "recenti": recenti,
        "active_page": "home",
        **counts,
    }
    return templates.TemplateResponse(request, "index.html", ctx)


@app.get("/dispositivi", response_class=HTMLResponse)
def page_dispositivi(request: Request, db: Session = Depends(get_db)):
    now = datetime.now()
    devices = []
    for d in db.query(Dispositivo).all():
        online = d.ultimo_heartbeat and (now - d.ultimo_heartbeat) < timedelta(minutes=3)
        devices.append(_device_dict(d, bool(online)))
    return templates.TemplateResponse(
        request,
        "dispositivi.html",
        {"devices": devices, "active_page": "dispositivi", **_sidebar_counts(db)},
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
    ctx = {
        "dipendenti": dips,
        "msg": msg,
        "error": error,
        "active_page": "dipendenti",
        **_sidebar_counts(db),
    }
    ctx["sidebar_n_dip"] = sum(1 for d in dips if d.attivo)
    return templates.TemplateResponse(request, "dipendenti.html", ctx)


@app.get("/dipendenti/export.csv")
def export_dipendenti_csv(db: Session = Depends(get_db)):
    dips = db.query(Dipendente).order_by(Dipendente.cognome, Dipendente.nome).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "Nome", "Cognome", "Badge", "Reparto", "Email", "Attivo"])
    for d in dips:
        writer.writerow([d.id, d.nome, d.cognome, d.badge_uid, d.reparto or "", d.email or "", "1" if d.attivo else "0"])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="dipendenti.csv"'},
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
        request,
        "dipendente_modifica.html",
        {"dipendente": dip, "error": error, "active_page": "dipendenti", **_sidebar_counts(db)},
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
        request,
        "dipendente_badge.html",
        {"dipendente": dip, "error": error, "active_page": "dipendenti", **_sidebar_counts(db)},
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
    n_totale = db.query(func.count(Timbratura.id)).scalar() or 0
    ctx = {
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
        **_sidebar_counts(db, n_timb=n_totale),
    }
    return templates.TemplateResponse(request, "timbrature.html", ctx)


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


@app.get("/timbrature/export.pdf")
def export_timbrature_pdf(
    db: Session = Depends(get_db),
    da: str | None = None,
    a: str | None = None,
    mese: str | None = None,
    dipendente_id: int | None = None,
):
    from server.app.services.pdf_export import timbrature_pdf
    from server.app.services.report import lista_timbrature, resolve_period

    da, a, _mese = resolve_period(da, a, mese)
    rows = lista_timbrature(db, da, a, dipendente_id)
    pdf = timbrature_pdf(rows, da, a, _current_lang())
    filename = f"timbrature_{da}_{a}.pdf"
    return StreamingResponse(
        iter([pdf]),
        media_type="application/pdf",
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
            **_sidebar_counts(db),
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
    writer.writerow(["Dipendente", "Data", "Ora inizio", "Ora fine", "Tempo totale"])
    for t in data["turni"]:
        writer.writerow([t["dipendente"], t["data"], t["ora_inizio"], t["ora_fine"] or "", t["durata"]])
    writer.writerow([])
    writer.writerow(["Riepilogo", "Giorni", "N. turni", "Tempo totale"])
    for r in data["riepilogo"]:
        writer.writerow([r["dipendente"], r["giorni"], r["n_turni"], r["durata_totale"]])
    buf.seek(0)
    filename = f"report_turni_{da}_{a}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/report/export.pdf")
def export_report_pdf(
    db: Session = Depends(get_db),
    da: str | None = None,
    a: str | None = None,
    mese: str | None = None,
    dipendente_id: int | None = None,
):
    from server.app.services.pdf_export import report_turni_pdf
    from server.app.services.report import report_turni, resolve_period

    da, a, _mese = resolve_period(da, a, mese)
    data = report_turni(db, da, a, dipendente_id)
    pdf = report_turni_pdf(data, da, a, _current_lang())
    filename = f"report_turni_{da}_{a}.pdf"
    return StreamingResponse(
        iter([pdf]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --- Impostazioni ---

def _settings_page_context(db: Session, *, msg: str = "", error: str = "", restart_error: str = "", network_warn: str = "", section: str = ""):
    from server.app.services.settings_env import (
        ENV_PATH,
        kiosk_background_path,
        localized_fields,
        localized_sections,
        parse_env_file,
        read_settings,
    )

    settings = read_settings(with_network=True)
    lang = settings.get("KIOSK_LANG", "it")
    env_raw = parse_env_file()
    bg_path = kiosk_background_path()
    secrets_set = {
        f["key"]
        for f in localized_fields(lang)
        if f["type"] == "password" and (env_raw.get(f["key"]) or os.environ.get(f["key"]))
    }

    return {
        "settings": settings,
        "fields": localized_fields(lang),
        "sections": localized_sections(lang),
        "secrets_set": secrets_set,
        "env_path": str(ENV_PATH.resolve()),
        "bg_exists": bg_path.is_file(),
        "bg_mtime": int(bg_path.stat().st_mtime) if bg_path.is_file() else 0,
        "msg": msg,
        "error": error,
        "restart_error": restart_error,
        "network_warn": network_warn,
        "saved_section": section,
        "active_page": "impostazioni",
        **_sidebar_counts(db),
    }


@app.get("/impostazioni", response_class=HTMLResponse)
def page_impostazioni(
    request: Request,
    db: Session = Depends(get_db),
    msg: str = "",
    error: str = "",
    restart_error: str = "",
    network_warn: str = "",
    section: str = "",
):
    return templates.TemplateResponse(
        request,
        "impostazioni.html",
        _settings_page_context(db, msg=msg, error=error, restart_error=restart_error, network_warn=network_warn, section=section),
    )


@app.post("/impostazioni/salva")
async def salva_impostazioni(request: Request, db: Session = Depends(get_db)):
    from server.app.services.settings_env import restart_kiosk, save_settings

    form = dict(await request.form())
    action = form.pop("action", "save")
    section = form.pop("section", "").strip()
    restart = action == "save_restart"

    if not section:
        return templates.TemplateResponse(
            request,
            "impostazioni.html",
            _settings_page_context(db, error="Sezione mancante"),
            status_code=400,
        )

    try:
        _, network_result = save_settings(form, section)
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "impostazioni.html",
            _settings_page_context(db, error=f"Errore salvataggio: {exc}"),
            status_code=400,
        )

    network_warn = ""
    if network_result:
        ok, detail = network_result
        if not ok:
            network_warn = detail

    def _redirect(query: str) -> RedirectResponse:
        from urllib.parse import quote

        query = f"{query}&section={quote(section)}"
        if network_warn:
            query = f"{query}&network_warn={quote(network_warn[:240])}"
        return RedirectResponse(f"/impostazioni?{query}", status_code=303)

    if restart:
        if section not in ("kiosk",):
            return _redirect("msg=saved")
        ok, detail = restart_kiosk()
        if ok:
            return _redirect("msg=saved_restart")
        return _redirect(f"msg=saved&restart_error={detail.replace(' ', '+')[:120]}")

    if network_result and network_result[0]:
        return _redirect("msg=saved_network")
    return _redirect("msg=saved")


@app.post("/impostazioni/sfondo")
async def upload_sfondo_kiosk(
    sfondo: UploadFile = File(...),
):
    from server.app.services.settings_env import save_kiosk_background

    content = await sfondo.read()
    if not content or len(content) > 5 * 1024 * 1024:
        return RedirectResponse("/impostazioni?msg=background_error", status_code=303)
    try:
        save_kiosk_background(content, filename="kiosk-background.png")
    except Exception:
        return RedirectResponse("/impostazioni?msg=background_error", status_code=303)
    return RedirectResponse("/impostazioni?msg=background", status_code=303)


@app.get("/impostazioni/sfondo-preview")
def sfondo_kiosk_preview():
    from fastapi.responses import FileResponse

    from server.app.services.settings_env import kiosk_background_path

    path = kiosk_background_path()
    if not path.is_file():
        from fastapi import HTTPException

        raise HTTPException(status_code=404)
    return FileResponse(path, media_type="image/png")


@app.get("/impostazioni/backup.zip")
def download_backup():
    from server.app.services.settings_env import create_backup_zip

    buf = create_backup_zip()
    filename = f"timbranfc-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


if __name__ == "__main__":
    import uvicorn
    from server.app.config import SERVER_HOST, SERVER_PORT

    uvicorn.run("server.app.main:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)
