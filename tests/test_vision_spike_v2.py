from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from research.vision_spike.benchmark import aggregate_rows, build_parser as build_benchmark_parser, write_comparison
from research.vision_spike.config import VisionSpikeConfig
from research.vision_spike.contracts import Detection, FrameResult
from research.vision_spike.detector import VisionDetector
from research.vision_spike.evaluator import MetricsCollector
from research.vision_spike.inference_modes import (
    TiledInferenceDetector,
    deduplicate_detections,
    letterbox_frame,
    restore_letterbox_box,
    tile_origins,
)
from research.vision_spike.manual_evaluation import (
    ManualObservation,
    build_parser as build_manual_parser,
    create_contact_sheet,
    decision_gate,
    load_observations,
    summarize_manual_review,
)
from research.vision_spike.rfdetr_detector import RFDETRDetector, RFDETR_LICENSE, RFDETR_REPOSITORY
from research.vision_spike.utils import require_cv2_numpy


ROOT = Path(__file__).resolve().parents[1]


class StaticDetector(VisionDetector):
    def load(self) -> None:
        pass

    def detect(self, frame, *, frame_index: int, timestamp_seconds: float):
        return [
            Detection(
                frame_index,
                timestamp_seconds,
                1,
                "person",
                0.9,
                (5.0, 5.0, 25.0, 45.0),
                "fake",
                f"f{frame_index}",
            )
        ]

    def close(self) -> None:
        pass

    def metadata(self):
        return {"backend": "fake"}


class FakePrediction:
    xyxy = [(64.0, 64.0, 192.0, 320.0), (12.0, 12.0, 24.0, 24.0)]
    confidence = [0.91, 0.8]
    class_id = [1, 2]
    data = {"class_name": ["person", "car"]}


class FakeModel:
    def __init__(self) -> None:
        self.threshold = None

    def predict(self, frame, **kwargs):
        self.threshold = kwargs.get("threshold")
        return FakePrediction()


def make_video(path: Path) -> None:
    cv2, np = require_cv2_numpy()
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 5.0, (160, 96))
    if not writer.isOpened():
        raise RuntimeError("test video writer unavailable")
    for index in range(8):
        frame = np.full((96, 160, 3), (25, 125, 35), dtype=np.uint8)
        cv2.circle(frame, (20 + index * 10, 45), 8, (240, 240, 240), -1)
        writer.write(frame)
    writer.release()


