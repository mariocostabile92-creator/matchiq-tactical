import base64
import html
import io
import json
import os
from datetime import datetime
from typing import List, Optional

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from database import can_use_feature, delete_video_report, get_plan_limits, get_video_reports, save_video_report, track_api_usage
from usage_guard import get_optional_user, require_user


load_dotenv()
load_dotenv(".env.local", override=False)

router = APIRouter(prefix="/api/video", tags=["video"])

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_VIDEO_MODEL = os.getenv("OPENAI_VIDEO_MODEL", "gpt-4.1-mini").strip()
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

MAX_FRAMES = int(os.getenv("VIDEO_REPORT_MAX_FRAMES", "6"))
MAX_SELECTION_FRAMES = int(os.getenv("VIDEO_SELECTION_MAX_FRAMES", "16"))
MAX_FRAME_CHARS = int(os.getenv("VIDEO_REPORT_MAX_FRAME_CHARS", "900000"))


class VideoReportRequest(BaseModel):
    title: Optional[str] = ""
    club_name: Optional[str] = ""
    category: Optional[str] = "Dilettanti"
    focus: Optional[str] = "Analisi tattica generale"
    observed_team: Optional[str] = ""
    home_team: Optional[str] = ""
    away_team: Optional[str] = ""
    home_formation: Optional[str] = ""
    away_formation: Optional[str] = ""
    lineup_notes: Optional[str] = ""
    report_style: Optional[str] = "Report staff completo"
    notes: Optional[str] = ""
    duration_seconds: Optional[float] = 0
    frame_times: List[float] = Field(default_factory=list)
    frame_meta: List[dict] = Field(default_factory=list)
    tactical_lines: List[dict] = Field(default_factory=list)
    frames: List[str]


class FrameSelectionRequest(BaseModel):
    focus: Optional[str] = "Analisi tattica generale"
    observed_team: Optional[str] = ""
    home_team: Optional[str] = ""
    away_team: Optional[str] = ""
    home_formation: Optional[str] = ""
    away_formation: Optional[str] = ""
    lineup_notes: Optional[str] = ""
    duration_seconds: Optional[float] = 0
    frame_times: List[float] = Field(default_factory=list)
    frame_meta: List[dict] = Field(default_factory=list)
    desired_count: Optional[int] = 6
    frames: List[str]


class CloudVideoReportRequest(BaseModel):
    title: Optional[str] = ""
    club_name: Optional[str] = ""
    category: Optional[str] = ""
    focus: Optional[str] = ""
    observed_team: Optional[str] = ""
    report_style: Optional[str] = ""
    frames_analyzed: Optional[int] = 0
    report: Optional[str] = ""
    pdf_base64: Optional[str] = ""
    payload: Optional[dict] = Field(default_factory=dict)


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


