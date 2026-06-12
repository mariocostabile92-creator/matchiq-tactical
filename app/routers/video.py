import base64
import html
import io
import os
from datetime import datetime
from typing import List, Optional

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


load_dotenv()
load_dotenv(".env.local", override=False)

router = APIRouter(prefix="/api/video", tags=["video"])

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_VIDEO_MODEL = os.getenv("OPENAI_VIDEO_MODEL", "gpt-4.1-mini").strip()
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

MAX_FRAMES = int(os.getenv("VIDEO_REPORT_MAX_FRAMES", "6"))
MAX_FRAME_CHARS = int(os.getenv("VIDEO_REPORT_MAX_FRAME_CHARS", "900000"))


class VideoReportRequest(BaseModel):
    title: Optional[str] = ""
    club_name: Optional[str] = ""
    category: Optional[str] = "Dilettanti"
    focus: Optional[str] = "Analisi tattica generale"
    observed_team: Optional[str] = ""
    report_style: Optional[str] = "Report staff completo"
    notes: Optional[str] = ""
    duration_seconds: Optional[float] = 0
    frame_times: List[float] = Field(default_factory=list)
    frames: List[str]


def _clean_text(value: str, limit: int = 1200) -> str:
    value = str(value or "").strip()
    return value[:limit]


def _sanitize_frames(frames: List[str]) -> List[str]:
    safe_frames = []

    for frame in frames[:MAX_FRAMES]:
        frame = str(frame or "").strip()

        if not frame.startswith("data:image/"):
            continue

        if len(frame) > MAX_FRAME_CHARS:
            continue

        safe_frames.append(frame)

    return safe_frames


def _build_prompt(data: VideoReportRequest, frame_count: int) -> str:
    title = _clean_text(data.title, 180) or "Video partita"
    club_name = _clean_text(data.club_name, 160) or "Non specificata"
    category = _clean_text(data.category, 80) or "Dilettanti"
    focus = _clean_text(data.focus, 160) or "Analisi tattica generale"
    observed_team = _clean_text(data.observed_team, 160) or "Non specificata"
    report_style = _clean_text(data.report_style, 120) or "Report staff completo"
    notes = _clean_text(data.notes, 1200) or "Nessuna nota staff inserita."
    duration = round(float(data.duration_seconds or 0), 1)
    frame_times = ", ".join(_format_seconds(t) for t in (data.frame_times or [])[:frame_count]) or "non disponibili"

    return f"""
Analizza questi fotogrammi estratti da una clip calcistica.

Contesto:
- Titolo clip: {title}
- Societa o squadra: {club_name}
- Categoria: {category}
- Focus richiesto: {focus}
- Squadra osservata: {observed_team}
- Stile report richiesto: {report_style}
- Durata stimata clip: {duration} secondi
- Fotogrammi disponibili: {frame_count}
- Minuti indicativi dei fotogrammi: {frame_times}
- Note staff: {notes}

Produci un report tecnico in italiano per un mister di calcio dilettantistico.
Sii utile, concreto e prudente: se un dettaglio non e' visibile, dichiaralo come limite.
Usa i minuti indicativi quando commenti un episodio, senza inventare cronologia non visibile.

Formato richiesto:
1. Sintesi video
2. Fase offensiva
3. Fase difensiva
4. Pressing e transizioni
5. Errori o rischi ricorrenti
6. Giocatori o zone coinvolte, solo se visibili
7. Indicazioni per il prossimo allenamento
8. Messaggio breve per la squadra
9. Limiti dell'analisi video
""".strip()


def _format_seconds(value: float) -> str:
    try:
        total = max(0, int(round(float(value or 0))))
    except Exception:
        total = 0
    minutes = total // 60
    seconds = total % 60
    return f"{minutes:02d}:{seconds:02d}"


