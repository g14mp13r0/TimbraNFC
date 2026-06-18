import calendar
import logging
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO

import config
from db import get_db, get_riepilogo_ore

log = logging.getLogger("notifications")


def _smtp_configured() -> bool:
    return bool(config.SMTP_HOST and config.REPORT_EMAIL_TO)


def invia_email(oggetto: str, corpo_html: str, allegato: tuple[str, bytes] | None = None) -> bool:
    if not _smtp_configured():
        log.warning("SMTP non configurato — email non inviata")
        return False

    msg = MIMEMultipart()
    msg["From"] = config.SMTP_FROM
    msg["To"] = config.REPORT_EMAIL_TO
    msg["Subject"] = oggetto
    msg.attach(MIMEText(corpo_html, "html", "utf-8"))

    if allegato:
        from email.mime.application import MIMEApplication

        nome, data = allegato
        part = MIMEApplication(data)
        part.add_header("Content-Disposition", "attachment", filename=nome)
        msg.attach(part)

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.starttls()
            if config.SMTP_USER:
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)
        log.info("Email inviata a %s", config.REPORT_EMAIL_TO)
        return True
    except Exception as e:
        log.error("Errore invio email: %s", e)
        return False


def genera_report_mensile(anno: int | None = None, mese: int | None = None) -> dict:
    oggi = date.today()
    anno = anno or oggi.year
    mese = mese or oggi.month
    da = date(anno, mese, 1).isoformat()
    ultimo_giorno = calendar.monthrange(anno, mese)[1]
    a = date(anno, mese, ultimo_giorno).isoformat()

    riepilogo = get_riepilogo_ore(da, a)

    with get_db() as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT s.nome, COUNT(*) AS n
            FROM timbrature t
            JOIN sedi s ON s.id = t.sede_id
            WHERE DATE(t.timestamp) BETWEEN ? AND ?
            GROUP BY s.nome ORDER BY n DESC
            """,
            (da, a),
        )
        per_sede = [dict(r) for r in cur.fetchall()]

    return {"periodo": {"da": da, "a": a, "mese": mese, "anno": anno}, "riepilogo": riepilogo, "per_sede": per_sede}


def invia_report_mensile(anno: int | None = None, mese: int | None = None) -> bool:
    report = genera_report_mensile(anno, mese)
    p = report["periodo"]

    righe = "".join(
        f"<tr><td>{r['nome']}</td><td style='text-align:right'>{r['ore']} h</td></tr>"
        for r in report["riepilogo"]
    )
    sedi = "".join(f"<li>{s['nome']}: {s['n']} timbrature</li>" for s in report["per_sede"])

    html = f"""
    <h2>Report presenze — {p['mese']:02d}/{p['anno']}</h2>
    <p>Periodo: {p['da']} → {p['a']}</p>
    <h3>Ore lavorate per dipendente</h3>
    <table border="1" cellpadding="8" cellspacing="0">
        <tr><th>Dipendente</th><th>Ore</th></tr>
        {righe or '<tr><td colspan="2">Nessun dato</td></tr>'}
    </table>
    <h3>Timbrature per sede</h3>
    <ul>{sedi or '<li>Nessun dato</li>'}</ul>
    """

    allegato = _genera_excel(report)
    oggetto = f"Report presenze {p['mese']:02d}/{p['anno']}"
    return invia_email(oggetto, html, allegato)


def _genera_excel(report: dict) -> tuple[str, bytes] | None:
    try:
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "Ore lavorate"
        ws.append(["Dipendente", "Ore"])
        for r in report["riepilogo"]:
            ws.append([r["nome"], r["ore"]])

        ws2 = wb.create_sheet("Per sede")
        ws2.append(["Sede", "Timbrature"])
        for s in report["per_sede"]:
            ws2.append([s["nome"], s["n"]])

        buf = BytesIO()
        wb.save(buf)
        p = report["periodo"]
        nome = f"report_{p['anno']}_{p['mese']:02d}.xlsx"
        return nome, buf.getvalue()
    except ImportError:
        return None
