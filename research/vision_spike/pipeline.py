from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .config import VisionSpikeConfig
from .contracts import FrameResult, RunManifest, utc_now
from .detector import VisionDetector, build_detector
from .evaluator import EvaluationSampler, MetricsCollector, write_evaluation
from .inference_modes import TiledInferenceDetector
from .overlay import VideoOverlayWriter, draw_overlay
from .pitch_detector import PitchDetector
from .team_classifier import OnlineTeamClassifier
from .tracker import IoUTracker, ObjectTracker
from .utils import ensure_writable_directory, require_cv2_numpy, runtime_versions, sha256_file, write_json, write_jsonl
from .video_reader import LocalVideoReader


@dataclass(slots=True)
class PipelineResult:
    status: str
    output_dir: Path
    metrics: dict
    manifest: dict


def _expected_frames(config: VisionSpikeConfig, source_fps: float) -> int:
    seconds = config.max_seconds
    expected = int((seconds * source_fps) / config.frame_stride) + 1
    if config.max_frames is not None:
        expected = min(expected, config.max_frames)
    return max(1, expected)


def _resolve_device(requested: str, detector_backend: str) -> tuple[str, list[str]]:
    if detector_backend == "rfdetr":
        if requested == "cpu":
            return "cpu", []
        try:
            import torch

            available = bool(torch.cuda.is_available())
        except ImportError:
            available = False
        if available:
            return "cuda", []
        warning = "CUDA requested but unavailable; RF-DETR CPU fallback used."
        return "cpu", [warning] if requested == "cuda" else []
    if requested == "cuda":
        return "cpu", ["CUDA requested but the V0 detector has no CUDA adapter; CPU fallback used."]
    if requested == "auto":
        return "cpu", ["V0 uses the deterministic CPU baseline; GPU was not used."]
    return "cpu", []


