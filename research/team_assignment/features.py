from __future__ import annotations

from dataclasses import dataclass

from .roi import TorsoRoi


@dataclass(frozen=True, slots=True)
class ColorFeature:
    vector: tuple[float, ...] | None
    dominant_color: dict[str, object] | None
    roi_report: dict[str, object]
    quality: float
    reason: str | None


def _hex_color(bgr: object) -> str:
    blue, green, red = (int(round(float(value))) for value in bgr)
    return f"#{red:02X}{green:02X}{blue:02X}"


def build_color_feature(torso: TorsoRoi, *, detection_confidence: float) -> ColorFeature:
    if torso.image is None:
        return ColorFeature(
            None,
            None,
            torso.as_report(),
            0.0,
            torso.reason or "torso_roi_unavailable",
        )

    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("OpenCV and NumPy are required by VE-003") from exc

    crop = torso.image
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)

    green_mask = (
        (hsv[:, :, 0] >= 28)
        & (hsv[:, :, 0] <= 100)
        & (hsv[:, :, 1] >= 38)
        & (hsv[:, :, 2] >= 18)
    )
    valid_mask = ~green_mask
    valid_count = int(np.count_nonzero(valid_mask))
    total_count = int(valid_mask.size)
    coverage = valid_count / max(total_count, 1)
    minimum_valid = max(16, int(total_count * 0.22))
    if valid_count < minimum_valid:
        report = torso.as_report(valid_pixels=valid_count, coverage=coverage)
        report["status"] = "excluded"
        report["reason"] = "insufficient_non_grass_pixels"
        return ColorFeature(None, None, report, 0.0, "insufficient_non_grass_pixels")

    bgr_pixels = crop[valid_mask].reshape(-1, 3).astype(np.float32)
    hsv_pixels = hsv[valid_mask].reshape(-1, 3).astype(np.float32)
    lab_pixels = lab[valid_mask].reshape(-1, 3).astype(np.float32)

    lab_median = np.median(lab_pixels, axis=0) / 255.0
    lab_q25 = np.percentile(lab_pixels, 25, axis=0) / 255.0
    lab_q75 = np.percentile(lab_pixels, 75, axis=0) / 255.0
    saturation = hsv_pixels[:, 1] / 255.0
    value = hsv_pixels[:, 2] / 255.0

    chromatic = (hsv_pixels[:, 1] >= 45) & (hsv_pixels[:, 2] >= 65)
    hue_histogram = np.zeros(8, dtype=np.float32)
    if np.any(chromatic):
        hue_values = hsv_pixels[chromatic, 0]
        hue_weights = 0.25 + (hsv_pixels[chromatic, 1] / 255.0)
        hue_histogram, _ = np.histogram(
            hue_values,
            bins=8,
            range=(0.0, 180.0),
            weights=hue_weights,
        )
        histogram_total = float(hue_histogram.sum())
        if histogram_total > 0.0:
            hue_histogram /= histogram_total

    red_fraction = float(np.mean(
        (
            ((hsv_pixels[:, 0] <= 12) | (hsv_pixels[:, 0] >= 168))
            & (hsv_pixels[:, 1] >= 55)
            & (hsv_pixels[:, 2] >= 65)
        )
    ))
    blue_fraction = float(np.mean(
        (
            (hsv_pixels[:, 0] >= 92)
            & (hsv_pixels[:, 0] <= 135)
            & (hsv_pixels[:, 1] >= 55)
            & (hsv_pixels[:, 2] >= 65)
        )
    ))
    white_fraction = float(np.mean((hsv_pixels[:, 1] <= 48) & (hsv_pixels[:, 2] >= 172)))
    black_fraction = float(np.mean(hsv_pixels[:, 2] <= 68))

    # Jersey identity must outweigh illumination. Raw LAB quartiles otherwise
    # tend to group distant white kits together even when their accent colors
    # clearly differ.
    vector = np.concatenate([
        lab_median * 0.15,
        lab_q25 * 0.10,
        lab_q75 * 0.10,
        np.array([
            float(np.median(saturation)),
            float(np.median(value)),
            float(np.mean(value <= 0.25)),
            float(np.mean(value >= 0.75)),
        ], dtype=np.float32) * 0.25,
        hue_histogram * 4.00,
        np.array([
            red_fraction * 10.00,
            blue_fraction * 10.00,
            white_fraction * 0.50,
            black_fraction * 6.00,
        ], dtype=np.float32),
    ])

    median_bgr = np.median(bgr_pixels, axis=0)
    median_hsv = np.median(hsv_pixels, axis=0)
    median_lab_raw = np.median(lab_pixels, axis=0)
    size_quality = min(1.0, (valid_count ** 0.5) / 20.0)
    coverage_quality = min(1.0, coverage / 0.70)
    quality = max(0.0, min(
        1.0,
        (0.40 * size_quality + 0.35 * coverage_quality + 0.25 * float(detection_confidence)),
    ))
    report = torso.as_report(valid_pixels=valid_count, coverage=coverage)
    return ColorFeature(
        tuple(round(float(value), 8) for value in vector.tolist()),
        {
            "hex": _hex_color(median_bgr),
            "bgr_median": [round(float(value), 3) for value in median_bgr],
            "hsv_median": [round(float(value), 3) for value in median_hsv],
            "lab_median": [round(float(value), 3) for value in median_lab_raw],
        },
        report,
        round(quality, 6),
        None,
    )