def _sanitize_selection_frames(frames: List[str]) -> List[str]:
    safe_frames = []

    for frame in frames[:MAX_SELECTION_FRAMES]:
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
    home_team = _clean_text(data.home_team, 120) or "Non specificata"
    away_team = _clean_text(data.away_team, 120) or "Non specificata"
    home_formation = _clean_text(data.home_formation, 40) or "Non indicato"
    away_formation = _clean_text(data.away_formation, 40) or "Non indicato"
    lineup_notes = _clean_text(data.lineup_notes, 1400) or "Non inserite"
    report_style = _clean_text(data.report_style, 120) or "Report staff completo"
    notes = _clean_text(data.notes, 1200) or "Nessuna nota staff inserita."
    duration = round(float(data.duration_seconds or 0), 1)
    frame_times = ", ".join(_format_seconds(t) for t in (data.frame_times or [])[:frame_count]) or "non disponibili"
    frame_meta = _format_frame_meta(data.frame_meta, frame_count)
    tactical_lines = _format_tactical_lines(data.tactical_lines)

    return f"""
Analizza questi fotogrammi estratti da una clip calcistica.

Contesto:
- Titolo clip: {title}
- Societa o squadra: {club_name}
- Categoria: {category}
- Focus richiesto: {focus}
- Squadra osservata: {observed_team}
- Squadra casa: {home_team}
- Modulo casa: {home_formation}
- Squadra trasferta: {away_team}
- Modulo trasferta: {away_formation}
- Formazioni o numeri inseriti dallo staff: {lineup_notes}
- Stile report richiesto: {report_style}
- Durata stimata clip: {duration} secondi
- Fotogrammi disponibili: {frame_count}
- Minuti indicativi dei fotogrammi: {frame_times}
- Motivo selezione fotogrammi: {frame_meta}
- Note staff: {notes}
- Linee tattiche selezionate dall'utente: {tactical_lines}

Produci un report tecnico in italiano per un mister di calcio dilettantistico.
Sii utile, concreto e prudente: se un dettaglio non e' visibile, dichiaralo come limite.
Usa i minuti indicativi quando commenti un episodio, senza inventare cronologia non visibile.
Se sono presenti linee tattiche selezionate, usale come priorita di lettura: commenta reparto, fase, distanze e spazio tra linee senza fingere misurazioni automatiche.
Se sono presenti squadre, moduli o formazioni, usali per associare meglio ruoli e reparti. Non inventare nomi di giocatori non forniti; se un numero o volto non e' leggibile, dichiaralo.
Per il focus richiesto, commenta prima i fotogrammi coerenti con quella fase e spiega se qualche frame e' poco adatto alla lettura tattica.
La sezione 9 deve essere concreta e breve: indica solo i dati mancanti o le verifiche utili per migliorare la prossima analisi. Non scrivere frasi da assistente come "se desideri posso approfondire" e non chiudere con separatori o inviti generici.

Formato richiesto:
1. Sintesi video
2. Fase offensiva
3. Fase difensiva
4. Pressing e transizioni
5. Errori o rischi ricorrenti
6. Giocatori o zone coinvolte, solo se visibili
7. Indicazioni per il prossimo allenamento
8. Messaggio breve per la squadra
9. Limiti dell'analisi video e prossima verifica
""".strip()


def _format_tactical_lines(lines: List[dict]) -> str:
    safe_lines = []
    for item in (lines or [])[:12]:
        phase = _clean_text(item.get("phase", ""), 80) or "Linea tattica"
        team = _clean_text(item.get("team", ""), 80) or "Squadra osservata"
        time_label = _clean_text(item.get("time_label", ""), 20)
        frame_label = _clean_text(item.get("frame_label", ""), 30)
        if not time_label:
            time_label = _format_seconds(item.get("time_seconds", 0))
        frame_prefix = f"{frame_label}, " if frame_label else ""
        safe_lines.append(f"{frame_prefix}{phase} - {team} a {time_label}")
    return "; ".join(safe_lines) if safe_lines else "nessuna linea selezionata"


def _format_frame_meta(items: List[dict], frame_count: int) -> str:
    safe_items = []
    for index, item in enumerate((items or [])[:frame_count]):
        label = _clean_text(item.get("label", ""), 60) or "lettura tattica"
        score = item.get("score", "")
        green = item.get("green_ratio", "")
        try:
            score_label = str(round(float(score), 1))
        except Exception:
            score_label = "-"
        safe_items.append(f"Frame {index + 1}: {label}, score {score_label}, campo {green}")
    return "; ".join(safe_items) if safe_items else "non disponibili"


def _safe_unit(value, fallback: float = 0.5) -> float:
    try:
        number = float(value)
    except Exception:
        number = fallback
    return max(0.0, min(1.0, number))


def _safe_color(value: str, fallback: str = "#ff4058") -> str:
    value = str(value or "").strip()
    if len(value) == 7 and value.startswith("#"):
        try:
            int(value[1:], 16)
            return value
        except Exception:
            return fallback
    return fallback


def _normalize_line_suggestions(items: List[dict]) -> List[dict]:
    safe_lines = []
    for item in (items or [])[:2]:
        start = item.get("start") or {}
        end = item.get("end") or {}
        safe_lines.append({
            "phase": _clean_text(item.get("phase", ""), 80) or "Linea tattica",
            "team": _clean_text(item.get("team", ""), 80) or "Squadra osservata",
            "color": _safe_color(item.get("color"), "#ff4058"),
            "confidence": item.get("confidence"),
            "reason": _clean_text(item.get("reason", ""), 220),
            "start": {
                "x": _safe_unit(start.get("x"), 0.25),
                "y": _safe_unit(start.get("y"), 0.5),
            },
            "end": {
                "x": _safe_unit(end.get("x"), 0.75),
                "y": _safe_unit(end.get("y"), 0.5),
            },
        })
    return safe_lines


