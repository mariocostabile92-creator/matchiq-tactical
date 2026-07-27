import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research.player_detection.adapters import ExistingVisionDetectorAdapter
from research.player_detection.cli import build_parser
from research.player_detection.compare import PlayerDetectionComparator
from research.player_detection.contracts import PlayerDetector, RawPlayerDetection
from research.player_detection.geometry import describe_bbox
from research.player_detection.runner import (
    PlayerDetectionConfig,
    PlayerDetectionRunner,
)
from research.vision_spike.contracts import Detection
from research.vision_spike.detector import VisionDetector
from research.vision_spike.utils import OptionalDependencyError


class FakePlayerDetector(PlayerDetector):
    def __init__(self):
        self.load_calls = 0
        self.detect_calls = 0
        self.closed = False

    def load(self):
        self.load_calls += 1

    def detect(self, image):
        self.detect_calls += 1
        return [
            RawPlayerDetection(
                class_id=0,
                class_name="person",
                confidence=0.91,
                bbox_xyxy=(-10.0, 5.0, 80.0, 95.0),
            ),
            RawPlayerDetection(
                class_id=0,
                class_name="person",
                confidence=0.63,
                bbox_xyxy=(110.0, 20.0, 150.0, 100.0),
            ),
        ]

    def metadata(self):
        return {
            "backend": "fake",
            "model": "deterministic test detector",
            "device": "cpu",
        }

    def close(self):
        self.closed = True


class FakeVisionDetector(VisionDetector):
    def __init__(self):
        self.load_calls = 0
        self.detect_calls = 0

    def load(self):
        self.load_calls += 1

    def detect(self, frame, *, frame_index, timestamp_seconds):
        self.detect_calls += 1
        return [
            Detection(
                frame_index,
                timestamp_seconds,
                7,
                "car",
                0.99,
                (0.0, 0.0, 20.0, 20.0),
                "mock-rfdetr",
                "car-1",
                {"original_class": "car"},
            ),
            Detection(
                frame_index,
                timestamp_seconds,
                1,
                "person",
                0.72,
                (-5.0, 10.0, 125.0, 110.0),
                "mock-rfdetr",
                "person-low",
                {"original_class": "person"},
            ),
            Detection(
                frame_index,
                timestamp_seconds,
                1,
                "person",
                0.94,
                (30.0, 5.0, 60.0, 90.0),
                "mock-rfdetr",
                "person-high",
                {"original_class": "person"},
            ),
        ]

    def metadata(self):
        return {
            "backend": "rfdetr",
            "model": "RF-DETR Small COCO mock",
            "rfdetr_version": "test",
            "device": "cpu",
            "last_inference": {
                "raw_detection_count": 3,
                "person_detection_count": 2,
                "kept_detection_count": 2,
            },
        }

    def close(self):
        pass


class BackendFakePlayerDetector(PlayerDetector):
    def __init__(self, backend: str):
        self.backend = backend
        self.load_calls = 0

    def load(self):
        self.load_calls += 1

    def detect(self, image):
        count = 1 if self.backend == "opencv_hog" else 2
        return [
            RawPlayerDetection(
                class_id=0,
                class_name="person",
                confidence=0.60 + index * 0.1,
                bbox_xyxy=(10.0 + index * 20, 10.0, 35.0 + index * 20, 90.0),
                source_model=self.backend,
                metadata={"original_class": "person"},
            )
            for index in range(count)
        ]

    def metadata(self):
        return {
            "backend": self.backend,
            "model": f"{self.backend}-test",
            "device": "cpu",
            "last_inference": {
                "raw_detection_count": 1 if self.backend == "opencv_hog" else 2,
                "kept_detection_count": 1 if self.backend == "opencv_hog" else 2,
            },
        }

    def close(self):
        pass


