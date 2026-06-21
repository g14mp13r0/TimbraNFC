"""Export PDF presenze — timbrature e report turni."""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from shared.dates import format_date, format_datetime
from shared.kiosk_i18n import normalize_lang, t


def _pdf_table(headers: list[str], rows: list[list[str]]) -> Table:
    data = [headers] + rows
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A5F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F5F7")]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCD2DA")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _kiosk_logo_image(max_height: float = 22 * mm) -> Image | None:
    from server.app.services.settings_env import kiosk_background_path

    path = kiosk_background_path()
    if not path.is_file():
        return None
    img = Image(str(path))
    iw, ih = float(img.imageWidth), float(img.imageHeight)
    if ih <= 0:
        return None
    scale = min(1.0, max_height / ih)
    img.drawHeight = ih * scale
    img.drawWidth = iw * scale
    img.hAlign = "CENTER"
    img.spaceBefore = 0
    img.spaceAfter = 0
    return img


def _build_pdf(
    *,
    title: str,
    subtitle: str,
    sections: list[tuple[str, list[str], list[list[str]]]],
    landscape_page: bool = False,
) -> bytes:
    buf = io.BytesIO()
    page_size = landscape(A4) if landscape_page else A4
    logo = _kiosk_logo_image()
    generated_at = format_datetime(datetime.now(), seconds=False)
    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=5 * mm if logo else 14 * mm,
        bottomMargin=14 * mm,
        title=title,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PdfTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=colors.HexColor("#0F1B2D"),
        spaceAfter=4,
    )
    sub_style = ParagraphStyle(
        "PdfSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#5C6675"),
        spaceAfter=10,
    )
    section_style = ParagraphStyle(
        "PdfSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor("#1E3A5F"),
        spaceBefore=8,
        spaceAfter=6,
    )

    story: list = []
    if logo:
        story.append(logo)
        story.append(Spacer(1, 8))
    story.extend([
        Paragraph(title, title_style),
        Paragraph(subtitle, sub_style),
    ])
    for section_title, headers, rows in sections:
        story.append(Paragraph(section_title, section_style))
        if rows:
            story.append(_pdf_table(headers, rows))
        else:
            story.append(Paragraph("—", sub_style))
        story.append(Spacer(1, 8))

    def _draw_generated_at(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#5C6675"))
        x = doc_obj.pagesize[0] - doc_obj.rightMargin
        y = doc_obj.pagesize[1] - 8 * mm
        canvas.drawRightString(x, y, generated_at)
        canvas.restoreState()

    doc.build(story, onFirstPage=_draw_generated_at, onLaterPages=_draw_generated_at)
    return buf.getvalue()


def _period_subtitle(da: str, a: str, lang: str | None = None) -> str:
    code = normalize_lang(lang)
    period = t("period_label", code).rstrip(":").rstrip("：")
    return f"{period}: {format_date(da)} → {format_date(a)}"


def sort_timbrature_rows(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (r["data"], r["dipendente"].lower(), r["ora"], r["id"]))


def timbrature_pdf(rows: list[dict], da: str, a: str, lang: str | None = None) -> bytes:
    code = normalize_lang(lang)
    ordered = sort_timbrature_rows(rows)
    headers = [
        t("col_date", code),
        t("col_time", code),
        t("lbl_employee", code),
        t("col_badge", code),
        t("col_department", code),
        t("col_action", code),
        t("col_terminal", code),
        t("col_received", code),
    ]
    table_rows = [
        [
            format_date(r["data"]),
            r["ora"],
            r["dipendente"],
            r["badge_uid"],
            r["reparto"],
            r["azione_label"],
            r["dispositivo"],
            format_datetime(r["ricevuto_il"]) if r["ricevuto_il"] != "—" else "—",
        ]
        for r in ordered
    ]
    return _build_pdf(
        title=f"TimbraNFC — {t('nav_timbrature', code)}",
        subtitle=_period_subtitle(da, a, code),
        sections=[(t("nav_timbrature", code), headers, table_rows)],
        landscape_page=True,
    )


def report_turni_pdf(data: dict, da: str, a: str, lang: str | None = None) -> bytes:
    code = normalize_lang(lang)
    riepilogo = sorted(data.get("riepilogo", []), key=lambda r: r["dipendente"].lower())
    turni = sorted(
        data.get("turni", []),
        key=lambda r: (r["dipendente"].lower(), r["data"], r["ora_inizio"]),
    )

    summary_headers = [
        t("lbl_employee", code),
        t("col_total_time", code),
    ]
    summary_rows = [
        [r["dipendente"], r["durata_totale"]]
        for r in riepilogo
    ]

    detail_headers = [
        t("lbl_employee", code),
        t("col_date", code),
        t("shift_start", code),
        t("shift_end", code),
        t("col_total_time", code),
    ]
    detail_rows = []
    for row in turni:
        if row.get("aperto"):
            fine = t("shift_in_progress", code)
        else:
            fine = row.get("ora_fine") or "—"
        detail_rows.append([
            row["dipendente"],
            format_date(row["data"]),
            row["ora_inizio"],
            fine,
            row["durata"],
        ])

    return _build_pdf(
        title=f"TimbraNFC — {t('nav_report', code)}",
        subtitle=_period_subtitle(da, a, code),
        sections=[
            (t("report_summary", code), summary_headers, summary_rows),
            (t("report_detail", code), detail_headers, detail_rows),
        ],
        landscape_page=False,
    )