def _sanitize_video_report(report: str) -> str:
    blocked_prefixes = (
        "se desideri",
        "se vuoi",
        "posso approfondire",
        "fammi sapere",
        "resto a disposizione",
    )
    clean_lines = []

    for raw_line in str(report or "").splitlines():
        line = raw_line.strip()
        lowered = line.lower()
        if line in {"---", "--", "***"}:
            continue
        if any(lowered.startswith(prefix) for prefix in blocked_prefixes):
            continue
        clean_lines.append(raw_line.rstrip())

    compact = "\n".join(clean_lines).strip()
    while "\n\n\n" in compact:
        compact = compact.replace("\n\n\n", "\n\n")
    return compact


def _format_seconds(value: float) -> str:
    try:
        total = max(0, int(round(float(value or 0))))
    except Exception:
        total = 0
    minutes = total // 60
    seconds = total % 60
    return f"{minutes:02d}:{seconds:02d}"


def _extract_json_object(value: str) -> dict:
    text = str(value or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
    return {}


def _build_frame_selection_prompt(data: FrameSelectionRequest, frame_count: int) -> str:
    focus = _clean_text(data.focus, 160) or "Analisi tattica generale"
    observed_team = _clean_text(data.observed_team, 160) or "Non specificata"
    home_team = _clean_text(data.home_team, 120) or "Non specificata"
    away_team = _clean_text(data.away_team, 120) or "Non specificata"
    home_formation = _clean_text(data.home_formation, 40) or "Non indicato"
    away_formation = _clean_text(data.away_formation, 40) or "Non indicato"
    lineup_notes = _clean_text(data.lineup_notes, 1400) or "Non inserite"
    desired_count = max(2, min(MAX_FRAMES, int(data.desired_count or MAX_FRAMES)))
    frame_times = ", ".join(
        f"index {idx}: {_format_seconds(t)}"
        for idx, t in enumerate((data.frame_times or [])[:frame_count])
    ) or "non disponibili"
    local_meta = _format_frame_meta(data.frame_meta, frame_count)

    return f"""
Seleziona i migliori fotogrammi per analisi calcistica.

Obiettivo:
- Focus richiesto: {focus}
- Fotogrammi da scegliere: {desired_count}
- Squadra osservata: {observed_team}
- Squadra casa: {home_team}
- Modulo casa: {home_formation}
- Squadra trasferta: {away_team}
- Modulo trasferta: {away_formation}
- Formazioni o numeri staff: {lineup_notes}
- Tempi candidati: {frame_times}
- Pre-score locale: {local_meta}

Regole importanti:
- Se il focus e' linea difensiva, centrocampo, offensiva, ampiezza o spazio tra reparti, preferisci immagini con campo aperto e piu giocatori visibili. Penalizza primi piani, arbitro isolato, replay, inquadrature ferme su un singolo giocatore.
- Se il focus e' pressing o transizioni, preferisci frame con palla, portatore, avversari vicini e densita attorno alla zona palla.
- Non inventare nomi dei giocatori. Rileva solo numeri o colori chiaramente leggibili.
- Le line_suggestions devono usare coordinate normalizzate da 0 a 1 rispetto all'immagine: x sinistra-destra, y alto-basso.
- Suggerisci al massimo 2 linee per frame e solo quando la lettura e' plausibile. Se il frame e' primo piano o poco tattico, lascia line_suggestions vuoto.
- Restituisci solo JSON valido, senza markdown.

Schema JSON:
{{
  "selected_indexes": [0, 3, 7],
  "frame_notes": [
    {{
      "index": 0,
      "phase": "Linea difensiva",
      "quality": 88,
      "camera": "campo aperto",
      "reason": "Linea e piu reparti visibili",
      "team_colors": ["bianco", "verde"],
      "visible_numbers": ["9", "18"],
      "player_read": "numeri parzialmente leggibili",
      "line_suggestions": [
        {{
          "phase": "Linea difensiva",
          "team": "Squadra osservata",
          "color": "#ff4058",
          "confidence": 72,
          "reason": "Tre giocatori in linea nella zona difensiva",
          "start": {{"x": 0.22, "y": 0.54}},
          "end": {{"x": 0.78, "y": 0.58}}
        }}
      ]
    }}
  ],
  "team_guess": {{
    "home_colors": "non certo",
    "away_colors": "non certo"
  }}
}}
""".strip()


def _call_openai_frame_selector(data: FrameSelectionRequest, frames: List[str]) -> dict:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY non configurata")

    prompt = _build_frame_selection_prompt(data, len(frames))
    content = [{"type": "text", "text": prompt}]
    for frame in frames:
        content.append({
            "type": "image_url",
            "image_url": {"url": frame}
        })

    payload = {
        "model": OPENAI_VIDEO_MODEL,
        "temperature": 0.1,
        "max_tokens": 1200,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Sei MatchIQ Frame Selector. Scegli fotogrammi calcistici utili "
                    "per una fase tattica e restituisci solo JSON valido."
                )
            },
            {"role": "user", "content": content},
        ],
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
        raise HTTPException(status_code=502, detail=f"Errore selezione AI: {detail or response.status_code}")

    message = response.json()["choices"][0]["message"]["content"]
    return _extract_json_object(message)


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
                    "pratici, prudenti e orientati all'allenamento. "
                    "Non usare chiusure da chatbot o inviti generici."
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


