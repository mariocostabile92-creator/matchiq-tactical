from __future__ import annotations

import subprocess
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .contracts import CandidateSampler, PipelineSelector
from .reports import write_html_report, write_json_report
from .sampler import CurrentPipelineSampler
from .selector import CurrentPipelineSelector


@dataclass(frozen=True, slots=True)
class BaselineRunConfig:
    video_path: Path
    output_dir: Path
    focus: str = "Analisi tattica generale"
    desired_count: int = 6
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BaselineRunResult:
    report: dict[str, Any]
    json_path: Path
    html_path: Path


def _source_revision() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _timestamp_label(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    return f"{total // 60:02d}:{total % 60:02d}"


def _description(note: dict[str, Any]) -> str:
    for key in ("evidence", "reason", "grade_reason", "ai_reason"):
        value = str(note.get(key) or "").strip()
        if value:
            return value
    return ""


def _category(note: dict[str, Any]) -> str:
    for key in ("detected_label", "set_piece_type", "label", "phase"):
        value = str(note.get(key) or "").strip()
        if value:
            return value
    return "Unknown"


def _confidence(note: dict[str, Any]) -> dict[str, Any]:
    displayed = None
    for key in ("confidence", "ai_quality", "quality"):
        if note.get(key) not in (None, ""):
            displayed = note[key]
            break
    if displayed is None:
        return {"displayed": None, "type": "unavailable", "origin": "not returned"}
    return {
        "displayed": displayed,
        "type": "OpenAI self-assessed quality moderated by taxonomy",
        "origin": "OpenAI Frame Selector + app.services.video_taxonomy",
    }


class BaselineRunner:
    def __init__(
        self,
        sampler: CandidateSampler | None = None,
        selector: PipelineSelector | None = None,
        *,
        clock: Callable[[], float] = time.perf_counter,
        now: Callable[[], datetime] | None = None,
        revision: Callable[[], str] = _source_revision,
    ) -> None:
        self.sampler = sampler or CurrentPipelineSampler()
        self.selector = selector or CurrentPipelineSelector(clock=clock)
        self.clock = clock
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.revision = revision

    def run(self, config: BaselineRunConfig) -> BaselineRunResult:
        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        started = self.clock()

        extraction_started = self.clock()
        batch = self.sampler.sample(
            Path(config.video_path),
            focus=config.focus,
            desired_count=config.desired_count,
        )
        extraction_seconds = self.clock() - extraction_started
        if len(batch.candidates) < 2:
            raise RuntimeError(
                "La pipeline corrente richiede almeno 2 fotogrammi candidati; "
                f"estratti: {len(batch.candidates)}"
            )

        observation = self.selector.select(
            batch,
            focus=config.focus,
            desired_count=config.desired_count,
            context=config.context,
        )
        total_processing_seconds = self.clock() - started
        validated = observation.validated_result
        notes = validated.get("frame_notes") or {}
        if isinstance(notes, list):
            notes = {
                str(item.get("index")): item
                for item in notes
                if isinstance(item, dict) and item.get("index") is not None
            }

        verified = set(validated.get("verified_indexes") or validated.get("selected_indexes") or [])
        review_candidates = set(validated.get("candidate_indexes") or [])
        rejected = set(validated.get("rejected_indexes") or [])
        frames_dir = output_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        candidates: list[dict[str, Any]] = []

        for candidate in batch.candidates:
            note = notes.get(str(candidate.index), {}) if isinstance(notes, dict) else {}
            if candidate.index in verified:
                selection_status = "verified"
            elif candidate.index in review_candidates:
                selection_status = "candidate"
            elif candidate.index in rejected:
                selection_status = "rejected"
            else:
                selection_status = "not_returned"
            frame_name = f"candidate_{candidate.index + 1:03d}_{round(candidate.timestamp_seconds * 1000):010d}ms.jpg"
            (frames_dir / frame_name).write_bytes(candidate.jpeg_bytes)
            candidates.append(
                {
                    "index": candidate.index,
                    "timestamp_seconds": candidate.timestamp_seconds,
                    "timestamp_label": _timestamp_label(candidate.timestamp_seconds),
                    "frame_selected": candidate.index in verified,
                    "frame_file": f"frames/{frame_name}",
                    "category": _category(note),
                    "description": _description(note),
                    "selection_status": selection_status,
                    "confidence": _confidence(note),
                    "local_metadata": candidate.local_metadata,
                }
            )

        distribution = dict(sorted(Counter(item["category"] for item in candidates).items()))
        descriptions = sum(bool(item["description"]) for item in candidates)
        count = len(candidates)
        revision = self.revision()
        processed_at = self.now().astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        report = {
            "schema_version": "matchiq.ve-001.baseline-report.v1",
            "run": {
                "status": "completed",
                "processed_at": processed_at,
                "pipeline_version": f"current-static-frame-openai@{revision}",
                "source_revision": revision,
                "runner_version": "VE-001",
                "focus": config.focus,
                "desired_count": config.desired_count,
            },
            "video": {
                "file_name": batch.video.file_name,
                "path": batch.video.path,
                "duration_seconds": batch.video.duration_seconds,
                "fps": batch.video.fps,
                "width": batch.video.width,
                "height": batch.video.height,
                "resolution": f"{batch.video.width}x{batch.video.height}",
                "frame_count": batch.video.frame_count,
            },
            "pipeline_statistics": {
                "frames_analyzed": count,
                "candidates_found": count,
                "candidates_sent_to_openai": count,
                "descriptions_generated": descriptions,
                "average_seconds_per_candidate": round(total_processing_seconds / count, 6) if count else 0,
            },
            "category_distribution": distribution,
            "performance": {
                "frame_extraction_seconds": round(extraction_seconds, 6),
                "ai_calls_seconds": round(observation.ai_seconds, 6),
                "local_validation_seconds": round(observation.validation_seconds, 6),
                "total_processing_seconds": round(total_processing_seconds, 6),
            },
            "candidates": candidates,
            "selection_summary": validated.get("validation_summary") or {
                "verified": len(verified),
                "candidates": len(review_candidates),
                "rejected": len(rejected),
            },
            "limitations": {
                "confidence_note": (
                    "La confidence e quella mostrata dalla pipeline corrente: una autovalutazione "
                    "OpenAI moderata dalla tassonomia locale, non una probabilita tattica calibrata."
                ),
                "measurement_scope": (
                    "Il runner replica sampling statico, euristiche browser, selettore OpenAI e "
                    "validazione correnti. Non introduce analisi di sequenza, tracking o detector."
                ),
            },
        }

        stem = Path(config.video_path).stem
        json_path = write_json_report(report, output_dir / f"{stem}_baseline.json")
        html_path = write_html_report(report, output_dir / f"{stem}_baseline.html")
        return BaselineRunResult(report=report, json_path=json_path, html_path=html_path)