class PlayerDetectionGeometryTests(unittest.TestCase):
    def test_bbox_conversions_center_footpoint_and_normalized_coordinates(self):
        geometry = describe_bbox((10.0, 20.0, 50.0, 80.0), width=100, height=100)

        self.assertEqual(geometry["bbox_xyxy"], [10.0, 20.0, 50.0, 80.0])
        self.assertEqual(geometry["bbox_xywh"], [10.0, 20.0, 40.0, 60.0])
        self.assertEqual(geometry["center_xy"], [30.0, 50.0])
        self.assertEqual(geometry["foot_point_xy"], [30.0, 80.0])
        self.assertEqual(geometry["normalized_bbox_xyxy"], [0.1, 0.2, 0.5, 0.8])
        self.assertEqual(geometry["normalized_center_xy"], [0.3, 0.5])
        self.assertEqual(geometry["normalized_foot_point_xy"], [0.3, 0.8])

    def test_bbox_is_clamped_to_image_boundaries(self):
        geometry = describe_bbox((-20.0, -5.0, 140.0, 120.0), width=120, height=90)

        self.assertEqual(geometry["bbox_xyxy"], [0.0, 0.0, 120.0, 90.0])
        self.assertEqual(geometry["normalized_bbox_xyxy"], [0.0, 0.0, 1.0, 1.0])
        self.assertEqual(geometry["normalized_foot_point_xy"], [0.5, 1.0])