def _call_openai(prompt: str, frames: List[str]) -> str:
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY non configurata"
        )

    content = [{"type": "text", "text": prompt}]

    for frame in frames:
        content.append({
            "type": "image_url",
            "image_url": {"url": frame}
        })

    payload = {
        "model": OPENAI_VIDEO_MODEL,
        "temperature": 0.2,
        "max_tokens": 1800,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Sei MatchIQ Video Analyst, un assistente per staff tecnici. "
                    "Analizzi clip calcistiche da fotogrammi e produci report "
                    "pratici, prudenti e orientati all'allenamento."
                )
            },
            {
                "role": "user",
                "content": content
            }
        ]
    }

    response = requests.post(
        OPENAI_API_URL,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=90,
    )

    if response.status_code >= 400:
        try:
            detail = response.json().get("error", {}).get("message")
        except Exception:
            detail = response.text

        detail_text = str(detail or "")
        quota_markers = [
            "quota",
            "billing",
            "credits",
            "insufficient_quota",
            "exceeded your current quota",
        ]

        if any(marker in detail_text.lower() for marker in quota_markers):
            raise HTTPException(
                status_code=402,
                detail=(
                    "Credito o quota OpenAI non disponibile. "
                    "Aggiungi credito API o controlla il limite di spesa su OpenAI Platform."
                )
            )

        raise HTTPException(
            status_code=502,
            detail=f"Errore OpenAI: {detail or response.status_code}"
        )

    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def _build_pdf_base64(title: str, report: str, data: VideoReportRequest, frame_count: int) -> str:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=42)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="MatchIQTitle",
        parent=styles["Title"],
        textColor=colors.HexColor("#06111c"),
        fontSize=21,
        leading=25,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="MatchIQKicker",
        parent=styles["Normal"],
        textColor=colors.HexColor("#0b8f6a"),
        fontSize=9,
        leading=12,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="MatchIQHeading",
        parent=styles["Heading3"],
        textColor=colors.HexColor("#0b2b4f"),
        fontSize=11,
        leading=14,
        spaceBefore=8,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="MatchIQBody",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#222222"),
    ))
    story = []

    story.append(Paragraph("MATCHIQ VIDEO ANALYST", styles["MatchIQKicker"]))
    story.append(Paragraph(html.escape(_clean_text(title, 180) or "Video Report"), styles["MatchIQTitle"]))

    summary_rows = [
        ["Data", datetime.now().strftime("%d/%m/%Y %H:%M")],
        ["Societa / squadra", _clean_text(data.club_name, 160) or "-"],
        ["Categoria", _clean_text(data.category, 80) or "-"],
        ["Focus", _clean_text(data.focus, 120) or "-"],
        ["Squadra osservata", _clean_text(data.observed_team, 160) or "-"],
        ["Stile report", _clean_text(data.report_style, 120) or "-"],
        ["Fotogrammi analizzati", str(frame_count)],
    ]
    summary = Table(summary_rows, colWidths=[112, 360])
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8fff6")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#075f4a")),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#1d2433")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#c9ded8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary)
    story.append(Spacer(1, 18))

    for block in str(report or "").split("\n"):
        block = block.strip()
        if not block:
            story.append(Spacer(1, 8))
            continue
        style = styles["MatchIQHeading"] if block[:2].strip(".").isdigit() or block.endswith(":") else styles["MatchIQBody"]
        story.append(Paragraph(html.escape(block), style))
        story.append(Spacer(1, 6))

    doc.build(story)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


@router.post("/analyze")
def analyze_video_clip(data: VideoReportRequest):
    frames = _sanitize_frames(data.frames)

    if len(frames) < 2:
        raise HTTPException(
            status_code=400,
            detail="Servono almeno 2 fotogrammi validi per analizzare la clip"
        )

    prompt = _build_prompt(data, len(frames))
    report = _call_openai(prompt, frames)
    title = _clean_text(data.title, 180) or "Video Report MatchIQ"
    pdf_base64 = _build_pdf_base64(title, report, data, len(frames))

    return {
        "ok": True,
        "model": OPENAI_VIDEO_MODEL,
        "frames_analyzed": len(frames),
        "title": title,
        "report": report,
        "pdf_base64": pdf_base64,
        "generated_at": datetime.utcnow().isoformat(),
    }
