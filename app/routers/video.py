import base64
import html
import io
import json
import os
from datetime import datetime
from typing import List, Optional

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from database import (
    can_use_feature,
    create_video_asset,
    delete_video_asset,
    delete_video_report,
    get_plan_limits,
    get_video_asset,
    get_video_assets,
    get_video_reports,
    save_video_report,
    save_video_frame_feedback,
    track_api_usage,
    update_video_asset_status,
)
from app.services.video_library import (
    parse_asset_metadata,
    remove_library_file,
    resolve_library_file,
    save_uploaded_video,
    storage_descriptor,
    validate_import_url,
)
from app.services.video_taxonomy import validate_selection_result
from usage_guard import get_optional_user, require_user


load_dotenv()
load_dotenv(".env.local", override=False)

router = APIRouter(prefix="/api/video", tags=["video"])

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_VIDEO_MODEL = os.getenv("OPENAI_VIDEO_MODEL", "gpt-4.1-mini").strip()
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

MAX_FRAMES = int(os.getenv("VIDEO_REPORT_MAX_FRAMES", "6"))
MAX_SELECTION_FRAMES = int(os.getenv("VIDEO_SELECTION_MAX_FRAMES", "32"))
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


class VideoSlide(BaseModel):
    index: Optional[int] = 0
    frame_index: Optional[int] = 0
    time_label: Optional[str] = ""
    phase: Optional[str] = ""
    set_piece_type: Optional[str] = ""
    grade: Optional[str] = ""
    grade_reason: Optional[str] = ""
    title: Optional[str] = ""
    tactical_read: Optional[str] = ""
    staff_action: Optional[str] = ""
    suggested_line: Optional[str] = ""
    training_drill: Optional[str] = ""
    confidence: Optional[int] = 0


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


class FrameFeedbackRequest(BaseModel):
    video_asset_id: Optional[int] = None
    report_id: Optional[int] = None
    frame_index: int = 0
    frame_time: float = 0
    source: Optional[str] = "verified"
    status: str
    requested_phase: Optional[str] = ""
    detected_phase: Optional[str] = ""
    corrected_phase: Optional[str] = ""
    confidence: Optional[float] = 0
    notes: Optional[str] = ""
    metadata: dict = Field(default_factory=dict)


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


class VideoImportRequest(BaseModel):
    title: Optional[str] = ""
    club_name: Optional[str] = ""
    category: Optional[str] = ""
    focus: Optional[str] = ""
    home_team: Optional[str] = ""
    away_team: Optional[str] = ""
    competition: Optional[str] = ""
    tags: Optional[str] = ""
    source_url: str
    rights_confirmed: bool = False
    notes: Optional[str] = ""


def _clean_text(value: str, limit: int = 1200) -> str:
    value = str(value or "").strip()
    return value[:limit]


def _clean_tags(value: str, limit: int = 8) -> list:
    items = []
    for raw in str(value or "").replace(";", ",").split(","):
        tag = _clean_text(raw, 28)
        if tag and tag.lower() not in {item.lower() for item in items}:
            items.append(tag)
        if len(items) >= limit:
            break
    return items


def _safe_thumbnail(value: str) -> str:
    text = str(value or "").strip()
    if not text.startswith("data:image/"):
        return ""
    if len(text) > 350000:
        return ""
    return text


def _normalize_frame_grade(value: str, confidence: int = 0, phase: str = "") -> str:
    raw = str(value or "").strip().lower()
    phase_text = str(phase or "").strip().lower()
    if "scart" in raw or "non tattico" in raw or "scart" in phase_text or "non tattico" in phase_text:
        return "Da scartare"
    if "pronta" in raw or "slide" in raw:
        return "Slide pronta"
    if "spunto" in raw or "utile" in raw or "controll" in raw:
        return "Spunto utile"
    if confidence >= 75:
        return "Slide pronta"
    if confidence >= 50:
        return "Spunto utile"
    return "Da scartare"