def run_pipeline(
    config: VisionSpikeConfig,
    *,
    detector: VisionDetector | None = None,
    tracker: ObjectTracker | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> PipelineResult:
    config.validate()
    ensure_writable_directory(config.output_dir)
    device, warnings = _resolve_device(config.device, config.detector_backend)
    manifest = RunManifest(
        input_file=str(config.input_video.resolve()),
        output_dir=str(config.output_dir.resolve()),
        device=device,
        versions=runtime_versions(),
        status="loading_model",
    )
    manifest_path = config.output_dir / "run_manifest.json"
    write_json(manifest_path, manifest.to_dict())

    if detector is not None:
        detector_instance = detector
    elif config.detector_backend == "rfdetr":
        detector_instance = build_detector(
            "rfdetr",
            model_size=config.model_size,
            model_path=config.model_path,
            confidence_threshold=config.confidence_threshold,
            input_resolution=config.input_resolution,
            device=config.device,
            class_mapping=config.class_mapping,
            batch_size=config.batch_size,
            half_precision=config.half_precision,
            max_detections=config.max_detections,
            inference_mode=config.inference_mode,
        )
        if config.inference_mode == "tiled":
            detector_instance = TiledInferenceDetector(
                detector_instance,
                tile_size=config.tile_size,
                overlap=config.tile_overlap,
                nms_iou_threshold=config.iou_threshold,
                max_detections=config.max_detections,
            )
    else:
        detector_instance = build_detector(
            config.detector_backend,
            confidence_threshold=config.confidence_threshold,
            nms_threshold=config.iou_threshold,
            detector_width=config.detector_width,
        )
    tracker_instance = tracker or IoUTracker(
        iou_threshold=config.tracker.iou_threshold,
        max_lost=config.tracker.max_lost,
        min_hits=config.tracker.min_hits,
    )
    pitch_detector = PitchDetector()
    team_classifier = OnlineTeamClassifier(
        enabled=config.team_clustering_enabled,
        random_seed=config.random_seed,
    )
    detections_payload: list[dict] = []
    tracks_payload: list[dict] = []
    frame_payload: list[dict] = []
    metrics_collector = MetricsCollector()
    overlay_writer: VideoOverlayWriter | None = None
    reader: LocalVideoReader | None = None
    sampler: EvaluationSampler | None = None
    first_pitch_mask = None
    started = time.perf_counter()
    final_metrics: dict = {}
    status = "failed"
    cv2 = None

    def persist_partial(current_status: str, error: str | None = None) -> None:
        nonlocal final_metrics
        elapsed = max(0.0, time.perf_counter() - started)
        tracker_metadata = tracker_instance.metadata()
        team_metadata = team_classifier.metadata()
        final_metrics = metrics_collector.finalize(
            elapsed_seconds=elapsed,
            tracker_metadata=tracker_metadata,
            team_metadata=team_metadata,
            device=device,
        )
        final_metrics["warnings"] = warnings
        final_metrics["ball_detection"] = {
            "requested": config.ball_detection_enabled,
            "supported": False,
            "detections": 0,
            "note": "No ball detector is available in V0; no ball boxes were generated.",
        }
        write_json(config.output_dir / "detections.json", detections_payload)
        write_json(config.output_dir / "tracks.json", tracks_payload)
        write_jsonl(config.output_dir / "detections.jsonl", detections_payload)
        write_jsonl(config.output_dir / "tracks.jsonl", tracks_payload)
        write_json(config.output_dir / "frames.json", frame_payload)
        write_json(config.output_dir / "metrics.json", final_metrics)
        write_json(config.output_dir / "team_clusters.json", team_metadata)
        manifest.processed_frames = len(frame_payload)
        manifest.status = current_status
        manifest.error = error
        manifest.completed_at = utc_now()
        manifest.partial_outputs = sorted(
            path.name for path in config.output_dir.iterdir() if path.is_file() and path != manifest_path
        )
        write_json(manifest_path, manifest.to_dict())

    try:
        cv2, _ = require_cv2_numpy()
        detector_instance.load()
        detector_metadata = detector_instance.metadata()
        warnings.extend(item for item in detector_metadata.get("warnings", []) if item not in warnings)
        manifest.model = detector_metadata.get("model", "unknown")
        manifest.status = "processing"
        write_json(manifest_path, manifest.to_dict())
        reader = LocalVideoReader(
            config.input_video,
            frame_stride=config.frame_stride,
            start_seconds=config.start_seconds,
            max_seconds=config.max_seconds,
            max_frames=config.max_frames,
        )
        metadata = reader.open()
        manifest.duration_seconds = metadata.duration_seconds
        manifest.resolution = (metadata.width, metadata.height)
        manifest.source_fps = metadata.fps
        manifest.skipped_frames = max(0, config.frame_stride - 1)
        manifest.versions["input_sha256"] = sha256_file(config.input_video)
        manifest.versions["detector"] = detector_metadata.get("backend", "unknown")
        manifest.versions["detector_metadata"] = detector_metadata
        sampler = EvaluationSampler(_expected_frames(config, metadata.fps))
        if config.overlay_enabled:
            output_fps = config.output_fps or max(0.1, metadata.fps / config.frame_stride)
            overlay_writer = VideoOverlayWriter(
                config.output_dir / "overlay.mp4",
                width=metadata.width,
                height=metadata.height,
                fps=output_fps,
            )

        for ordinal, video_frame in enumerate(reader.frames()):
            if should_cancel and should_cancel():
                status = "cancelled"
                break
            frame_started = time.perf_counter()
            pitch = pitch_detector.analyze(
                video_frame.image,
                include_mask=config.pitch_detection_enabled,
            )
            if first_pitch_mask is None and pitch.mask is not None:
                first_pitch_mask = pitch.mask.copy()
            detections = detector_instance.detect(
                video_frame.image,
                frame_index=video_frame.frame_index,
                timestamp_seconds=video_frame.timestamp_seconds,
            )
            detections = team_classifier.classify_detections(video_frame.image, detections)
            tracks = tracker_instance.update(
                detections,
                frame_index=video_frame.frame_index,
                timestamp_seconds=video_frame.timestamp_seconds,
            )
            processing_ms = (time.perf_counter() - frame_started) * 1000.0
            result = FrameResult(
                frame_index=video_frame.frame_index,
                timestamp_seconds=video_frame.timestamp_seconds,
                detections=detections,
                tracks=tracks,
                processing_ms=round(processing_ms, 4),
                pitch_visible=pitch.pitch_visible,
                green_ratio=pitch.green_ratio,
                tactical_view_score=pitch.tactical_view_score,
                debug_metadata={
                    "ordinal": ordinal,
                    "largest_green_region_ratio": pitch.largest_green_region_ratio,
                },
            )
            frame_payload.append(result.to_dict())
            detections_payload.extend(item.to_dict() for item in detections)
            tracks_payload.extend(item.to_dict() for item in tracks)
            metrics_collector.observe(result, pitch.mask)
            sampler.observe(ordinal, video_frame.image, result)
            if overlay_writer is not None:
                overlay = draw_overlay(
                    video_frame.image,
                    detections=detections,
                    tracks=tracks,
                    frame_index=video_frame.frame_index,
                    timestamp_seconds=video_frame.timestamp_seconds,
                    processing_fps=(1000.0 / processing_ms) if processing_ms > 0 else 0.0,
                    pitch_visible=pitch.pitch_visible,
                    green_ratio=pitch.green_ratio,
                )
                overlay_writer.write(overlay)
            if config.save_debug_frames and ordinal < 20:
                debug_dir = config.output_dir / "debug"
                debug_dir.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(debug_dir / f"frame_{video_frame.frame_index}.jpg"), video_frame.image)
        else:
            status = "completed"

        if status == "failed":
            status = "completed"
        if first_pitch_mask is not None and cv2 is not None:
            cv2.imwrite(str(config.output_dir / "pitch_mask.png"), first_pitch_mask)
        persist_partial(status)
        samples = sampler.save(config.output_dir / "frames") if sampler else []
        write_evaluation(config.output_dir / "evaluation.md", final_metrics, samples)
        manifest.partial_outputs = sorted(
            path.name for path in config.output_dir.iterdir() if path.is_file() and path != manifest_path
        )
        write_json(manifest_path, manifest.to_dict())
    except KeyboardInterrupt:
        status = "cancelled"
        persist_partial(status, "interrupted by user")
        if sampler:
            samples = sampler.save(config.output_dir / "frames")
            write_evaluation(config.output_dir / "evaluation.md", final_metrics, samples)
    except Exception as exc:
        status = "partial" if frame_payload else "failed"
        persist_partial(status, f"{type(exc).__name__}: {exc}")
        if sampler:
            samples = sampler.save(config.output_dir / "frames")
            write_evaluation(config.output_dir / "evaluation.md", final_metrics, samples)
        raise
    finally:
        if overlay_writer is not None:
            overlay_writer.close()
        if reader is not None:
            reader.close()
        detector_instance.close()
        tracker_instance.close()

    return PipelineResult(status, config.output_dir, final_metrics, manifest.to_dict())
