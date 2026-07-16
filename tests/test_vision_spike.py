from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from research.vision_spike.cli import build_parser
from research.vision_spike.config import TrackerSettings, VisionSpikeConfig
from research.vision_spike.contracts import Detection, FrameResult, RunManifest, Track
from research.vision_spike.detector import OpenCvHogPersonDetector, VisionDetector
from research.vision_spike.evaluator import MetricsCollector, write_evaluation
from research.vision_spike.make_clip import make_clip
from research.vision_spike.overlay import VideoOverlayWriter, draw_overlay, format_timestamp
from research.vision_spike.pipeline import run_pipeline
from research.vision_spike.pitch_detector import PitchDetector
from research.vision_spike.team_classifier import OnlineTeamClassifier, extract_team_color_feature
from research.vision_spike.tracker import IoUTracker, bbox_iou
from research.vision_spike.utils import ensure_writable_directory, require_cv2_numpy, write_json
from research.vision_spike.video_reader import LocalVideoReader


ROOT = Path(__file__).resolve().parents[1]


class FakeDetector(VisionDetector):
    def __init__(self, *, fail_on_load: bool = False) -> None:
        self.loaded = False
        self.closed = False
        self.fail_on_load = fail_on_load

    def load(self) -> None:
        if self.fail_on_load:
            raise RuntimeError("synthetic model unavailable")
        self.loaded = True

    def detect(self, frame, *, frame_index: int, timestamp_seconds: float):
        return [
            Detection(
                frame_index=frame_index,
                timestamp_seconds=timestamp_seconds,
                class_id=0,
                class_name="person",
                confidence=0.9,
                bbox_xyxy=(20.0, 15.0, 55.0, 90.0),
                source_model="fake",
                detection_id=f"fake-{frame_index}",
            )
        ]

    def close(self) -> None:
        self.closed = True

    def metadata(self):
        return {"backend": "fake", "model": "synthetic", "device": "cpu"}


def create_video(path: Path, *, frames: int = 12, fps: float = 6.0) -> None:
    cv2, np = require_cv2_numpy()
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (160, 96))
    if not writer.isOpened():
        raise RuntimeError("test video writer unavailable")
    for index in range(frames):
        image = np.zeros((96, 160, 3), dtype=np.uint8)
        image[:, :] = (25, 125, 35)
        cv2.rectangle(image, (20 + index, 15), (55 + index, 90), (15, 15, 220), -1)
        writer.write(image)
    writer.release()


class VisionSpikeUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.video = self.root / "input.mp4"
        create_video(self.video)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def config(self, **changes) -> VisionSpikeConfig:
        values = {
            "input_video": self.video,
            "output_dir": self.root / "output",
            "detector_backend": "fake",
            "frame_stride": 2,
            "max_seconds": 2.0,
            "overlay_enabled": False,
            "team_clustering_enabled": False,
        }
        values.update(changes)
        return VisionSpikeConfig(**values)

    def test_01_valid_config(self):
        self.config().validate()

    def test_02_missing_input_rejected(self):
        with self.assertRaisesRegex(ValueError, "input video not found"):
            self.config(input_video=self.root / "missing.mp4").validate()

    def test_03_invalid_stride_rejected(self):
        with self.assertRaisesRegex(ValueError, "frame_stride"):
            self.config(frame_stride=0).validate()

    def test_04_invalid_device_rejected(self):
        with self.assertRaisesRegex(ValueError, "device"):
            self.config(device="tpu").validate()

    def test_05_tracker_settings_validation(self):
        with self.assertRaises(ValueError):
            TrackerSettings(iou_threshold=1.2).validate()

    def test_06_detection_serialization(self):
        item = FakeDetector().detect(None, frame_index=1, timestamp_seconds=0.2)[0].to_dict()
        self.assertEqual(item["contract_version"], "vision-spike.v1")
        self.assertIsInstance(item["bbox_xyxy"], list)

    def test_07_track_serialization(self):
        item = Track(1, 2, 0.4, (1, 2, 3, 4), "person", 0.8, 2, 0).to_dict()
        self.assertEqual(item["track_id"], 1)

    def test_08_frame_result_serialization(self):
        result = FrameResult(1, 0.1, [], [], 4.0, True)
        self.assertEqual(result.to_dict()["detections"], [])

    def test_09_manifest_serialization(self):
        manifest = RunManifest("a", "b")
        self.assertEqual(manifest.to_dict()["status"], "pending")

    def test_10_iou_identity(self):
        self.assertEqual(bbox_iou((0, 0, 10, 10), (0, 0, 10, 10)), 1.0)

    def test_11_iou_disjoint(self):
        self.assertEqual(bbox_iou((0, 0, 2, 2), (3, 3, 5, 5)), 0.0)

    def test_12_tracker_creates_temporary_id(self):
        tracker = IoUTracker(min_hits=1)
        tracks = tracker.update(FakeDetector().detect(None, frame_index=1, timestamp_seconds=0.0), frame_index=1, timestamp_seconds=0.0)
        self.assertEqual(tracks[0].track_id, 1)

    def test_13_tracker_keeps_id_on_overlap(self):
        tracker = IoUTracker(min_hits=1)
        detector = FakeDetector()
        first = tracker.update(detector.detect(None, frame_index=1, timestamp_seconds=0.0), frame_index=1, timestamp_seconds=0.0)
        second = tracker.update(detector.detect(None, frame_index=2, timestamp_seconds=0.1), frame_index=2, timestamp_seconds=0.1)
        self.assertEqual(first[0].track_id, second[0].track_id)

    def test_14_reader_metadata(self):
        with LocalVideoReader(self.video) as reader:
            self.assertEqual(reader.metadata.width, 160)

    def test_15_reader_stride(self):
        with LocalVideoReader(self.video, frame_stride=3) as reader:
            indices = [item.frame_index for item in reader.frames()]
        self.assertEqual(indices[:3], [0, 3, 6])

    def test_16_reader_max_frames(self):
        with LocalVideoReader(self.video, max_frames=2) as reader:
            self.assertEqual(len(list(reader.frames())), 2)

    def test_17_reader_releases_capture(self):
        reader = LocalVideoReader(self.video)
        reader.open()
        reader.close()
        self.assertIsNone(reader._capture)

    def test_18_timestamp_format(self):
        self.assertEqual(format_timestamp(65.2), "01:05")

    def test_19_pitch_green_frame(self):
        cv2, np = require_cv2_numpy()
        frame = np.full((100, 160, 3), (30, 140, 30), dtype=np.uint8)
        result = PitchDetector().analyze(frame)
        self.assertTrue(result.pitch_visible)

    def test_20_pitch_dark_frame_not_visible(self):
        _, np = require_cv2_numpy()
        result = PitchDetector().analyze(np.zeros((100, 160, 3), dtype=np.uint8))
        self.assertFalse(result.pitch_visible)

    def test_21_team_feature_from_torso(self):
        _, np = require_cv2_numpy()
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[10:70, 20:80] = (0, 0, 220)
        self.assertIsNotNone(extract_team_color_feature(frame, (20, 10, 80, 90)))

    def test_22_team_classifier_disabled_is_unknown(self):
        _, np = require_cv2_numpy()
        assignment = OnlineTeamClassifier(enabled=False).classify(np.zeros((40, 40, 3), dtype=np.uint8), (0, 0, 20, 30))
        self.assertEqual(assignment.team_id, "unknown")

    def test_23_overlay_preserves_shape(self):
        _, np = require_cv2_numpy()
        frame = np.zeros((96, 160, 3), dtype=np.uint8)
        output = draw_overlay(frame, detections=[], tracks=[], frame_index=1, timestamp_seconds=0.0, processing_fps=1.0, pitch_visible=False, green_ratio=0.0)
        self.assertEqual(output.shape, frame.shape)

    def test_24_overlay_writer_creates_file(self):
        _, np = require_cv2_numpy()
        path = self.root / "overlay.mp4"
        writer = VideoOverlayWriter(path, width=160, height=96, fps=2.0)
        writer.write(np.zeros((96, 160, 3), dtype=np.uint8))
        writer.close()
        self.assertGreater(path.stat().st_size, 0)

    def test_25_json_writer_is_valid(self):
        path = self.root / "value.json"
        write_json(path, {"ok": True})
        self.assertTrue(json.loads(path.read_text(encoding="utf-8"))["ok"])

    def test_26_output_directory_probe(self):
        path = self.root / "writable"
        ensure_writable_directory(path)
        self.assertTrue(path.is_dir())

    def test_27_pipeline_outputs_contracts(self):
        result = run_pipeline(self.config(), detector=FakeDetector())
        self.assertEqual(result.status, "completed")
        for name in ("detections.json", "tracks.json", "frames.json", "metrics.json", "run_manifest.json", "evaluation.md"):
            self.assertTrue((self.root / "output" / name).exists(), name)

    def test_28_pipeline_cpu_fallback(self):
        result = run_pipeline(self.config(device="cuda"), detector=FakeDetector())
        self.assertEqual(result.metrics["device"], "cpu")
        self.assertIn("CPU fallback", result.metrics["warnings"][0])

    def test_29_pipeline_cancellation(self):
        result = run_pipeline(self.config(), detector=FakeDetector(), should_cancel=lambda: True)
        self.assertEqual(result.status, "cancelled")

    def test_30_model_failure_writes_manifest(self):
        with self.assertRaisesRegex(RuntimeError, "model unavailable"):
            run_pipeline(self.config(), detector=FakeDetector(fail_on_load=True))
        manifest = json.loads((self.root / "output" / "run_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "failed")

    def test_31_ball_is_never_invented(self):
        result = run_pipeline(self.config(ball_detection_enabled=True), detector=FakeDetector())
        self.assertFalse(result.metrics["ball_detection"]["supported"])
        self.assertEqual(result.metrics["ball_detection"]["detections"], 0)

    def test_32_pipeline_is_deterministic_for_counts(self):
        first = run_pipeline(self.config(output_dir=self.root / "one"), detector=FakeDetector())
        second = run_pipeline(self.config(output_dir=self.root / "two"), detector=FakeDetector())
        self.assertEqual(first.metrics["processed_frames"], second.metrics["processed_frames"])
        self.assertEqual(first.metrics["tracks_total"], second.metrics["tracks_total"])

    def test_33_cli_requires_input_and_output(self):
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([])

    def test_34_cli_help_is_available(self):
        completed = subprocess.run(
            [str(Path(__import__("sys").executable)), "-m", "research.vision_spike.cli", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertIn("feasibility spike", completed.stdout)

    def test_35_hog_detector_metadata_is_honest(self):
        detector = OpenCvHogPersonDetector()
        detector.load()
        self.assertFalse(detector.metadata()["ball_supported"])
        detector.close()

    def test_36_evaluation_declares_no_ground_truth(self):
        path = self.root / "evaluation.md"
        write_evaluation(path, {}, [])
        self.assertIn("No precision or recall", path.read_text(encoding="utf-8"))

    def test_37_metrics_do_not_claim_accuracy(self):
        metrics = MetricsCollector().finalize(elapsed_seconds=1.0, tracker_metadata={}, team_metadata={}, device="cpu")
        self.assertIn("no annotated ground truth", metrics["accuracy_note"].lower())

    def test_38_no_product_route_imports_spike(self):
        product_files = [ROOT / "main.py", *list((ROOT / "app" / "routers").glob("*.py"))]
        self.assertFalse(any("research.vision_spike" in path.read_text(encoding="utf-8", errors="ignore") for path in product_files))

    def test_39_no_database_import_in_spike(self):
        source = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "research" / "vision_spike").glob("*.py"))
        for forbidden in ("sqlalchemy", "SessionLocal", "DATABASE_URL"):
            self.assertNotIn(forbidden, source)

    def test_40_no_committed_video_or_weights_in_spike(self):
        forbidden = {".mp4", ".mov", ".avi", ".pt", ".onnx", ".weights"}
        self.assertFalse(any(path.suffix.lower() in forbidden for path in (ROOT / "research" / "vision_spike").rglob("*")))

    def test_41_make_clip_rejects_missing_source(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            make_clip(self.root / "missing.mp4", self.root / "clip.mp4", start_seconds=0, duration_seconds=1)

    def test_42_pipeline_closes_detector(self):
        detector = FakeDetector()
        run_pipeline(self.config(), detector=detector)
        self.assertTrue(detector.closed)


if __name__ == "__main__":
    unittest.main()
