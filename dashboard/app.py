import csv
import io
import sys
from datetime import date
from pathlib import Path

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import generate_password_hash

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from audit import log_audit
from auth import (
    RUOLI,
    autentica,
    crea_utente_default,
    ha_permesso,
    login_required,
    permesso_required,
    utente_corrente,
)
from db import get_db, get_riepilogo_ore, init_db
from notifications import invia_report_mensile
from sync import esegui_sync_completa, stato_sync

app = Flask(__name__)
app.secret_key = config.DASHBOARD_SECRET


@app.context_processor
def inject_auth():
    ruolo = session.get("ruolo", "")
    return {
        "ruolo": ruolo,
        "utente_nome": session.get("nome", ""),
        "ha_permesso": lambda p: ha_permesso(ruolo, p),
    }


def _get_sedi():
    with get_db() as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM sedi WHERE attiva=1 ORDER BY nome")
        return [dict(r) for r in cur.fetchall()]


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = autentica(request.form.get("username", ""), request.form.get("password", ""))
        if user:
            session["logged_in"] = True
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["ruolo"] = user["ruolo"]
            session["nome"] = user["nome"]
            log_audit("login", "dashboard", utente=user["username"])
            return redirect(url_for("index"))
        flash("Credenziali non valide", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
@permesso_required("index")
def index():
    oggi = date.today().isoformat()
    with get_db() as con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) AS n FROM dipendenti WHERE attivo=1")
        n_dip = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) AS n FROM timbrature WHERE DATE(timestamp)=?", (oggi,))
        n_timb = cur.fetchone()["n"]
        cur.execute(
            """
            SELECT t.timestamp, t.tipo, d.nome, d.cognome, s.nome AS sede_nome
            FROM timbrature t
            JOIN dipendenti d ON d.id = t.dipendente_id
            LEFT JOIN sedi s ON s.id = t.sede_id
            ORDER BY t.timestamp DESC LIMIT 10
            """
        )
        recenti = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT COUNT(*) AS n FROM sedi WHERE attiva=1")
        n_sedi = cur.fetchone()["n"]
    return render_template("index.html", n_dip=n_dip, n_timb=n_timb, n_sedi=n_sedi, recenti=recenti, oggi=oggi)


@app.route("/dipendenti", methods=["GET", "POST"])
@login_required
@permesso_required("dipendenti")
def dipendenti():
    if request.method == "POST":
        action = request.form.get("action")
        with get_db() as con:
            cur = con.cursor()
            if action == "add":
                sede_id = request.form.get("sede_id") or None
                cur.execute(
                    """
                    INSERT INTO dipendenti (nome, cognome, badge_uid, email, reparto, sede_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request.form["nome"].strip(),
                        request.form["cognome"].strip(),
                        request.form["badge_uid"].strip().upper(),
                        request.form.get("email", "").strip() or None,
                        request.form.get("reparto", "").strip() or None,
                        sede_id,
                    ),
                )
                log_audit("creazione", "dipendenti", cur.lastrowid, utente=utente_corrente())
                flash("Dipendente aggiunto", "success")
            elif action == "toggle":
                cur.execute(
                    "UPDATE dipendenti SET attivo = CASE attivo WHEN 1 THEN 0 ELSE 1 END WHERE id=?",
                    (request.form["id"],),
                )
            elif action == "delete":
                cur.execute("DELETE FROM dipendenti WHERE id=?", (request.form["id"],))
                log_audit("eliminazione", "dipendenti", int(request.form["id"]), utente=utente_corrente())

    with get_db() as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT d.*, s.nome AS sede_nome FROM dipendenti d
            LEFT JOIN sedi s ON s.id = d.sede_id
            ORDER BY d.cognome, d.nome
            """
        )
        lista = [dict(r) for r in cur.fetchall()]
    return render_template("dipendenti.html", dipendenti=lista, sedi=_get_sedi())