def _draw_pdf_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d8e4ef"))
    canvas.setLineWidth(0.4)
    canvas.line(doc.leftMargin, 30, A4[0] - doc.rightMargin, 30)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.setFillColor(colors.HexColor("#0b8f6a"))
    canvas.drawString(doc.leftMargin, 18, "MatchIQ Video Analyst")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawCentredString(A4[0] / 2, 18, "Supporto tecnico allo staff: valutazione finale dell'allenatore.")
    canvas.drawRightString(A4[0] - doc.rightMargin, 18, f"Pagina {doc.page}")
    canvas.restoreState()


def _paragraph(value: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(html.escape(str(value or "")), style)


def _build_pdf_base64(title: str, report: str, data: VideoReportRequest, frame_count: int) -> str:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=38, leftMargin=38, topMargin=34, bottomMargin=42)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="MatchIQTitle",
        parent=styles["Title"],
        textColor=colors.white,
        fontSize=23,
        leading=27,
        alignment=0,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="MatchIQKicker",
        parent=styles["Normal"],
        textColor=colors.HexColor("#00f5a0"),
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=12,
        spaceAfter=6,
        uppercase=True,
    ))
    styles.add(ParagraphStyle(
        name="MatchIQHeading",
        parent=styles["Heading3"],
        textColor=colors.HexColor("#092642"),
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        spaceBefore=8,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="MatchIQBody",
        parent=styles["BodyText"],
        fontSize=9.1,
        leading=12.2,
        textColor=colors.HexColor("#1f2937"),
    ))
    styles.add(ParagraphStyle(
        name="MatchIQSmall",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#475569"),
    ))
    styles.add(ParagraphStyle(
        name="MatchIQWhiteSmall",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#dbeafe"),
    ))
    story = []
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    duration = _format_seconds(float(data.duration_seconds or 0))
    frame_times = ", ".join(_format_seconds(t) for t in (data.frame_times or [])[:frame_count]) or "non disponibili"
    tactical_lines = _format_tactical_lines(data.tactical_lines)
    report_title = _clean_text(title, 180) or "Video Report MatchIQ"

    cover = Table(
        [[
            [
                Paragraph("MATCHIQ VIDEO ANALYST", styles["MatchIQKicker"]),
                _paragraph(report_title, styles["MatchIQTitle"]),
                Paragraph(
                    "Report tecnico generato da clip video: sintesi, rischi, transizioni e indicazioni operative per lo staff.",
                    styles["MatchIQWhiteSmall"],
                ),
            ]
        ]],
        colWidths=[A4[0] - doc.leftMargin - doc.rightMargin],
    )
    cover.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#07101f")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#0bbf8a")),
        ("LEFTPADDING", (0, 0), (-1, -1), 18),
        ("RIGHTPADDING", (0, 0), (-1, -1), 18),
        ("TOPPADDING", (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
    ]))
    story.append(cover)
    story.append(Spacer(1, 10))

    summary_rows = [
        ["Data", generated_at],
        ["Societa / squadra", _clean_text(data.club_name, 160) or "-"],
        ["Categoria", _clean_text(data.category, 80) or "-"],
        ["Focus", _clean_text(data.focus, 120) or "-"],
        ["Squadra osservata", _clean_text(data.observed_team, 160) or "-"],
        ["Casa / modulo", f"{_clean_text(data.home_team, 120) or '-'} / {_clean_text(data.home_formation, 40) or '-'}"],
        ["Trasferta / modulo", f"{_clean_text(data.away_team, 120) or '-'} / {_clean_text(data.away_formation, 40) or '-'}"],
        ["Stile report", _clean_text(data.report_style, 120) or "-"],
        ["Fotogrammi analizzati", str(frame_count)],
        ["Durata clip", duration],
        ["Tempi fotogrammi", frame_times],
        ["Linee tattiche", tactical_lines],
    ]
    summary = Table(summary_rows, colWidths=[128, 354])
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8fff6")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#075f4a")),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#1d2433")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.2),
        ("LEADING", (0, 0), (-1, -1), 10.5),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#d8e4ef")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary)
    story.append(Spacer(1, 9))

    limits_box = Table(
        [[
            Paragraph("<b>Nota di lettura</b>", styles["MatchIQSmall"]),
            Paragraph(
                "L'analisi deriva da fotogrammi estratti dalla clip. Se numeri, volti, palla o reparti non sono leggibili, il report resta prudente e segnala i limiti invece di inventare dettagli.",
                styles["MatchIQSmall"],
            ),
        ]],
        colWidths=[92, 390],
    )
    limits_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff7dd")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#f4d675")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(limits_box)
    story.append(Spacer(1, 10))

    for block in str(report or "").split("\n"):
        block = block.strip()
        if not block:
            story.append(Spacer(1, 4))
            continue
        style = styles["MatchIQHeading"] if block[:2].strip(".").isdigit() or block.endswith(":") else styles["MatchIQBody"]
        story.append(_paragraph(block, style))
        story.append(Spacer(1, 3))

    doc.build(story, onFirstPage=_draw_pdf_footer, onLaterPages=_draw_pdf_footer)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _public_video_report(row: dict):
    return {
        "id": row.get("id"),
        "title": row.get("title") or "Video Report MatchIQ",
        "club": row.get("club_name") or "",
        "category": row.get("category") or "",
        "focus": row.get("focus") or "",
        "observed_team": row.get("observed_team") or "",
        "report_style": row.get("report_style") or "",
        "frames": int(row.get("frames_analyzed") or 0),
        "report": row.get("report") or "",
        "pdf_base64": row.get("pdf_base64") or "",
        "date": row.get("created_at") or "",
        "cloud": True,
    }