def _normalize_set_piece_type(value: str, phase: str = "") -> str:
    text = f"{value or ''} {phase or ''}".strip().lower()
    if not text:
        return ""
    side = ""
    if "difens" in text or "da difendere" in text:
        side = " difensivo"
    elif "offens" in text or "attacco" in text or "a favore" in text:
        side = " offensivo"

    if "corner" in text or "angolo" in text:
        return f"Calcio d'angolo{side}".strip()
    if "rimessa dal fondo" in text or "rinvio" in text:
        return "Rimessa dal fondo"
    if "rimessa laterale" in text or "throw" in text or "fallo laterale" in text:
        return f"Rimessa laterale{side}".strip()
    if "punizione laterale" in text or ("punizione" in text and ("laterale" in text or "fascia" in text)):
        return f"Punizione laterale{side}".strip()
    if "punizione centrale" in text or "free kick" in text or "punizione" in text:
        return f"Punizione centrale{side}".strip()
    if "palla inattiva" in text:
        if "difens" in text or "da difendere" in text:
            return "Palla inattiva difensiva"
        if "offens" in text or "attacco" in text or "a favore" in text:
            return "Palla inattiva offensiva"
        return "Palla inattiva da classificare"
    return ""


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
        effect = _clean_text(item.get("effect", ""), 20).lower()
        if effect not in {"line", "shadow", "zone", "player"}:
            effect = "line"
        safe_lines.append({
            "phase": _clean_text(item.get("phase", ""), 80) or "Linea tattica",
            "team": _clean_text(item.get("team", ""), 80) or "Squadra osservata",
            "color": _safe_color(item.get("color"), "#ff4058"),
            "confidence": item.get("confidence"),
            "reason": _clean_text(item.get("reason", ""), 220),
            "effect": effect,
            "player_name": _clean_text(item.get("player_name", ""), 80),
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
- Riconosci palle inattive in modo specifico: "Calcio d'angolo offensivo", "Calcio d'angolo difensivo", "Punizione laterale offensiva", "Punizione laterale difensiva", "Punizione centrale offensiva", "Punizione centrale difensiva", "Rimessa laterale offensiva", "Rimessa laterale difensiva", "Rimessa dal fondo".
- Non usare "Palla inattiva offensiva/difensiva" se puoi capire il tipo reale. Se non lo capisci, usa "Palla inattiva da classificare" con grade massimo "Spunto utile".
- Se il focus chiede calci d'angolo, seleziona solo frame in cui si vede davvero un corner: punto di battuta vicino alla bandierina, area pronta, giocatori schierati, palla ferma o traiettoria da corner. Non chiamare corner un'azione a campo aperto.
- Se il focus chiede punizioni, seleziona solo frame con palla ferma, barriera/linea difensiva o punto di battuta riconoscibile. Non chiamare punizione un cross o un'azione dinamica.
- Se il focus chiede rimesse laterali, seleziona solo frame con giocatore vicino alla linea laterale in gesto di battuta o palla fuori/ferma in zona laterale. Non chiamare rimessa una normale azione sulla fascia.
- Riconosci "Costruzione dal basso" quando la palla parte da portiere/difensori, con prima pressione avversaria e linee di passaggio basse.
- Per ogni frame indica restart_type, ball_state, field_zone e visual_signals. Se non trovi segnali visivi chiari, usa restart_type "open_play" o "unknown" e non forzare palle inattive.
- Se il focus chiede un tipo specifico e nessun fotogramma lo dimostra, restituisci selected_indexes vuoto e metti i frame dubbi come "Da scartare" o "Spunto utile".
- Non selezionare come "Slide pronta" una palla inattiva senza almeno 2 prove visive tra: palla ferma, punto di battuta, bandierina, barriera, area pronta, gesto di rimessa, portiere in area, difensori in costruzione.
- Classifica ogni frame con grade: "Slide pronta" solo se palla, campo, reparti e fase sono leggibili; "Spunto utile" se la situazione puo aiutare ma va controllata; "Da scartare" se non va nello storyboard.
- Per palle inattive e costruzione dal basso non basta un'inquadratura generica: serve vedere chiaramente punto di battuta/portiere, palla, compagni e avversari rilevanti. Altrimenti usa "Spunto utile" o "Da scartare".
- Se il frame mostra esultanza, primo piano, giocatore isolato, panchina, arbitro o scena senza lettura collettiva, non chiamarlo linea difensiva/pressing: usa phase "Frame non tattico", quality massimo 35 e non aggiungere line_suggestions.
- In selected_indexes metti prima le "Slide pronta", poi eventuali "Spunto utile"; evita "Da scartare" salvo mancanza totale di alternative.
- Non fidarti del pre-score locale se l'immagine reale lo contraddice: guarda il fotogramma e correggi etichetta e quality.
- Se il pre-score locale dice corner/punizione/rimessa ma l'immagine non lo dimostra chiaramente, correggi phase in "Frame non tattico" o "Palla inattiva da classificare" e metti quality massimo 45.
- Non inventare nomi dei giocatori. Se nelle formazioni e' scritto "numero + nome" e il numero e' leggibile, puoi citare il nome come ipotesi prudente.
- Le line_suggestions devono usare coordinate normalizzate da 0 a 1 rispetto all'immagine: x sinistra-destra, y alto-basso.
- Suggerisci al massimo 2 effetti per frame e solo quando la lettura e' plausibile. Per "line_suggestions" puoi usare phase come: Linea difensiva, Linea centrocampo, Calcio d'angolo difensivo, Punizione laterale offensiva, Rimessa laterale difensiva, Rimessa dal fondo, Costruzione dal basso, Cono d'ombra, Zona libera, Rest defense.
- Per coni d'ombra e zone usa sempre start/end come riferimento grafico approssimato. Se il frame e' primo piano o poco tattico, lascia line_suggestions vuoto.
- Restituisci solo JSON valido, senza markdown.

Schema JSON:
{{
  "selected_indexes": [0, 3, 7],
  "frame_notes": [
    {{
      "index": 0,
      "phase": "Calcio d'angolo difensivo",
      "set_piece_type": "Calcio d'angolo difensivo",
      "grade": "Slide pronta",
      "quality": 88,
      "camera": "campo aperto",
      "restart_type": "corner",
      "restart_side": "defensive",
      "field_zone": "corner_flag",
      "ball_state": "stopped",
      "visual_signals": ["punto di battuta vicino alla bandierina", "area pronta", "marcature visibili"],
      "missing_signals": [],
      "evidence": "Si vedono punto di battuta del corner, palla ferma e marcature in area",
      "reason": "Punto di battuta, area e marcature visibili",
      "grade_reason": "Corner difensivo riconoscibile con avversari e marcature in area",
      "team_colors": ["bianco", "verde"],
      "visible_numbers": ["9", "18"],
      "player_read": "numeri parzialmente leggibili",
      "line_suggestions": [
        {{
          "phase": "Calcio d'angolo difensivo",
          "team": "Squadra osservata",
          "color": "#ff4058",
          "confidence": 72,
          "reason": "Tre giocatori in linea nella zona difensiva",
          "effect": "line",
          "player_name": "",
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


def _build_slides_prompt(data: VideoReportRequest, frame_count: int) -> str:
    title = _clean_text(data.title, 180) or "Video partita"
    focus = _clean_text(data.focus, 160) or "Analisi tattica generale"
    observed_team = _clean_text(data.observed_team, 160) or "Squadra osservata"
    home_team = _clean_text(data.home_team, 120) or "Non specificata"
    away_team = _clean_text(data.away_team, 120) or "Non specificata"
    home_formation = _clean_text(data.home_formation, 40) or "Non indicato"
    away_formation = _clean_text(data.away_formation, 40) or "Non indicato"
    lineup_notes = _clean_text(data.lineup_notes, 1400) or "Non inserite"
    notes = _clean_text(data.notes, 1200) or "Nessuna nota staff inserita."
    frame_times = ", ".join(
        f"Frame {idx + 1}: {_format_seconds(t)}"
        for idx, t in enumerate((data.frame_times or [])[:frame_count])
    ) or "non disponibili"
    frame_meta = _format_frame_meta(data.frame_meta, frame_count)
    tactical_lines = _format_tactical_lines(data.tactical_lines)

    return f"""
Costruisci una mini-presentazione tattica tipo match analyst professionista partendo dai fotogrammi della clip.

Contesto:
- Titolo: {title}
- Focus richiesto: {focus}
- Squadra osservata: {observed_team}
- Casa/modulo: {home_team} / {home_formation}
- Trasferta/modulo: {away_team} / {away_formation}
- Formazioni o numeri staff: {lineup_notes}
- Note staff: {notes}
- Tempi frame: {frame_times}
- Motivo selezione frame: {frame_meta}
- Linee tattiche gia tracciate: {tactical_lines}

Obiettivo prodotto:
Devi proporre slide pronte per un allenatore o match analyst: una slide deve dire cosa guardare, perche conta e cosa correggere.
Non inventare giocatori, nomi o misurazioni.
Ogni frame deve avere grade:
- "Slide pronta": entra nello storyboard perche fase, palla, reparti e distanze sono leggibili.
- "Spunto utile": puo aiutare staff o match analyst, ma va controllato prima di usarlo nel PDF o nella riunione.
- "Da scartare": non deve essere usato come slide tattica perche e' primo piano, esultanza, replay, scena troppo chiusa o fase non leggibile.
Per palle inattive non restare generico: devi distinguere se e' calcio d'angolo, punizione laterale, punizione centrale, rimessa laterale o rimessa dal fondo. Aggiungi sempre set_piece_type quando riconosci una palla inattiva.
Per palle inattive e costruzione dal basso usa "Slide pronta" solo se la situazione e' davvero chiara: punto di battuta o portiere, palla, linea avversaria e compagni rilevanti devono essere visibili.
Guarda il fotogramma reale, non solo le etichette ricevute: se il frame mostra esultanza, primo piano, giocatore isolato, panchina o scena senza struttura collettiva, non trasformarlo in linea difensiva o pressing.
In quei casi imposta grade "Da scartare", phase "Frame da scartare", title "Frame non adatto alla slide", suggested_line "Nessuna linea affidabile" e confidence massimo 35.
Quando possibile, suggerisci quale linea tracciare: linea difensiva, centrocampo, offensiva, ampiezza, spazio tra reparti, pressing o rest defense.
Devi includere quando riconoscibile una sezione/fase specifica tra:
- Calcio d'angolo offensivo/difensivo: corner a favore o da difendere, con area e punto di battuta leggibili.
- Punizione laterale offensiva/difensiva: palla ferma laterale, traiettoria crossabile, linea/area da attaccare o difendere.
- Punizione centrale offensiva/difensiva: palla ferma centrale o semi-centrale, barriera o struttura difensiva/offensiva leggibile.
- Rimessa laterale offensiva/difensiva: battuta laterale riconoscibile, smarcamenti, marcature e zona palla leggibili.
- Rimessa dal fondo: portiere o difensori bassi impostano da fermo.
- Costruzione dal basso: portiere/difensori iniziano l'azione, avversari pressano, linee di passaggio basse.
- Cono d'ombra: zona schermata da un giocatore o da una linea di pressione.
- Giocatore chiave: solo se il numero/nome e' coerente con le formazioni inserite dallo staff; altrimenti resta prudente.
Usa un linguaggio da staff, non da debug: "spunto tattico", "clip utile", "priorita staff", "frame da scartare".
Restituisci solo JSON valido, senza markdown.

Schema:
{{
  "slides": [
    {{
      "index": 1,
      "frame_index": 0,
      "time_label": "12:34",
      "phase": "Calcio d'angolo difensivo",
      "set_piece_type": "Calcio d'angolo difensivo",
      "grade": "Slide pronta",
      "grade_reason": "Punto di battuta, area e marcature sono leggibili",
      "title": "Marcature su calcio d'angolo",
      "tactical_read": "La squadra osservata difende il corner con marcature strette e copertura del secondo palo.",
      "staff_action": "Controllare comunicazione tra primo palo, zona dischetto e secondo palo.",
      "suggested_line": "Traccia zona di attacco palla e linea dei marcatori in area.",
      "training_drill": "Sequenza corner difensivi con uscita, respinta e seconda palla.",
      "confidence": 82
    }}
  ],
  "deck_summary": "Tema principale da portare allo staff",
  "coach_next_click": "La prossima azione consigliata nell'app"
}}
""".strip()


def _sanitize_slides(raw: dict, frame_count: int) -> dict:
    slides = []
    for idx, item in enumerate((raw or {}).get("slides") or []):
        try:
            frame_index = int(item.get("frame_index", idx))
        except Exception:
            frame_index = idx
        frame_index = max(0, min(max(0, frame_count - 1), frame_index))
        try:
            confidence = int(float(item.get("confidence", 0) or 0))
        except Exception:
            confidence = 0
        confidence = max(0, min(100, confidence))
        phase = _clean_text(item.get("phase", ""), 80) or "Lettura tattica"
        set_piece_type = _normalize_set_piece_type(item.get("set_piece_type", ""), phase)
        if set_piece_type and phase.lower().startswith("palla inattiva"):
            phase = set_piece_type
        grade = _normalize_frame_grade(item.get("grade", ""), confidence, phase)
        slides.append({
            "index": idx + 1,
            "frame_index": frame_index,
            "time_label": _clean_text(item.get("time_label", ""), 20),
            "phase": phase,
            "set_piece_type": set_piece_type,
            "grade": grade,
            "grade_reason": _clean_text(item.get("grade_reason", ""), 180),
            "title": _clean_text(item.get("title", ""), 120) or f"Slide {idx + 1}",
            "tactical_read": _clean_text(item.get("tactical_read", ""), 420),
            "staff_action": _clean_text(item.get("staff_action", ""), 360),
            "suggested_line": _clean_text(item.get("suggested_line", ""), 220),
            "training_drill": _clean_text(item.get("training_drill", ""), 260),
            "confidence": confidence,
        })
        if len(slides) >= min(6, frame_count):
            break
    return {
        "slides": slides,
        "deck_summary": _clean_text((raw or {}).get("deck_summary", ""), 260),
        "coach_next_click": _clean_text((raw or {}).get("coach_next_click", ""), 220),
    }


def _call_openai_slides(data: VideoReportRequest, frames: List[str]) -> dict:
    if not OPENAI_API_KEY:
        return {"slides": [], "deck_summary": "", "coach_next_click": ""}

    prompt = _build_slides_prompt(data, len(frames))
    content = [{"type": "text", "text": prompt}]
    for frame in frames:
        content.append({"type": "image_url", "image_url": {"url": frame}})

    payload = {
        "model": OPENAI_VIDEO_MODEL,
        "temperature": 0.15,
        "max_tokens": 1800,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Sei MatchIQ Slide Analyst. Crei storyboard tattici in JSON "
                    "per staff tecnici, con letture prudenti e azioni operative."
                ),
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
        return {"slides": [], "deck_summary": "", "coach_next_click": ""}
    message = response.json()["choices"][0]["message"]["content"]
    return _sanitize_slides(_extract_json_object(message), len(frames))


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


def _pdf_cell(value: str, style: ParagraphStyle) -> Paragraph:
    safe = html.escape(str(value or "")).replace("\n", "<br/>")
    return Paragraph(safe, style)


def _build_pdf_base64(title: str, report: str, data: VideoReportRequest, frame_count: int, slides_data: Optional[dict] = None) -> str:
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

    slides = (slides_data or {}).get("slides") or []
    if slides:
        story.append(_paragraph("Diapositive tattiche AI", styles["MatchIQHeading"]))
        deck_summary = _clean_text((slides_data or {}).get("deck_summary", ""), 260)
        if deck_summary:
            story.append(_paragraph(deck_summary, styles["MatchIQSmall"]))
            story.append(Spacer(1, 5))
        slide_rows = [["Slide", "Frame", "Lettura", "Azione staff"]]
        for slide in slides[:6]:
            grade = _normalize_frame_grade(slide.get("grade", ""), int(slide.get("confidence") or 0), slide.get("phase", ""))
            grade_reason = _clean_text(slide.get("grade_reason", ""), 160)
            set_piece_type = _normalize_set_piece_type(slide.get("set_piece_type", ""), slide.get("phase", ""))
            phase_label = slide.get("phase") or ""
            if set_piece_type:
                phase_label = f"{phase_label}\nPalla inattiva: {set_piece_type}"
            slide_rows.append([
                _pdf_cell(f"{slide.get('index') or ''}\n{grade}", styles["MatchIQSmall"]),
                _pdf_cell(slide.get("time_label") or f"Frame {int(slide.get('frame_index') or 0) + 1}", styles["MatchIQSmall"]),
                _pdf_cell(f"{slide.get('title') or ''}\n{phase_label}\n{grade_reason}\n{slide.get('tactical_read') or ''}\nLinea: {slide.get('suggested_line') or '-'}", styles["MatchIQSmall"]),
                _pdf_cell(f"{slide.get('staff_action') or '-'}\nEsercizio: {slide.get('training_drill') or '-'}", styles["MatchIQSmall"]),
            ])
        slide_table = Table(slide_rows, colWidths=[36, 62, 194, 190])
        slide_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#07101f")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#1f2937")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.4),
            ("LEADING", (0, 0), (-1, -1), 9.4),
            ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#d8e4ef")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(slide_table)
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
    payload = row.get("payload") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {}
    if not isinstance(payload, dict):
        payload = {}

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
        "slides": payload.get("slides") or [],
        "deck_summary": payload.get("deck_summary") or "",
        "coach_next_click": payload.get("coach_next_click") or "",
        "cloud": True,
    }


def _public_video_asset(row: dict):
    metadata = row.get("metadata") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}
    job = metadata.get("job") if isinstance(metadata.get("job"), dict) else {}
    status = row.get("status") or job.get("status") or "ready"
    progress = job.get("progress")
    if progress is None:
        progress = 100 if status == "ready" else 0

    return {
        "id": row.get("id"),
        "title": row.get("title") or row.get("file_name") or "Partita MatchIQ",
        "club": row.get("club_name") or "",
        "category": row.get("category") or "",
        "source_type": row.get("source_type") or "upload",
        "source_url": row.get("source_url") or "",
        "file_name": row.get("file_name") or "",
        "mime_type": row.get("mime_type") or "",
        "size_bytes": int(row.get("size_bytes") or 0),
        "rights_confirmed": bool(row.get("rights_confirmed")),
        "status": status,
        "progress": max(0, min(100, int(progress or 0))),
        "job_stage": job.get("stage") or status,
        "job_error": job.get("error") or "",
        "thumbnail": metadata.get("thumbnail") or "",
        "duration_seconds": float(metadata.get("duration_seconds") or 0),
        "home_team": metadata.get("home_team") or "",
        "away_team": metadata.get("away_team") or "",
        "competition": metadata.get("competition") or "",
        "focus": metadata.get("focus") or "",
        "tags": metadata.get("tags") if isinstance(metadata.get("tags"), list) else [],
        "last_used_at": metadata.get("last_used_at") or "",
        "metadata": metadata,
        "created_at": row.get("created_at") or "",
        "updated_at": row.get("updated_at") or "",
    }


def _save_cloud_report_for_user(user: dict, data: VideoReportRequest, report: str, pdf_base64: str, frames_count: int, slides_data: Optional[dict] = None):
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
            "slides": (slides_data or {}).get("slides", [])[:8],
            "deck_summary": _clean_text((slides_data or {}).get("deck_summary", ""), 260),
            "coach_next_click": _clean_text((slides_data or {}).get("coach_next_click", ""), 220),
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

    if not user:
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "allowed": False,
                "login_required": True,
                "message": "Accedi o registrati per generare report video AI."
            }
        )

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
                "message": "Hai raggiunto il limite giornaliero per i report video AI. Passa a Pro per continuare."
            }
        )

    prompt = _build_prompt(data, len(frames))
    report = _sanitize_video_report(_call_openai(prompt, frames))
    slides = _call_openai_slides(data, frames)
    title = _clean_text(data.title, 180) or "Video Report MatchIQ"
    pdf_base64 = _build_pdf_base64(title, report, data, len(frames), slides)
    track_api_usage(user["id"], "/api/video/analyze", "video_report")
    cloud_save = _save_cloud_report_for_user(user, data, report, pdf_base64, len(frames), slides)

    return {
        "ok": True,
        "model": OPENAI_VIDEO_MODEL,
        "frames_analyzed": len(frames),
        "title": title,
        "report": report,
        "slides": slides.get("slides", []),
        "deck_summary": slides.get("deck_summary", ""),
        "coach_next_click": slides.get("coach_next_click", ""),
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

    if not user:
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "allowed": False,
                "login_required": True,
                "message": "Accedi o registrati per usare la selezione AI dei frame."
            }
        )

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
                "message": "Hai raggiunto il limite giornaliero per i video AI. Passa a Pro per continuare."
            }
        )

    desired_count = max(2, min(MAX_FRAMES, int(data.desired_count or MAX_FRAMES)))
    result = _call_openai_frame_selector(data, frames)

    normalized_notes = []
    for note in result.get("frame_notes") or []:
        try:
            index = int(note.get("index"))
        except Exception:
            continue
        try:
            quality = int(float(note.get("quality", 0) or 0))
        except Exception:
            quality = 0
        phase = _clean_text(note.get("phase") or note.get("camera") or "selezione AI", 80)
        set_piece_type = _normalize_set_piece_type(note.get("set_piece_type", ""), phase)
        if set_piece_type and phase.lower().startswith("palla inattiva"):
            phase = set_piece_type
        grade = _normalize_frame_grade(note.get("grade", ""), quality, phase)
        normalized_notes.append({
            "index": index,
            "label": phase,
            "phase": phase,
            "set_piece_type": set_piece_type,
            "grade": grade,
            "grade_reason": _clean_text(note.get("grade_reason", ""), 180),
            "quality": quality,
            "ai_quality": quality,
            "ai_reason": _clean_text(note.get("reason", ""), 220),
            "reason": _clean_text(note.get("reason", ""), 220),
            "restart_type": _clean_text(note.get("restart_type", ""), 40),
            "restart_side": _clean_text(note.get("restart_side", ""), 40),
            "field_zone": _clean_text(note.get("field_zone", ""), 60),
            "ball_state": _clean_text(note.get("ball_state", ""), 40),
            "visual_signals": [_clean_text(item, 90) for item in note.get("visual_signals", [])[:8]] if isinstance(note.get("visual_signals"), list) else [],
            "missing_signals": [_clean_text(item, 90) for item in note.get("missing_signals", [])[:8]] if isinstance(note.get("missing_signals"), list) else [],
            "evidence": _clean_text(note.get("evidence", ""), 220),
            "team_colors": note.get("team_colors") if isinstance(note.get("team_colors"), list) else [],
            "visible_numbers": note.get("visible_numbers") if isinstance(note.get("visible_numbers"), list) else [],
            "player_read": _clean_text(note.get("player_read", ""), 180),
            "line_suggestions": _normalize_line_suggestions(note.get("line_suggestions") or []),
        })

    result["frame_notes"] = normalized_notes
    return validate_selection_result(result, data, len(frames), desired_count)


@router.get("/library")
def list_video_library(user=Depends(require_user)):
    rows = get_video_assets(user["id"], limit=80)
    return {
        "ok": True,
        "items": [_public_video_asset(row) for row in rows],
        "count": len(rows),
    }


@router.post("/library/upload")
def upload_video_library_item(
    title: str = Form(""),
    club_name: str = Form(""),
    category: str = Form(""),
    focus: str = Form(""),
    home_team: str = Form(""),
    away_team: str = Form(""),
    competition: str = Form(""),
    tags: str = Form(""),
    duration_seconds: float = Form(0),
    thumbnail: str = Form(""),
    rights_confirmed: bool = Form(False),
    file: UploadFile = File(...),
    user=Depends(require_user),
):
    if not rights_confirmed:
        raise HTTPException(status_code=400, detail="Conferma di avere diritto a usare questo video.")

    saved = save_uploaded_video(user["id"], file, title)
    result = create_video_asset(
        user_id=user["id"],
        title=_clean_text(title, 180) or saved.get("file_name", "Partita MatchIQ"),
        club_name=_clean_text(club_name, 160),
        category=_clean_text(category, 80),
        source_type="upload",
        file_path=saved.get("file_path", ""),
        file_name=saved.get("file_name", ""),
        mime_type=saved.get("mime_type", ""),
        size_bytes=int(saved.get("size_bytes") or 0),
        rights_confirmed=True,
        status="ready",
        metadata={
            **storage_descriptor(saved),
            "original_name": saved.get("file_name", ""),
            "duration_seconds": max(0, float(duration_seconds or 0)),
            "home_team": _clean_text(home_team, 120),
            "away_team": _clean_text(away_team, 120),
            "competition": _clean_text(competition, 120),
            "focus": _clean_text(focus, 160),
            "tags": _clean_tags(tags),
            "thumbnail": _safe_thumbnail(thumbnail),
            "job": {
                "status": "ready",
                "stage": "ready",
                "progress": 100,
                "updated_at": datetime.utcnow().isoformat(),
            },
        },
    )
    asset = get_video_asset(user["id"], result["id"])
    return {"ok": True, "item": _public_video_asset(asset)}


@router.post("/library/import-url")
def import_video_library_url(data: VideoImportRequest, user=Depends(require_user)):
    if not data.rights_confirmed:
        raise HTTPException(status_code=400, detail="Conferma di avere diritto a usare questo link video.")

    import_info = validate_import_url(data.source_url)
    safe_url = import_info.get("url", "")
    result = create_video_asset(
        user_id=user["id"],
        title=_clean_text(data.title, 180) or "Video importato",
        club_name=_clean_text(data.club_name, 160),
        category=_clean_text(data.category, 80),
        source_type="url",
        source_url=safe_url,
        mime_type=import_info.get("content_type", ""),
        size_bytes=int(import_info.get("size_bytes") or 0),
        rights_confirmed=True,
        status="ready",
        metadata={
            "notes": _clean_text(data.notes, 500),
            "storage": "remote_url",
            "import_check": {
                "content_type": import_info.get("content_type", ""),
                "size_bytes": int(import_info.get("size_bytes") or 0),
                "extension": import_info.get("extension", ""),
                "redirects": import_info.get("redirects", [])[:4],
                "checked_at": datetime.utcnow().isoformat(),
            },
            "home_team": _clean_text(data.home_team, 120),
            "away_team": _clean_text(data.away_team, 120),
            "competition": _clean_text(data.competition, 120),
            "focus": _clean_text(data.focus, 160),
            "tags": _clean_tags(data.tags),
            "job": {
                "status": "ready",
                "stage": "ready",
                "progress": 100,
                "updated_at": datetime.utcnow().isoformat(),
            },
        },
    )
    asset = get_video_asset(user["id"], result["id"])
    return {"ok": True, "item": _public_video_asset(asset)}


@router.post("/library/{asset_id}/touch")
def touch_video_library_item(asset_id: int, user=Depends(require_user)):
    asset = get_video_asset(user["id"], asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Video non trovato")
    public = _public_video_asset(asset)
    updated = update_video_asset_status(
        user_id=user["id"],
        asset_id=asset_id,
        status=public.get("status") or "ready",
        progress=public.get("progress", 100),
        stage=public.get("job_stage") or "ready",
        metadata_patch={"last_used_at": datetime.utcnow().isoformat()},
    )
    return {"ok": True, "item": _public_video_asset(updated)}


@router.get("/library/{asset_id}/status")
def get_video_library_status(asset_id: int, user=Depends(require_user)):
    asset = get_video_asset(user["id"], asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Video non trovato")
    return {"ok": True, "item": _public_video_asset(asset)}


@router.post("/library/{asset_id}/status")
def update_video_library_status(asset_id: int, data: dict, user=Depends(require_user)):
    status = _clean_text(data.get("status", ""), 40) or "ready"
    if status not in {"queued", "uploading", "processing", "ready", "error"}:
        status = "ready"
    asset = update_video_asset_status(
        user_id=user["id"],
        asset_id=asset_id,
        status=status,
        progress=data.get("progress"),
        stage=_clean_text(data.get("stage", ""), 60) or status,
        error=_clean_text(data.get("error", ""), 300),
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Video non trovato")
    return {"ok": True, "item": _public_video_asset(asset)}


@router.get("/library/{asset_id}/stream")
def stream_video_library_item(asset_id: int, user=Depends(require_user)):
    asset = get_video_asset(user["id"], asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Video non trovato")
    if asset.get("source_type") != "upload":
        raise HTTPException(status_code=400, detail="Questo video e' un link esterno, non un file caricato.")
    file_path = resolve_library_file(asset)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File video non disponibile sul server")
    return FileResponse(
        file_path,
        media_type=asset.get("mime_type") or "video/mp4",
        filename=asset.get("file_name") or "matchiq-video.mp4",
    )


@router.delete("/library/{asset_id}")
def remove_video_library_item(asset_id: int, user=Depends(require_user)):
    asset = delete_video_asset(user["id"], asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Video non trovato")
    remove_library_file(asset.get("file_path"), parse_asset_metadata(asset))
    return {"ok": True, "deleted": True}


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


@router.post("/frame-feedback")
def create_frame_feedback(data: FrameFeedbackRequest, user=Depends(require_user)):
    status = _clean_text(data.status, 40).lower()
    allowed = {"corretto", "non pertinente", "categoria corretta", "approvato", "scartato"}
    if status not in allowed:
        raise HTTPException(status_code=400, detail="Feedback frame non valido")

    corrected_phase = _clean_text(data.corrected_phase, 120)
    if status == "categoria corretta" and not corrected_phase:
        raise HTTPException(status_code=400, detail="Indica la categoria corretta")

    result = save_video_frame_feedback(
        user_id=user["id"],
        video_asset_id=data.video_asset_id,
        report_id=data.report_id,
        frame_index=max(0, int(data.frame_index or 0)),
        frame_time=max(0, float(data.frame_time or 0)),
        source=_clean_text(data.source, 40),
        status=status,
        requested_phase=_clean_text(data.requested_phase, 160),
        detected_phase=_clean_text(data.detected_phase, 160),
        corrected_phase=corrected_phase,
        confidence=float(data.confidence or 0),
        notes=_clean_text(data.notes, 500),
        metadata=data.metadata or {},
    )

    return {"ok": True, "id": result.get("id"), "created_at": result.get("created_at")}