@app.route("/sedi", methods=["GET", "POST"])
@login_required
@permesso_required("sedi")
def sedi():
    if request.method == "POST":
        action = request.form.get("action")
        with get_db() as con:
            cur = con.cursor()
            if action == "add":
                cur.execute(
                    "INSERT INTO sedi (nome, codice, indirizzo) VALUES (?, ?, ?)",
                    (
                        request.form["nome"].strip(),
                        request.form["codice"].strip().upper(),
                        request.form.get("indirizzo", "").strip() or None,
                    ),
                )
                log_audit("creazione", "sedi", cur.lastrowid, utente=utente_corrente())
                flash("Sede aggiunta", "success")
            elif action == "toggle":
                cur.execute(
                    "UPDATE sedi SET attiva = CASE attiva WHEN 1 THEN 0 ELSE 1 END WHERE id=?",
                    (request.form["id"],),
                )

    with get_db() as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM sedi ORDER BY nome")
        lista = [dict(r) for r in cur.fetchall()]
    return render_template("sedi.html", sedi=lista)


@app.route("/report")
@login_required
@permesso_required("report")
def report():
    da = request.args.get("da", date.today().replace(day=1).isoformat())
    a = request.args.get("a", date.today().isoformat())
    dip_id = request.args.get("dipendente_id", "")
    sede_id = request.args.get("sede_id", "")

    with get_db() as con:
        cur = con.cursor()
        cur.execute("SELECT id, nome, cognome FROM dipendenti WHERE attivo=1 ORDER BY cognome")
        dipendenti = [dict(r) for r in cur.fetchall()]

        query = """
            SELECT t.id, t.timestamp, t.tipo, d.nome, d.cognome, d.id AS dipendente_id,
                   s.nome AS sede_nome
            FROM timbrature t
            JOIN dipendenti d ON d.id = t.dipendente_id
            LEFT JOIN sedi s ON s.id = t.sede_id
            WHERE DATE(t.timestamp) BETWEEN ? AND ?
        """
        params: list = [da, a]
        if dip_id:
            query += " AND d.id=?"
            params.append(dip_id)
        if sede_id:
            query += " AND t.sede_id=?"
            params.append(sede_id)
        query += " ORDER BY t.timestamp DESC"
        cur.execute(query, params)
        timbrature = [dict(r) for r in cur.fetchall()]

    riepilogo = get_riepilogo_ore(da, a, int(sede_id) if sede_id else None, int(dip_id) if dip_id else None)

    return render_template(
        "report.html",
        timbrature=timbrature,
        riepilogo=riepilogo,
        dipendenti=dipendenti,
        sedi=_get_sedi(),
        da=da,
        a=a,
        dipendente_id=dip_id,
        sede_id=sede_id,
    )


@app.route("/audit")
@login_required
@permesso_required("audit")
def audit():
    with get_db() as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 200")
        logs = [dict(r) for r in cur.fetchall()]
    return render_template("audit.html", logs=logs)