def _save_cloud_report_for_user(user: dict, data: VideoReportRequest, report: str, pdf_base64: str, frames_count: int):
    if not user:
        return {"success": False, "reason": "login_required"}

    return save_video_report(
        user_id=user["id"],
        title=_clean_text(data.title, 180) or "Video Report MatchIQ",
        club_name=_clean_text(data.club_name, 160),
        category=_clean_text(data.category, 80),
        focus=_clean_text(data.focus, 160),
        observed_team=_clean_text(data.observed_team, 160),
        report_style=_clean_text(data.report_style, 120),
        frames_analyzed=frames_count,
        report=report,
        pdf_base64=pdf_base64,
        payload={
            "duration_seconds": data.duration_seconds,
            "frame_times": data.frame_times,
            "frame_meta": data.frame_meta[:12],
            "notes": _clean_text(data.notes, 1200),
            "tactical_lines": data.tactical_lines[:12],
            "home_team": _clean_text(data.home_team, 120),
            "away_team": _clean_text(data.away_team, 120),
            "home_formation": _clean_text(data.home_formation, 40),
            "away_formation": _clean_text(data.away_formation, 40),
            "lineup_notes": _clean_text(data.lineup_notes, 1400),
        },
    )


@router.post("/analyze")
def analyze_video_clip(data: VideoReportRequest, user=Depends(get_optional_user)):
    frames = _sanitize_frames(data.frames)

    if len(frames) < 2:
        raise HTTPException(
            status_code=400,
            detail="Servono almeno 2 fotogrammi validi per analizzare la clip"
        )

    usage = None
    if user:
        usage = can_use_feature(user["id"], "video_report")
        if not usage.get("allowed"):
            raise HTTPException(
                status_code=402,
                detail={
                    "success": False,
                    "allowed": False,
                    "upgrade_required": True,
                    "feature": "video_report",
                    "plan": usage.get("plan"),
                    "used": usage.get("used", 0),
                    "limit": usage.get("limit", 0),
                    "message": "Hai raggiunto il limite giornaliero per i report video AI."
                }
            )

    prompt = _build_prompt(data, len(frames))
    report = _sanitize_video_report(_call_openai(prompt, frames))
    title = _clean_text(data.title, 180) or "Video Report MatchIQ"
    pdf_base64 = _build_pdf_base64(title, report, data, len(frames))
    if user:
        track_api_usage(user["id"], "/api/video/analyze", "video_report")
    cloud_save = _save_cloud_report_for_user(user, data, report, pdf_base64, len(frames)) if user else None

    return {
        "ok": True,
        "model": OPENAI_VIDEO_MODEL,
        "frames_analyzed": len(frames),
        "title": title,
        "report": report,
        "pdf_base64": pdf_base64,
        "generated_at": datetime.utcnow().isoformat(),
        "cloud_saved": bool(cloud_save and cloud_save.get("success")),
        "cloud_report_id": cloud_save.get("id") if cloud_save and cloud_save.get("success") else None,
        "cloud_error": cloud_save.get("error") if cloud_save and not cloud_save.get("success") else None,
        "usage": {
            **usage,
            "used": int((usage or {}).get("used") or 0) + 1,
        } if usage else None,
    }


