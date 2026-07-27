from __future__ import annotations

import base64
import math
from pathlib import Path

from .contracts import SampleBatch, SampledCandidate, VideoMetadata


STRICT_FOCUS_TERMS = (
    "palla inattiva",
    "palle inattive",
    "angolo",
    "corner",
    "punizion",
    "rimess",
    "costruzione dal basso",
    "prima costruzione",
    "rimessa dal fondo",
    "portiere",
)


def candidate_count_for_focus(focus: str, desired_count: int) -> int:
    normalized = str(focus or "").lower()
    if any(term in normalized for term in STRICT_FOCUS_TERMS):
        return 44
    return min(32, max(max(1, int(desired_count)) * 4, 16))


def tactical_frame_label(focus: str, green_ratio: float, white_ratio: float, edge_score: float) -> str:
    normalized = str(focus or "").lower()
    if green_ratio < 0.18:
        return "scartato: poco campo"
    if "angolo" in normalized or "corner" in normalized:
        return "candidato calcio d'angolo"
    if "punizion" in normalized and "later" in normalized:
        return "candidato punizione laterale"
    if "punizion" in normalized and "central" in normalized:
        return "candidato punizione centrale"
    if "rimess" in normalized and "lateral" in normalized:
        return "candidato rimessa laterale"
    if "rimessa dal fondo" in normalized:
        return "candidato rimessa dal fondo"
    if "costruzione dal basso" in normalized or "prima costruzione" in normalized:
        return "candidato costruzione dal basso"
    if "palle inattive" in normalized or "palla inattiva" in normalized:
        return "candidato palla inattiva"
    if "pressing" in normalized or "transizion" in normalized:
        return "azione/pressione"
    if "ampiezza" in normalized:
        return "ampiezza campo"
    if "spazio" in normalized or "repart" in normalized:
        return "spazi tra reparti"
    if "linea" in normalized:
        return "linea/reparto"
    if white_ratio > 0.018 or edge_score > 0.08:
        return "campo aperto"
    return "lettura tattica"


def _rounded(value: float) -> float:
    return round(float(value), 3)


def score_tactical_frame(image: object, timestamp: float, duration: float, focus: str) -> dict[str, float | str]:
    """Port the current browser pixel heuristic without changing its weights."""
    height, width = image.shape[:2]
    step = 8
    samples = green = white = dark = upper_green = lower_green = center_green = edge = 0
    luminance_sum = luminance_squared_sum = 0.0
    previous_luminance: float | None = None

    for y in range(0, height, step):
        for x in range(0, width, step):
            blue, green_channel, red = (int(value) for value in image[y, x][:3])
            luminance = (red + green_channel + blue) / 3
            is_green = (
                green_channel > red * 1.08
                and green_channel > blue * 1.05
                and green_channel > 45
            )
            is_white = red > 180 and green_channel > 180 and blue > 180
            samples += 1
            luminance_sum += luminance
            luminance_squared_sum += luminance * luminance
            if is_green:
                green += 1
                if y < height * 0.46:
                    upper_green += 1
                if y > height * 0.54:
                    lower_green += 1
                if width * 0.25 < x < width * 0.75:
                    center_green += 1
            if is_white:
                white += 1
            if luminance < 45:
                dark += 1
            if previous_luminance is not None and abs(luminance - previous_luminance) > 42:
                edge += 1
            previous_luminance = luminance

    divisor = max(1, samples)
    green_ratio = green / divisor
    white_ratio = white / divisor
    dark_ratio = dark / divisor
    edge_score = edge / divisor
    mean_luminance = luminance_sum / divisor
    variance = max(0.0, (luminance_squared_sum / divisor) - (mean_luminance * mean_luminance))
    brightness = mean_luminance / 255
    contrast = min(1.0, math.sqrt(variance) / 96)
    sharpness = min(1.0, edge_score * 5.5)
    visual_information = min(1.0, (edge_score * 4) + (green_ratio * 0.45) + (white_ratio * 2))
    vertical_balance = 1 - abs(upper_green - lower_green) / max(1, green)
    center_pitch = center_green / max(1, green)
    closeup_penalty = 42 if green_ratio < 0.18 else 18 if green_ratio < 0.28 else 0
    overlay_penalty = 8 if dark_ratio > 0.28 else 0
    early_late_penalty = 8 if timestamp < duration * 0.03 or timestamp > duration * 0.97 else 0
    normalized = str(focus or "").lower()

    if any(term in normalized for term in ("angolo", "corner", "punizion", "rimess", "palla inattiva")):
        focus_bonus = green_ratio * 58 + white_ratio * 500 + edge_score * 85 + vertical_balance * 18
    elif any(term in normalized for term in ("costruzione dal basso", "prima costruzione", "portiere")):
        focus_bonus = (
            green_ratio * 52
            + white_ratio * 380
            + edge_score * 80
            + vertical_balance * 22
            + center_pitch * 12
        )
    elif any(term in normalized for term in ("linea", "difens", "offens", "centrocampo")):
        focus_bonus = green_ratio * 48 + white_ratio * 420 + vertical_balance * 18 + center_pitch * 10
    elif "ampiezza" in normalized:
        focus_bonus = green_ratio * 55 + vertical_balance * 18 + (1 - abs(center_pitch - 0.48)) * 18
    elif "spazio" in normalized or "repart" in normalized:
        focus_bonus = green_ratio * 52 + vertical_balance * 24 + edge_score * 90
    elif "pressing" in normalized or "transizion" in normalized:
        focus_bonus = green_ratio * 36 + edge_score * 115 + white_ratio * 220
    else:
        focus_bonus = green_ratio * 45 + white_ratio * 250 + edge_score * 65 + vertical_balance * 12

    score = focus_bonus - closeup_penalty - overlay_penalty - early_late_penalty
    visual_hash = "-".join(
        str(round(value * 20))
        for value in (green_ratio, white_ratio, dark_ratio, edge_score, brightness, contrast)
    )
    return {
        "score": score,
        "green_ratio": _rounded(green_ratio),
        "white_ratio": _rounded(white_ratio),
        "black_ratio": _rounded(dark_ratio),
        "dark_ratio": _rounded(dark_ratio),
        "edge_score": _rounded(edge_score),
        "brightness": _rounded(brightness),
        "contrast": _rounded(contrast),
        "sharpness": _rounded(sharpness),
        "blur": _rounded(1 - sharpness),
        "visual_information": _rounded(visual_information),
        "scene_stability": _rounded(max(0.0, 1 - min(1.0, edge_score * 2.4))),
        "visual_hash": visual_hash,
        "label": tactical_frame_label(focus, green_ratio, white_ratio, edge_score),
    }


