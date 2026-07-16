from __future__ import annotations

import html
import io
import re
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def report_pdf_filename(report: Dict[str, Any]) -> str:
    title = str(report.get("title") or "matchiq-video-report").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", title).strip("-") or "matchiq-video-report"
    return f"{slug[:100]}.pdf"


def _paragraph(value: Any, style: ParagraphStyle) -> Paragraph:
    safe = html.escape(str(value or "")).replace("\n", "<br/>")
    return Paragraph(safe, style)


def _draw_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d8e4ef"))
    canvas.setLineWidth(0.4)
    canvas.line(doc.leftMargin, 30, A4[0] - doc.rightMargin, 30)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.setFillColor(colors.HexColor("#0b8f6a"))
    canvas.drawString(doc.leftMargin, 18, "MatchIQ Video AI")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawRightString(A4[0] - doc.rightMargin, 18, f"Pagina {doc.page}")
    canvas.restoreState()


def build_evidence_report_pdf(report: Dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=38,
        leftMargin=38,
        topMargin=34,
        bottomMargin=42,
        title=str(report.get("title") or "Report tecnico Video AI"),
        author="MatchIQ Coach AI",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="MatchIQTitle",
        parent=styles["Title"],
        textColor=colors.white,
        fontSize=21,
        leading=25,
        alignment=0,
        spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="MatchIQKicker",
        parent=styles["Normal"],
        textColor=colors.HexColor("#00f5a0"),
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
    ))
    styles.add(ParagraphStyle(
        name="MatchIQHeading",
        parent=styles["Heading3"],
        textColor=colors.HexColor("#092642"),
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        spaceBefore=9,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="MatchIQBody",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12.2,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="MatchIQSmall",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#475569"),
    ))

    title = str(report.get("title") or "Report tecnico Video AI")
    story = []
    cover = Table([[[
        Paragraph("MATCHIQ VIDEO INTELLIGENCE", styles["MatchIQKicker"]),
        _paragraph(title, styles["MatchIQTitle"]),
        Paragraph(
            "Documento tecnico basato esclusivamente sulle evidenze revisionate dallo staff.",
            ParagraphStyle("MatchIQCoverBody", parent=styles["MatchIQSmall"], textColor=colors.HexColor("#dbeafe")),
        ),
    ]]], colWidths=[A4[0] - doc.leftMargin - doc.rightMargin])
    cover.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#07101f")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#0bbf8a")),
        ("LEFTPADDING", (0, 0), (-1, -1), 18),
        ("RIGHTPADDING", (0, 0), (-1, -1), 18),
        ("TOPPADDING", (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
    ]))
    story.extend([cover, Spacer(1, 10)])

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    summary_rows = [
        ["Generato", report.get("generated_at") or "-"],
        ["Evidenze accettate", summary.get("accepted_evidences", 0)],
        ["Confermate / corrette", f"{summary.get('confirmed', 0)} / {summary.get('corrected', 0)}"],
        ["Pendenti in appendice", summary.get("pending_appendix", 0)],
    ]
    table = Table(
        [[_paragraph(label, styles["MatchIQSmall"]), _paragraph(value, styles["MatchIQSmall"])] for label, value in summary_rows],
        colWidths=[125, A4[0] - doc.leftMargin - doc.rightMargin - 125],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8fff7")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([table, Spacer(1, 7), _paragraph(report.get("evidence_policy"), styles["MatchIQSmall"])])

    for section in report.get("sections") or []:
        story.append(_paragraph(section.get("title") or "Evidenze", styles["MatchIQHeading"]))
        for finding in section.get("findings") or []:
            heading = f"{finding.get('timecode') or '--:--'} - {finding.get('title') or 'Osservazione'}"
            story.append(_paragraph(heading, styles["MatchIQBody"]))
            if finding.get("observation"):
                story.append(_paragraph(finding.get("observation"), styles["MatchIQBody"]))
            if finding.get("interpretation"):
                story.append(_paragraph(f"Lettura: {finding.get('interpretation')}", styles["MatchIQSmall"]))
            if finding.get("staff_correction"):
                story.append(_paragraph(f"Correzione staff: {finding.get('staff_correction')}", styles["MatchIQSmall"]))

    pending = report.get("pending_appendix") or []
    if pending:
        story.append(_paragraph("Appendice - evidenze ancora da verificare", styles["MatchIQHeading"]))
        for item in pending:
            story.append(_paragraph(
                f"{item.get('timecode') or '--:--'} - {item.get('title') or 'Evidenza'}: {item.get('reason') or ''}",
                styles["MatchIQSmall"],
            ))

    limitations = report.get("limitations") or []
    if limitations:
        story.append(_paragraph("Limiti dell'analisi", styles["MatchIQHeading"]))
        for item in limitations:
            story.append(_paragraph(f"- {item}", styles["MatchIQSmall"]))

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    payload = buffer.getvalue()
    if not payload.startswith(b"%PDF"):
        raise RuntimeError("Il documento PDF generato non e valido")
    return payload
