from __future__ import annotations

import time
from typing import Any, Callable

from .contracts import SampleBatch, SelectionObservation


class CurrentPipelineSelector:
    """Thin observer around the current OpenAI selector and taxonomy validator."""

    def __init__(self, clock: Callable[[], float] = time.perf_counter) -> None:
        self.clock = clock

    def select(
        self,
        batch: SampleBatch,
        *,
        focus: str,
        desired_count: int,
        context: dict[str, Any],
    ) -> SelectionObservation:
        from app.routers.video import (
            MAX_FRAMES,
            FrameSelectionRequest,
            _call_openai_frame_selector,
            _clean_text,
            _normalize_frame_grade,
            _normalize_line_suggestions,
            _normalize_set_piece_type,
        )
        from app.services.video_taxonomy import validate_selection_result

        request = FrameSelectionRequest(
            video_asset_id=None,
            focus=focus,
            observed_team=context.get("observed_team", ""),
            home_team=context.get("home_team", ""),
            away_team=context.get("away_team", ""),
            home_formation=context.get("home_formation", ""),
            away_formation=context.get("away_formation", ""),
            lineup_notes=context.get("lineup_notes", ""),
            duration_seconds=batch.video.duration_seconds,
            frame_times=[item.timestamp_seconds for item in batch.candidates],
            frame_meta=[item.local_metadata for item in batch.candidates],
            desired_count=desired_count,
            frames=[item.data_url for item in batch.candidates],
        )

        ai_started = self.clock()
        raw_result = _call_openai_frame_selector(request, request.frames)
        ai_seconds = self.clock() - ai_started

        validation_started = self.clock()
        normalized_notes = []
        for note in raw_result.get("frame_notes") or []:
            try:
                index = int(note.get("index"))
            except (AttributeError, TypeError, ValueError):
                continue
            try:
                quality = int(float(note.get("quality", 0) or 0))
            except (TypeError, ValueError):
                quality = 0
            phase = _clean_text(note.get("phase") or note.get("camera") or "selezione AI", 80)
            set_piece_type = _normalize_set_piece_type(note.get("set_piece_type", ""), phase)
            if set_piece_type and phase.lower().startswith("palla inattiva"):
                phase = set_piece_type
            normalized_notes.append(
                {
                    "index": index,
                    "label": phase,
                    "phase": phase,
                    "set_piece_type": set_piece_type,
                    "grade": _normalize_frame_grade(note.get("grade", ""), quality, phase),
                    "grade_reason": _clean_text(note.get("grade_reason", ""), 180),
                    "quality": quality,
                    "ai_quality": quality,
                    "ai_reason": _clean_text(note.get("reason", ""), 220),
                    "reason": _clean_text(note.get("reason", ""), 220),
                    "restart_type": _clean_text(note.get("restart_type", ""), 40),
                    "restart_side": _clean_text(note.get("restart_side", ""), 40),
                    "field_zone": _clean_text(note.get("field_zone", ""), 60),
                    "ball_state": _clean_text(note.get("ball_state", ""), 40),
                    "visual_signals": [
                        _clean_text(item, 90) for item in note.get("visual_signals", [])[:8]
                    ] if isinstance(note.get("visual_signals"), list) else [],
                    "missing_signals": [
                        _clean_text(item, 90) for item in note.get("missing_signals", [])[:8]
                    ] if isinstance(note.get("missing_signals"), list) else [],
                    "evidence": _clean_text(note.get("evidence", ""), 220),
                    "team_colors": note.get("team_colors")
                    if isinstance(note.get("team_colors"), list) else [],
                    "visible_numbers": note.get("visible_numbers")
                    if isinstance(note.get("visible_numbers"), list) else [],
                    "player_read": _clean_text(note.get("player_read", ""), 180),
                    "line_suggestions": _normalize_line_suggestions(
                        note.get("line_suggestions") or []
                    ),
                }
            )
        normalized_result = dict(raw_result)
        normalized_result["frame_notes"] = normalized_notes
        effective_count = max(2, min(MAX_FRAMES, int(desired_count or MAX_FRAMES)))
        validated = validate_selection_result(
            normalized_result,
            request,
            len(request.frames),
            min(effective_count, len(request.frames)),
        )
        validation_seconds = self.clock() - validation_started
        return SelectionObservation(
            raw_result=raw_result,
            validated_result=validated,
            ai_seconds=ai_seconds,
            validation_seconds=validation_seconds,
        )