class CurrentPipelineSampler:
    """Reproduce the current browser sampling and JPEG extraction in Python."""

    def sample(self, video_path: Path, *, focus: str, desired_count: int) -> SampleBatch:
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError(
                "OpenCV non disponibile. Installa soltanto le dipendenze development gia dichiarate."
            ) from exc

        path = Path(video_path)
        if not path.is_file():
            raise ValueError(f"Video non trovato: {path}")
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            capture.release()
            raise ValueError(f"Video non apribile: {path}")

        try:
            fps = float(capture.get(cv2.CAP_PROP_FPS))
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            if fps <= 0 or width <= 0 or height <= 0 or frame_count <= 0:
                raise ValueError("Metadati video non validi o codec non supportato")
            duration = frame_count / fps
            count = candidate_count_for_focus(focus, desired_count)
            ratio = min(1.0, 720 / width)
            target_width = max(1, round(width * ratio))
            target_height = max(1, round(height * ratio))
            candidates: list[SampledCandidate] = []

            for index in range(count):
                timestamp = duration * ((index + 1) / (count + 1))
                capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
                ok, image = capture.read()
                if not ok:
                    continue
                if image.shape[1] != target_width or image.shape[0] != target_height:
                    image = cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_AREA)
                metadata = score_tactical_frame(image, timestamp, duration, focus)
                encoded, buffer = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 72])
                if not encoded:
                    continue
                jpeg_bytes = bytes(buffer)
                data_url = "data:image/jpeg;base64," + base64.b64encode(jpeg_bytes).decode("ascii")
                candidates.append(
                    SampledCandidate(
                        index=index,
                        # The browser sends Math.round(t) to the selector.
                        timestamp_seconds=float(math.floor(timestamp + 0.5)),
                        jpeg_bytes=jpeg_bytes,
                        data_url=data_url,
                        local_metadata=metadata,
                    )
                )
        finally:
            capture.release()

        return SampleBatch(
            video=VideoMetadata(
                file_name=path.name,
                path=str(path.resolve()),
                duration_seconds=round(duration, 6),
                fps=round(fps, 6),
                width=width,
                height=height,
                frame_count=frame_count,
            ),
            candidates=tuple(candidates),
        )