class PlayerDetectionRunnerTests(unittest.TestCase):
    @staticmethod
    def _write_image(path: Path, color: tuple[int, int, int]) -> bytes:
        import cv2
        import numpy as np

        image = np.zeros((100, 120, 3), dtype=np.uint8)
        image[:, :] = color
        cv2.rectangle(image, (20, 10), (70, 90), (240, 240, 240), 2)
        if not cv2.imwrite(str(path), image):
            raise AssertionError("test image could not be written")
        return path.read_bytes()

    def test_directory_run_loads_model_once_writes_json_manifest_and_debug_images(self):
        detector = FakePlayerDetector()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = root / "inputs"
            output = root / "output"
            inputs.mkdir()
            first = inputs / "frame-one.jpg"
            second = inputs / "frame-two.jpg"
            first_original = self._write_image(first, (30, 120, 40))
            second_original = self._write_image(second, (35, 125, 45))

            result = PlayerDetectionRunner(detector=detector).run(
                [first, second],
                PlayerDetectionConfig(output_dir=output),
                source_mode="image_directory",
            )

            self.assertEqual(detector.load_calls, 1)
            self.assertEqual(detector.detect_calls, 2)
            self.assertTrue(detector.closed)
            self.assertEqual(first.read_bytes(), first_original)
            self.assertEqual(second.read_bytes(), second_original)
            self.assertTrue(result.manifest_path.is_file())
            self.assertTrue(result.html_path.is_file())
            self.assertEqual(result.manifest["aggregate"]["images_processed"], 2)
            self.assertEqual(result.manifest["aggregate"]["images_successful"], 2)
            self.assertEqual(result.manifest["aggregate"]["images_failed"], 0)
            self.assertEqual(result.manifest["aggregate"]["detections_total"], 4)
            self.assertEqual(result.manifest["aggregate"]["detections_min"], 2)
            self.assertEqual(result.manifest["aggregate"]["detections_max"], 2)
            self.assertEqual(result.manifest["aggregate"]["confidence_distribution"]["0.75-1.00"], 2)
            self.assertEqual(result.manifest["aggregate"]["confidence_distribution"]["0.50-0.74"], 2)
            self.assertTrue(all((output / item["debug_image"]).is_file() for item in result.manifest["files"]))
            self.assertTrue(all((output / item["json_report"]).is_file() for item in result.manifest["files"]))

    def test_image_json_contains_required_detection_contract(self):
        detector = FakePlayerDetector()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "frame.jpg"
            output = root / "output"
            self._write_image(source, (25, 110, 35))

            result = PlayerDetectionRunner(detector=detector).run(
                [source],
                PlayerDetectionConfig(output_dir=output),
                source_mode="single_image",
            )
            image_report_path = output / result.manifest["files"][0]["json_report"]
            payload = json.loads(image_report_path.read_text(encoding="utf-8"))
            detection = payload["detections"][0]

            self.assertEqual(payload["schema_version"], "matchiq.ve-002.player-detection.v1")
            self.assertEqual(payload["detection_count"], 2)
            self.assertEqual(detection["detection_id"], "player_001")
            self.assertEqual(detection["class_id"], 0)
            self.assertEqual(detection["class_name"], "person")
            self.assertEqual(detection["confidence"], 0.91)
            self.assertEqual(detection["bbox_xyxy"], [0.0, 5.0, 80.0, 95.0])
            self.assertEqual(detection["bbox_xywh"], [0.0, 5.0, 80.0, 90.0])
            self.assertEqual(detection["center_xy"], [40.0, 50.0])
            self.assertEqual(detection["foot_point_xy"], [40.0, 95.0])
            self.assertEqual(detection["normalized_center_xy"], [0.333333, 0.5])
            self.assertEqual(detection["normalized_foot_point_xy"], [0.333333, 0.95])
            self.assertIn("model_load_ms", result.manifest["timing_ms"])
            self.assertIn("average_inference_ms", result.manifest["timing_ms"])

    def test_corrupt_image_is_recorded_and_directory_processing_continues(self):
        detector = FakePlayerDetector()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid = root / "valid.jpg"
            corrupt = root / "corrupt.jpg"
            output = root / "output"
            self._write_image(valid, (30, 120, 40))
            corrupt.write_bytes(b"not-an-image")

            result = PlayerDetectionRunner(detector=detector).run(
                [corrupt, valid],
                PlayerDetectionConfig(output_dir=output),
                source_mode="image_directory",
            )

            self.assertEqual(result.manifest["aggregate"]["images_processed"], 2)
            self.assertEqual(result.manifest["aggregate"]["images_successful"], 1)
            self.assertEqual(result.manifest["aggregate"]["images_failed"], 1)
            self.assertEqual(detector.detect_calls, 1)
            self.assertEqual(result.manifest["errors"][0]["source_name"], "corrupt.jpg")
            self.assertIn("unreadable or corrupt", result.manifest["errors"][0]["message"])
            failed_file = next(item for item in result.manifest["files"] if item["status"] == "failed")
            failed_payload = json.loads(
                (output / failed_file["json_report"]).read_text(encoding="utf-8")
            )
            self.assertEqual(failed_payload["status"], "failed")
            self.assertEqual(failed_payload["detections"], [])
            self.assertIn("unreadable or corrupt", failed_payload["error"])

    def test_debug_render_never_overwrites_source_even_when_output_is_near_input(self):
        detector = FakePlayerDetector()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "frame.jpg"
            original = self._write_image(source, (20, 100, 30))

            result = PlayerDetectionRunner(detector=detector).run(
                [source],
                PlayerDetectionConfig(output_dir=root / "ve002"),
                source_mode="single_image",
            )

            self.assertEqual(source.read_bytes(), original)
            debug_path = root / "ve002" / result.manifest["files"][0]["debug_image"]
            self.assertNotEqual(debug_path.resolve(), source.resolve())
            self.assertTrue(debug_path.is_file())

    def test_rfdetr_adapter_refuses_to_download_missing_weights(self):
        adapter = ExistingVisionDetectorAdapter(backend="rfdetr")

        with self.assertRaisesRegex(RuntimeError, "never downloads"):
            adapter.load()

    def test_rfdetr_adapter_loads_once_filters_person_and_preserves_metadata(self):
        detector = FakeVisionDetector()
        with tempfile.TemporaryDirectory() as temporary:
            weights = Path(temporary) / "weights.pth"
            weights.write_bytes(b"mock")
            adapter = ExistingVisionDetectorAdapter(
                backend="rfdetr",
                model_path=weights,
                confidence_threshold=0.30,
                device="cpu",
            )
            with patch(
                "research.player_detection.adapters.existing_vision.build_detector",
                return_value=detector,
            ) as factory:
                adapter.load()
                adapter.load()
                detections = adapter.detect(object())

        self.assertEqual(factory.call_count, 1)
        self.assertEqual(detector.load_calls, 1)
        self.assertEqual(detector.detect_calls, 1)
        self.assertEqual([item.class_name for item in detections], ["person", "person"])
        self.assertEqual([item.confidence for item in detections], [0.94, 0.72])
        self.assertEqual(detections[0].source_model, "mock-rfdetr")
        self.assertEqual(detections[0].metadata["original_class"], "person")
        metadata = adapter.metadata()
        self.assertEqual(metadata["backend"], "rfdetr")
        self.assertEqual(metadata["confidence_threshold"], 0.30)
        self.assertFalse(metadata["automatic_downloads"])

    def test_rfdetr_adapter_surfaces_missing_optional_dependency_without_download(self):
        class MissingDependencyDetector(FakeVisionDetector):
            def load(self):
                raise OptionalDependencyError("RF-DETR dependency missing")

        with tempfile.TemporaryDirectory() as temporary:
            weights = Path(temporary) / "weights.pth"
            weights.write_bytes(b"mock")
            adapter = ExistingVisionDetectorAdapter(
                backend="rfdetr",
                model_path=weights,
            )
            with patch(
                "research.player_detection.adapters.existing_vision.build_detector",
                return_value=MissingDependencyDetector(),
            ):
                with self.assertRaisesRegex(OptionalDependencyError, "dependency missing"):
                    adapter.load()

    def test_rfdetr_runner_serializes_clipped_boxes_model_and_postprocessing(self):
        detector = ExistingVisionDetectorAdapter(
            backend="rfdetr",
            model_path=Path(__file__),
            confidence_threshold=0.30,
            device="cpu",
        )
        vision_detector = FakeVisionDetector()
        detector._detector = vision_detector
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "frame.jpg"
            output = root / "output"
            self._write_image(source, (25, 110, 35))
            result = PlayerDetectionRunner(detector=detector).run(
                [source],
                PlayerDetectionConfig(
                    output_dir=output,
                    backend="rfdetr",
                    confidence_threshold=0.30,
                    model_path=Path(__file__),
                    device="cpu",
                ),
                source_mode="single_image",
            )
            payload = json.loads(
                (output / result.manifest["files"][0]["json_report"]).read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(payload["detector"]["backend"], "rfdetr")
        self.assertEqual(payload["postprocessing"]["raw_detection_count"], 3)
        self.assertEqual(payload["postprocessing"]["kept_detection_count"], 2)
        self.assertEqual(payload["detections"][0]["bbox_xyxy"], [30.0, 5.0, 60.0, 90.0])
        self.assertEqual(payload["detections"][1]["bbox_xyxy"], [0.0, 10.0, 120.0, 100.0])
        self.assertEqual(payload["detections"][0]["candidate_type"], "player_candidate")
        self.assertEqual(payload["detections"][0]["original_class"], "person")
        json.dumps(payload)

    def test_cli_selects_rfdetr_threshold_and_hog_alias(self):
        parser = build_parser()
        rfdetr = parser.parse_args([
            "--image",
            "frame.jpg",
            "--output",
            "out",
            "--backend",
            "rfdetr",
            "--threshold",
            "0.30",
        ])
        hog = parser.parse_args([
            "--image",
            "frame.jpg",
            "--output",
            "out",
            "--backend",
            "hog",
        ])

        self.assertEqual(rfdetr.backend, "rfdetr")
        self.assertEqual(rfdetr.confidence, 0.30)
        self.assertEqual(hog.backend, "hog")

    def test_comparison_uses_identical_frames_and_writes_descriptive_outputs(self):
        created_detectors: list[BackendFakePlayerDetector] = []

        def detector_factory(**settings):
            detector = BackendFakePlayerDetector(settings["backend"])
            created_detectors.append(detector)
            return detector

        def runner_factory():
            return PlayerDetectionRunner(detector_factory=detector_factory)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "frame.jpg"
            output = root / "comparison"
            weights = root / "weights.pth"
            weights.write_bytes(b"mock")
            self._write_image(source, (25, 110, 35))
            result = PlayerDetectionComparator(
                runner_factory=runner_factory
            ).run(
                [source],
                output_dir=output,
                model_path=weights,
                threshold=0.30,
                device="cpu",
            )

            self.assertTrue(result.manifest_path.is_file())
            self.assertTrue(result.html_path.is_file())
            self.assertTrue((output / "hog" / "player_detection_manifest.json").is_file())
            self.assertTrue(
                (output / "rfdetr" / "player_detection_manifest.json").is_file()
            )
            frame = result.manifest["frames"][0]
            self.assertEqual(frame["source_path"], str(source.resolve()))
            self.assertEqual(frame["hog"]["detection_count"], 1)
            self.assertEqual(frame["rfdetr"]["detection_count"], 2)
            self.assertEqual(frame["count_delta"], 1)
            self.assertEqual(result.manifest["accuracy_metrics"], None)
            self.assertIn("senza ground truth", result.manifest["interpretation_notice"])

        self.assertEqual([item.load_calls for item in created_detectors], [1, 1])


if __name__ == "__main__":
    unittest.main()
