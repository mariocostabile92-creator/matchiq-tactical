import base64
import io
import os
from datetime import datetime
from typing import List, Optional

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


load_dotenv()
load_dotenv(".env.local", override=False)

router = APIRouter(prefix="/api/video", tags=["video"])

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_VIDEO_MODEL = os.getenv("OPENAI_VIDEO_MODEL", "gpt-4.1-mini").strip()
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

MAX_FRAMES = int(os.getenv("VIDEO_REPORT_MAX_FRAMES", "8"))
MAX_FRAME_CHARS = int(os.getenv("VIDEO_REPORT_MAX_FRAME_CHARS", "900000"))


class VideoReportRequest(BaseModel):
    title: Optional[str] = ""
    category: Optional[str] = "Dilettanti"
    focus: Optional[str] = "Analisi tattica generale"
    notes: Optional[str] = ""
    duration_seconds: Optional[float] = 0
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
    category = _clean_text(data.category, 80) or "Dilettanti"
    focus = _clean_text(data.focus, 160) or "Analisi tattica generale"
    notes = _clean_text(data.notes, 1200) or "Nessuna nota staff inserita."
    duration = round(float(data.duration_seconds or 0), 1)

    return f"""
Analizza questi fotogrammi estratti da una clip calcistica.

Contesto:
- Titolo clip: {title}
- Categoria: {category}
- Focus richiesto: {focus}
- Durata stimata clip: {duration} secondi
- Fotogrammi disponibili: {frame_count}
- Note staff: {notes}

Produci un report tecnico in italiano per un mister di calcio dilettantistico.
Sii utile, concreto e prudente: se un dettaglio non e' visibile, dichiaralo come limite.

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
        raise HTTPException(
            status_code=502,
            detail=f"Errore OpenAI: {detail or response.status_code}"
        )

    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def _build_pdf_base64(title: str, report: str) -> str:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=42)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("MatchIQ Video Analyst", styles["Title"]))
    story.append(Paragraph(_clean_text(title, 180) or "Video Report", styles["Heading2"]))
    story.append(Paragraph(datetime.now().strftime("%d/%m/%Y %H:%M"), styles["Normal"]))
    story.append(Spacer(1, 18))

    for block in str(report or "").split("\n"):
        block = block.strip()
        if not block:
            story.append(Spacer(1, 8))
            continue
        style = styles["Heading3"] if block[:2].strip(".").isdigit() or block.endswith(":") else styles["BodyText"]
        story.append(Paragraph(block.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), style))
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
    pdf_base64 = _build_pdf_base64(title, report)

    return {
        "ok": True,
        "model": OPENAI_VIDEO_MODEL,
        "frames_analyzed": len(frames),
        "title": title,
        "report": report,
        "pdf_base64": pdf_base64,
        "generated_at": datetime.utcnow().isoformat(),
    }