@router.post("/select-frames")
def select_video_frames(data: FrameSelectionRequest, user=Depends(get_optional_user)):
    frames = _sanitize_selection_frames(data.frames)

    if len(frames) < 2:
        raise HTTPException(
            status_code=400,
            detail="Servono almeno 2 fotogrammi candidati per la selezione AI"
        )

    result = _call_openai_frame_selector(data, frames)
    desired_count = max(2, min(MAX_FRAMES, int(data.desired_count or MAX_FRAMES)))
    selected_indexes = []

    for value in result.get("selected_indexes") or []:
        try:
            index = int(value)
        except Exception:
            continue
        if 0 <= index < len(frames) and index not in selected_indexes:
            selected_indexes.append(index)
        if len(selected_indexes) >= desired_count:
            break

    if len(selected_indexes) < 2:
        raise HTTPException(
            status_code=502,
            detail="La selezione AI non ha restituito fotogrammi validi"
        )

    notes_by_index = {}
    for note in result.get("frame_notes") or []:
        try:
            index = int(note.get("index"))
        except Exception:
            continue
        notes_by_index[str(index)] = {
            "label": _clean_text(note.get("phase") or note.get("camera") or "selezione AI", 80),
            "ai_quality": note.get("quality"),
            "ai_reason": _clean_text(note.get("reason", ""), 220),
            "team_colors": note.get("team_colors") if isinstance(note.get("team_colors"), list) else [],
            "visible_numbers": note.get("visible_numbers") if isinstance(note.get("visible_numbers"), list) else [],
            "player_read": _clean_text(note.get("player_read", ""), 180),
            "line_suggestions": _normalize_line_suggestions(note.get("line_suggestions") or []),
        }

    if user:
        track_api_usage(user["id"], "/api/video/select-frames", "video_report")

    return {
        "ok": True,
        "selected_indexes": selected_indexes,
        "frame_notes": notes_by_index,
        "team_guess": result.get("team_guess") or {},
    }


@router.get("/reports")
def list_video_reports(user=Depends(require_user)):
    limits = get_plan_limits(user.get("plan", "free"))
    limit = min(int(limits.get("video_archive_limit", 50) or 50), 200)
    rows = get_video_reports(user["id"], limit=limit)
    return {
        "ok": True,
        "reports": [_public_video_report(row) for row in rows],
        "limit": limit,
        "count": len(rows),
    }


@router.post("/reports")
def create_video_report(data: CloudVideoReportRequest, user=Depends(require_user)):
    result = save_video_report(
        user_id=user["id"],
        title=_clean_text(data.title, 180) or "Video Report MatchIQ",
        club_name=_clean_text(data.club_name, 160),
        category=_clean_text(data.category, 80),
        focus=_clean_text(data.focus, 160),
        observed_team=_clean_text(data.observed_team, 160),
        report_style=_clean_text(data.report_style, 120),
        frames_analyzed=int(data.frames_analyzed or 0),
        report=_clean_text(data.report, 12000),
        pdf_base64=str(data.pdf_base64 or ""),
        payload=data.payload or {},
    )

    if not result.get("success"):
        raise HTTPException(status_code=402, detail=result)

    return {"ok": True, "id": result.get("id")}


@router.delete("/reports/{report_id}")
def remove_video_report(report_id: int, user=Depends(require_user)):
    deleted = delete_video_report(user["id"], report_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Report video non trovato")

    return {"ok": True}
