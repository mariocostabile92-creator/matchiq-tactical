from __future__ import annotations

from typing import Iterable

from ..utils import require_cv2_numpy


def blur_score(frame: object) -> float:
    cv2, _ = require_cv2_numpy()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def mean_luma(frame: object) -> float:
    cv2, _ = require_cv2_numpy()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(gray.mean())


def difference_hash(frame: object) -> int:
    cv2, _ = require_cv2_numpy()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    bits = resized[:, 1:] > resized[:, :-1]
    value = 0
    for bit in bits.flatten():
        value = (value << 1) | int(bit)
    return value


def hamming_distance(first: int, second: int) -> int:
    return (first ^ second).bit_count()


def is_near_duplicate(candidate: int, previous: Iterable[int], max_distance: int) -> bool:
    return any(hamming_distance(candidate, item) <= max_distance for item in previous)


def infer_quality(width: int, height: int) -> str:
    pixels = width * height
    if pixels >= 1920 * 1080:
        return "high_1080p_or_above"
    if pixels >= 1280 * 720:
        return "medium_720p"
    return "low_below_720p"


def infer_lighting(luma: float) -> str:
    if luma < 55:
        return "low_light"
    if luma > 185:
        return "bright"
    return "normal"
