from __future__ import annotations

import json
import os
import platform
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

from ..contracts import AdapterResult, CalibrationFrame, CalibrationStatus
from .base import ExternalCalibrationError


class TVCalibAdapter:
    """Subprocess boundary for an independently installed TVCalib runtime.

    MatchIQ deliberately does not vendor TVCalib, its segmentation submodule, or
    its weights. The external command must emit one JSON object on stdout using
    the MatchIQ adapter fields consumed below.
    """

    name = "tvcalib"
    version = "upstream-1222c5230af2742395d74918ed6f34eb2b9bf7f9"

    def __init__(
        self,
        command: Sequence[str] | None = None,
        *,
        timeout_seconds: float = 180.0,
        upstream_root: Path | None = None,
        checkpoint: Path | None = None,
    ) -> None:
        configured = os.environ.get("MATCHIQ_TVCALIB_COMMAND", "")
        self.command = tuple(command or (shlex.split(configured) if configured else ()))
        self.timeout_seconds = timeout_seconds
        self.upstream_root = Path(upstream_root).resolve() if upstream_root else None
        self.checkpoint = Path(checkpoint).resolve() if checkpoint else None

    def inspect_environment(self) -> dict[str, Any]:
        reasons: list[str] = []
        if not self.command:
            reasons.append("MATCHIQ_TVCALIB_COMMAND is not configured")
        if self.upstream_root is not None and not self.upstream_root.exists():
            reasons.append("configured upstream root does not exist")
        if self.checkpoint is not None and not self.checkpoint.exists():
            reasons.append("configured checkpoint does not exist")
        runtime = _runtime_versions()
        return {
            "adapter": self.name,
            "adapter_version": self.version,
            "ready": not reasons,
            "command_configured": bool(self.command),
            "upstream_root": str(self.upstream_root) if self.upstream_root else None,
            "checkpoint": str(self.checkpoint) if self.checkpoint else None,
            "blocking_reasons": reasons,
            "runtime": runtime,
            "device": runtime.get("torch_device", "unknown"),
            "license_gate": {
                "tvcalib_code": "MIT",
                "segmentation_submodule": "UNVERIFIED_NO_LICENSE_FILE",
                "checkpoint": "UNVERIFIED_NO_SEPARATE_TERMS_FOUND",
            },
        }

    def calibrate(self, frame: CalibrationFrame) -> AdapterResult:
        environment = self.inspect_environment()
        if not environment["ready"]:
            raise ExternalCalibrationError("; ".join(environment["blocking_reasons"]))

        command = [*self.command, "--image", str(frame.image_path), "--json-stdout"]
        try:
            completed = subprocess.run(
                command,
                cwd=self.upstream_root,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise ExternalCalibrationError(
                f"TVCalib subprocess exceeded {self.timeout_seconds:.0f}s"
            ) from exc
        if completed.returncode != 0:
            message = completed.stderr.strip() or "TVCalib subprocess failed"
            raise ExternalCalibrationError(message[-1000:])
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ExternalCalibrationError("TVCalib bridge did not emit valid JSON") from exc
        return self._parse_result(payload)

    @staticmethod
    def _parse_result(payload: dict[str, Any]) -> AdapterResult:
        status_raw = str(payload.get("status", CalibrationStatus.ESTIMATED.value))
        try:
            status = CalibrationStatus(status_raw)
        except ValueError:
            status = CalibrationStatus.ESTIMATED
        return AdapterResult(
            status=status,
            homography_image_to_pitch=payload.get("homography_image_to_pitch"),
            homography_pitch_to_image=payload.get("homography_pitch_to_image"),
            camera_parameters=payload.get("camera_parameters"),
            model_confidence=_number(payload.get("model_confidence")),
            reprojection_error_px=_number(payload.get("reprojection_error_px")),
            coverage_score=_number(payload.get("coverage_score")),
            valid_image_region=(
                dict(payload["valid_image_region"])
                if isinstance(payload.get("valid_image_region"), dict)
                else None
            ),
            calibration_origin=str(payload.get("calibration_origin") or "tvcalib"),
            detected_field_elements=tuple(payload.get("detected_field_elements") or ()),
            ambiguity_flags=tuple(str(item) for item in payload.get("ambiguity_flags") or ()),
            failure_reason=payload.get("failure_reason"),
            diagnostics=dict(payload.get("diagnostics") or {}),
        )


def _number(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _runtime_versions() -> dict[str, Any]:
    result: dict[str, Any] = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "memory_measurement": "unavailable (psutil is not a declared dependency)",
    }
    for module_name in ("numpy", "cv2", "torch", "torchvision"):
        try:
            module = __import__(module_name)
            result[module_name] = getattr(module, "__version__", "unknown")
        except Exception:
            result[module_name] = None
    try:
        import torch

        result["torch_cuda_available"] = bool(torch.cuda.is_available())
        result["torch_device"] = (
            torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
        )
    except Exception:
        result["torch_cuda_available"] = False
        result["torch_device"] = "unavailable"
    return result