@app.route("/utenti", methods=["GET", "POST"])
@login_required
@permesso_required("utenti")
def utenti():
    if request.method == "POST":
        action = request.form.get("action")
        with get_db() as con:
            cur = con.cursor()
            if action == "add":
                cur.execute(
                    """
                    INSERT INTO utenti (username, password_hash, ruolo, nome)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        request.form["username"].strip().lower(),
                        generate_password_hash(request.form["password"]),
                        request.form["ruolo"],
                        request.form["nome"].strip(),
                    ),
                )
                log_audit("creazione", "utenti", cur.lastrowid, utente=utente_corrente())
                flash("Utente creato", "success")
            elif action == "toggle":
                uid = int(request.form["id"])
                if uid != session.get("user_id"):
                    cur.execute(
                        "UPDATE utenti SET attivo = CASE attivo WHEN 1 THEN 0 ELSE 1 END WHERE id=?",
                        (uid,),
                    )
            elif action == "reset_password":
                cur.execute(
                    "UPDATE utenti SET password_hash=? WHERE id=?",
                    (generate_password_hash(request.form["password"]), request.form["id"]),
                )
                flash("Password aggiornata", "success")

    with get_db() as con:
        cur = con.cursor()
        cur.execute("SELECT id, username, ruolo, nome, attivo, creato_il FROM utenti ORDER BY username")
        lista = [dict(r) for r in cur.fetchall()]
    return render_template("utenti.html", utenti=lista, ruoli=RUOLI)


@app.route("/sync", methods=["GET", "POST"])
@login_required
@permesso_required("sync")
def sync_page():
    risultato = None
    if request.method == "POST":
        risultato = esegui_sync_completa()
        flash(risultato.get("push", {}).get("msg", "Sync eseguita"), "success")
    stato = stato_sync()
    return render_template("sync.html", stato=stato, risultato=risultato)


@app.route("/report/invia-email", methods=["POST"])
@login_required
@permesso_required("email")
def invia_email_report():
    mese = int(request.form.get("mese", date.today().month))
    anno = int(request.form.get("anno", date.today().year))
    if invia_report_mensile(anno, mese):
        flash(f"Report {mese:02d}/{anno} inviato a {config.REPORT_EMAIL_TO}", "success")
        log_audit("invio_email", "report", dettagli=f"{mese:02d}/{anno}", utente=utente_corrente())
    else:
        flash("Invio fallito — verifica configurazione SMTP", "error")
    return redirect(url_for("report"))


@app.route("/export/<fmt>")
@login_required
@permesso_required("export")
def export(fmt):
    da = request.args.get("da", date.today().replace(day=1).isoformat())
    a = request.args.get("a", date.today().isoformat())
    dip_id = request.args.get("dipendente_id", "")
    sede_id = request.args.get("sede_id", "")

    with get_db() as con:
        cur = con.cursor()
        query = """
            SELECT t.timestamp, t.tipo, d.nome, d.cognome, d.badge_uid, d.reparto, s.nome AS sede
            FROM timbrature t
            JOIN dipendenti d ON d.id = t.dipendente_id
            LEFT JOIN sedi s ON s.id = t.sede_id
            WHERE DATE(t.timestamp) BETWEEN ? AND ?
        """
        params: list = [da, a]
        if dip_id:
            query += " AND d.id=?"
            params.append(dip_id)
        if sede_id:
            query += " AND t.sede_id=?"
            params.append(sede_id)
        query += " ORDER BY t.timestamp"
        cur.execute(query, params)
        rows = [dict(r) for r in cur.fetchall()]

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Data/Ora", "Tipo", "Nome", "Cognome", "Badge UID", "Reparto", "Sede"])
        for r in rows:
            writer.writerow(
                [r["timestamp"], r["tipo"], r["nome"], r["cognome"], r["badge_uid"], r["reparto"] or "", r["sede"] or ""]
            )
        from flask import Response

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=timbrature_{da}_{a}.csv"},
        )

    if fmt == "xlsx":
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "Timbrature"
        ws.append(["Data/Ora", "Tipo", "Nome", "Cognome", "Badge UID", "Reparto", "Sede"])
        for r in rows:
            ws.append(
                [r["timestamp"], r["tipo"], r["nome"], r["cognome"], r["badge_uid"], r["reparto"] or "", r["sede"] or ""]
            )
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        from flask import send_file

        return send_file(
            buf,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"timbrature_{da}_{a}.xlsx",
        )

    return "Formato non supportato", 400


@app.route("/api/stats/giornaliere")
@login_required
@permesso_required("index")
def stats_giornaliere():
    da = request.args.get("da", date.today().replace(day=1).isoformat())
    a = request.args.get("a", date.today().isoformat())
    sede_id = request.args.get("sede_id", "")

    query = """
        SELECT DATE(timestamp) AS giorno, COUNT(*) AS n
        FROM timbrature WHERE DATE(timestamp) BETWEEN ? AND ?
    """
    params: list = [da, a]
    if sede_id:
        query += " AND sede_id=?"
        params.append(sede_id)
    query += " GROUP BY DATE(timestamp) ORDER BY giorno"

    with get_db() as con:
        cur = con.cursor()
        cur.execute(query, params)
        data = [dict(r) for r in cur.fetchall()]
    return jsonify(data)


if __name__ == "__main__":
    init_db()
    crea_utente_default()
    app.run(host=config.DASHBOARD_HOST, port=config.DASHBOARD_PORT, debug=False)