class VisionSpikeV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def detection(box=(0.0, 0.0, 20.0, 40.0), confidence=0.9, identity="d") -> Detection:
        return Detection(1, 0.1, 1, "person", confidence, box, "mock", identity)

    def test_01_rfdetr_adapter_importable(self):
        self.assertTrue(issubclass(RFDETRDetector, VisionDetector))

    def test_02_missing_model_has_readable_error(self):
        detector = RFDETRDetector(model_path=self.root / "missing.pth", model_factory=lambda **_: FakeModel())
        fake_torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False))
        fake_rfdetr = types.SimpleNamespace(RFDETRSmall=object, RFDETRMedium=object)
        with patch.dict(sys.modules, {"torch": fake_torch, "rfdetr": fake_rfdetr}):
            with self.assertRaisesRegex(FileNotFoundError, "weight not found"):
                detector.load()

    def test_03_metadata_is_honest(self):
        metadata = RFDETRDetector().metadata()
        self.assertEqual(metadata["classes"], ["person"])
        self.assertFalse(metadata["roles_supported"])

    def test_04_class_mapping_does_not_invent_player(self):
        detector = RFDETRDetector(class_mapping={"person": "person"})
        detector._model = FakeModel()
        _, np = require_cv2_numpy()
        detections = detector.detect(np.zeros((360, 640, 3), dtype=np.uint8), frame_index=1, timestamp_seconds=0.0)
        self.assertEqual([item.class_name for item in detections], ["person"])

    def test_05_letterbox_coordinates_round_trip(self):
        _, np = require_cv2_numpy()
        _, scale, ox, oy = letterbox_frame(np.zeros((360, 640, 3), dtype=np.uint8), 512)
        restored = restore_letterbox_box((80 * scale + ox, 40 * scale + oy, 200 * scale + ox, 300 * scale + oy), scale=scale, offset_x=ox, offset_y=oy, original_width=640, original_height=360)
        self.assertAlmostEqual(restored[0], 80.0, places=3)
        self.assertAlmostEqual(restored[3], 300.0, places=3)

    def test_06_mock_inference_filters_non_person(self):
        detector = RFDETRDetector()
        detector._model = FakeModel()
        _, np = require_cv2_numpy()
        self.assertEqual(len(detector.detect(np.zeros((512, 512, 3), dtype=np.uint8), frame_index=1, timestamp_seconds=0.0)), 1)

    def test_07_rfdetr_output_is_serializable(self):
        detector = RFDETRDetector()
        detector._model = FakeModel()
        _, np = require_cv2_numpy()
        payload = detector.detect(np.zeros((512, 512, 3), dtype=np.uint8), frame_index=1, timestamp_seconds=0.0)[0].to_dict()
        json.dumps(payload)

    def test_08_tiled_coordinates_become_global(self):
        _, np = require_cv2_numpy()
        detector = TiledInferenceDetector(StaticDetector(), tile_size=100, overlap=0.0)
        detections = detector.detect(np.zeros((100, 200, 3), dtype=np.uint8), frame_index=1, timestamp_seconds=0.0)
        self.assertTrue(any(item.bbox_xyxy[0] >= 100 for item in detections))

    def test_09_tiled_deduplication(self):
        items = [self.detection(identity="a"), self.detection((1, 1, 21, 41), 0.8, "b")]
        self.assertEqual(len(deduplicate_detections(items, 0.5)), 1)

    def test_10_high_resolution_config(self):
        config = VisionSpikeConfig(self.root / "x.mp4", self.root / "o", detector_backend="rfdetr", input_resolution=960, inference_mode="highres")
        config.validate(require_input=False)

    def test_11_confidence_threshold_is_forwarded(self):
        model = FakeModel()
        detector = RFDETRDetector(confidence_threshold=0.37)
        detector._model = model
        _, np = require_cv2_numpy()
        detector.detect(np.zeros((512, 512, 3), dtype=np.uint8), frame_index=1, timestamp_seconds=0.0)
        self.assertEqual(model.threshold, 0.37)

    def test_12_cpu_device_resolution(self):
        detector = RFDETRDetector(device="cpu")
        fake_torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: True))
        self.assertEqual(detector._resolve_device(fake_torch), "cpu")

    def test_13_cuda_fallback(self):
        detector = RFDETRDetector(device="cuda")
        fake_torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False))
        self.assertEqual(detector._resolve_device(fake_torch), "cpu")
        self.assertTrue(detector.metadata()["warnings"])

    def test_14_configuration_is_deterministic(self):
        first = VisionSpikeConfig(self.root / "x", self.root / "o", detector_backend="rfdetr").to_dict()
        second = VisionSpikeConfig(self.root / "x", self.root / "o", detector_backend="rfdetr").to_dict()
        self.assertEqual(first, second)

    def test_15_manifest_metadata_contains_source(self):
        metadata = RFDETRDetector().metadata()
        self.assertEqual(metadata["repository"], RFDETR_REPOSITORY)
        self.assertIn("weights_source", metadata)

    def test_16_weight_hash_is_recorded(self):
        weights = self.root / "model.pth"
        weights.write_bytes(b"official-test-fixture")
        detector = RFDETRDetector(model_path=weights, model_factory=lambda **_: FakeModel())
        fake_torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False))
        fake_rfdetr = types.SimpleNamespace(RFDETRSmall=object, RFDETRMedium=object)
        with patch.dict(sys.modules, {"torch": fake_torch, "rfdetr": fake_rfdetr}):
            detector.load()
        self.assertEqual(len(detector.metadata()["weights_sha256"]), 64)

    def test_17_license_is_registered(self):
        metadata = RFDETRDetector().metadata()
        self.assertEqual(metadata["code_license"], RFDETR_LICENSE)
        self.assertEqual(metadata["weights_license"], RFDETR_LICENSE)

    def test_18_comparison_aggregate(self):
        aggregate = aggregate_rows([{"processed_frames": 10, "elapsed_seconds": 2, "average_people_detected": 5, "frames_with_active_tracks_percent": 60}])
        self.assertEqual(aggregate["processing_fps"], 5.0)
        self.assertEqual(aggregate["average_people_detected"], 5.0)

    def test_19_comparison_files_are_written(self):
        rows = [{"variant": "rfdetr_small_standard", "processed_frames": 1, "elapsed_seconds": 1}]
        write_comparison(self.root, rows)
        self.assertTrue((self.root / "comparison" / "detector_comparison.json").is_file())
        self.assertTrue((self.root / "comparison" / "detector_comparison.csv").is_file())

    def test_20_contact_sheet_is_created(self):
        from research.vision_spike.benchmark import ClipSpec

        clip_path = self.root / "clip.mp4"
        make_video(clip_path)
        for variant in ("baseline_opencv", "rfdetr_small_standard", "rfdetr_small_highres", "rfdetr_small_tiled"):
            run = self.root / variant / "clip"
            run.mkdir(parents=True)
            (run / "frames.json").write_text(json.dumps([{"timestamp_seconds": 0.2, "detections": []}]), encoding="utf-8")
        destination = self.root / "sheet.jpg"
        create_contact_sheet(clip=ClipSpec("clip", clip_path, 1), timestamp_seconds=0.2, output_root=self.root, destination=destination)
        self.assertGreater(destination.stat().st_size, 0)

    def test_21_scene_metrics_are_separate(self):
        metrics = MetricsCollector()
        metrics.observe(FrameResult(1, 0.0, [self.detection()], [], 10.0, True, tactical_view_score=0.8), None)
        result = metrics.finalize(elapsed_seconds=1, tracker_metadata={}, team_metadata={}, device="cpu")
        self.assertEqual(result["scene_metrics"]["wide_tactical"]["frames"], 1)

    def test_22_manual_coverage_parser(self):
        path = self.root / "review.json"
        row = ManualObservation("rfdetr_small_standard", "clip", 7, "wide_tactical", 10, 7, 3, 0, 0, 0, True, "useful")
        path.write_text(json.dumps({"observations": [row.to_dict()]}), encoding="utf-8")
        self.assertEqual(load_observations(path)[0].manual_exploratory_coverage, 0.7)

    def test_23_no_product_imports_spike(self):
        files = [ROOT / "main.py", *(ROOT / "app" / "routers").glob("*.py")]
        self.assertFalse(any("research.vision_spike" in path.read_text(encoding="utf-8", errors="ignore") for path in files))

    def test_24_no_new_product_route(self):
        source = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "research" / "vision_spike").glob("*.py"))
        self.assertNotIn("APIRouter", source)

    def test_25_no_pwa_reference(self):
        source = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "research" / "vision_spike").glob("*.py"))
        self.assertNotIn("service-worker.js", source)
        self.assertNotIn("manifest.webmanifest", source)
        self.assertNotIn("frontend/", source)

    def test_26_no_video_in_spike_source(self):
        self.assertFalse(any(path.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv"} for path in (ROOT / "research" / "vision_spike").rglob("*")))

    def test_27_no_weights_in_spike_source(self):
        self.assertFalse(any(path.suffix.lower() in {".pt", ".pth", ".onnx", ".engine"} for path in (ROOT / "research" / "vision_spike").rglob("*")))

    def test_28_output_v2_is_ignored(self):
        completed = subprocess.run(["git", "check-ignore", "research/vision_spike/vision_output_v2/probe.txt"], cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0)

    def test_29_cli_help_is_available(self):
        self.assertIn("output_root", {action.dest for action in build_benchmark_parser()._actions})
        self.assertIn("clip_root", {action.dest for action in build_manual_parser()._actions})

    def test_30_decision_gate_and_error_are_readable(self):
        self.assertEqual(decision_gate(0.72, 75, licensing_ok=True), "GREEN")
        self.assertEqual(decision_gate(0.55, 50, licensing_ok=True), "YELLOW")
        self.assertEqual(decision_gate(0.35, 80, licensing_ok=True), "RED")
        summary = summarize_manual_review([], {"variants": {}})
        self.assertEqual(summary["rfdetr_small_standard"]["decision_gate"], "PENDING_MANUAL_REVIEW")

    def test_31_tile_origins_cover_last_pixel(self):
        origins = tile_origins(1920, 960, 0.2)
        self.assertEqual(origins[-1], 960)

    def test_32_generic_model_disables_ball_and_roles(self):
        metadata = RFDETRDetector().metadata()
        self.assertFalse(metadata["ball_supported"])
        self.assertEqual(metadata["football_specific_weights"], "unavailable")


if __name__ == "__main__":
    unittest.main()
