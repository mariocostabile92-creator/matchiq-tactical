from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from research.vision_spike.utils import require_cv2_numpy
from research.vision_spike.v3 import CATEGORY_IDS, CLASS_NAMES
from research.vision_spike.v3.annotation_schema import coco_categories, empty_coco_dataset, validate_category_schema
from research.vision_spike.v3.checkpoint_metadata import write_checkpoint_metadata
from research.vision_spike.v3.coco import bbox_iou_coco, validate_bbox, validate_coco_structure, write_coco
from research.vision_spike.v3.image_quality import blur_score, difference_hash, is_near_duplicate
from research.vision_spike.v3.licenses import DatasetSource, load_source_registry, write_source_registry
from research.vision_spike.v3.manifest import FrameRecord, read_jsonl, write_jsonl
from research.vision_spike.v3.metrics import average_precision, evaluate_detection_metrics, iou_xyxy
from research.vision_spike.v3.paths import DatasetPaths, assert_external_dataset_path
from research.vision_spike.v3.split_dataset import assign_matches, split_dataset
from research.vision_spike.v3.training_config import load_training_config
from research.vision_spike.v3.training_gate import evaluate_training_gate
from research.vision_spike.v3.validate_dataset import validate_dataset
from research.vision_spike.v3.visual_comparison import CLASS_STYLE, comparison_sheet, draw_detections


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "research" / "vision_spike" / "v3" / "configs" / "rfdetr_small_football.yaml"


def approved_source() -> DatasetSource:
    return DatasetSource(
        source_id="authorized-local", name="Synthetic authorized fixture", author="MatchIQ test",
        origin="local-fixture", license_name="Owner authorization", license_url="internal-reference",
        modification_allowed=True, commercial_use_allowed=True, commercial_weight_training_allowed=True,
        redistribution_allowed=False, attribution_required=False, authorization_reference="AUTH-TEST-001",
        media_types=("synthetic",), annotation_quality="test", classes=CLASS_NAMES, image_count=3,
        camera_types=("tactical_wide",), matchiq_relevance="validator fixture", status="approved",
    )


def create_video(path: Path) -> None:
    cv2, np = require_cv2_numpy()
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 5.0, (160, 96))
    if not writer.isOpened():
        raise RuntimeError("test video writer unavailable")
    for index in range(8):
        image = np.full((96, 160, 3), (30, 130, 35), dtype=np.uint8)
        cv2.rectangle(image, (20 + index * 3, 20), (40 + index * 3, 80), (240, 240, 240), -1)
        writer.write(image)
    writer.release()


def build_dataset(root: Path, *, matches: int = 3) -> DatasetPaths:
    cv2, np = require_cv2_numpy()
    paths = DatasetPaths.from_root(root)
    paths.initialize()
    write_source_registry(paths.source_registry, [approved_source()])
    coco = empty_coco_dataset()
    frames = []
    annotation_id = 1
    for index in range(1, matches + 1):
        name = f"frame-{index}.jpg"
        image = np.full((120, 200, 3), (25 + index, 120, 35), dtype=np.uint8)
        cv2.rectangle(image, (20, 20), (60, 105), (220, 220, 220), -1)
        cv2.imwrite(str(paths.extracted / name), image)
        digest = f"{index:064x}"
        match_id = f"match-{index}"
        metadata = {
            "source_id": "authorized-local", "video_id": match_id, "match_id": match_id,
            "frame_sha256": digest, "camera_type": "tactical_wide", "lighting": "day",
            "quality": "high", "split": "unassigned", "staff_public_visible": index == 1,
        }
        coco["images"].append({"id": index, "file_name": name, "width": 200, "height": 120, "metadata": metadata})
        for category_id, box in ((1, [20, 20, 40, 85]), (2, [80, 20, 30, 80]), (3, [125, 20, 25, 75]), (4, [165, 70, 8, 8])):
            coco["annotations"].append({
                "id": annotation_id, "image_id": index, "category_id": category_id,
                "bbox": box, "area": box[2] * box[3], "iscrowd": 0,
            })
            annotation_id += 1
        frames.append({
            "frame_id": f"frame-{index}", "file_name": name, "video_id": match_id, "match_id": match_id,
            "source_id": "authorized-local", "source_file_name": "fixture.mp4", "source_sha256": "a" * 64,
            "frame_sha256": digest, "timestamp_seconds": float(index), "frame_index": index,
            "width": 200, "height": 120, "source_fps": 25.0, "camera_type": "tactical_wide",
            "quality": "high", "lighting": "day", "authorization_origin": "AUTH-TEST-001",
            "split": "unassigned", "blur_score": 100.0, "mean_luma": 100.0, "green_ratio": 0.6,
            "tactical_view_score": 0.8, "is_negative": False,
        })
    write_coco(paths.canonical_annotations, coco)
    write_jsonl(paths.frame_manifest, frames)
    return paths


class VisionSpikeV3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_01_dataset_paths(self):
        paths = DatasetPaths.from_root(self.root / "data")
        paths.initialize()
        self.assertTrue(paths.annotations.is_dir())

    def test_02_external_path_guard(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            assert_external_dataset_path(ROOT / "research" / "vision_spike" / "data", ROOT)

    def test_03_frame_record_round_trip(self):
        payload = build_dataset(self.root).frame_manifest
        self.assertEqual(len(read_jsonl(payload)), 3)

    def test_04_manifest_invalid_json(self):
        path = self.root / "broken.jsonl"
        path.write_text("{broken}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "invalid JSONL"):
            read_jsonl(path)

    def test_05_duplicate_hash_filter(self):
        self.assertTrue(is_near_duplicate(0b1010, [0b1011], max_distance=1))

    def test_06_blur_filter_signal(self):
        _, np = require_cv2_numpy()
        self.assertEqual(blur_score(np.zeros((50, 50, 3), dtype=np.uint8)), 0.0)

    def test_07_difference_hash_deterministic(self):
        _, np = require_cv2_numpy()
        frame = np.zeros((50, 50, 3), dtype=np.uint8)
        self.assertEqual(difference_hash(frame), difference_hash(frame))

    def test_08_class_schema(self):
        self.assertEqual(tuple(item["name"] for item in coco_categories()), CLASS_NAMES)

    def test_09_class_ids_fixed(self):
        self.assertEqual(CATEGORY_IDS, {"player": 1, "goalkeeper": 2, "referee": 3, "ball": 4})

    def test_10_invalid_category_schema(self):
        self.assertTrue(validate_category_schema([{"id": 1, "name": "player"}]))

    def test_11_bbox_bounds(self):
        self.assertIn("bbox exceeds image bounds", validate_bbox([90, 90, 20, 20], 100, 100))

    def test_12_bbox_iou(self):
        self.assertEqual(bbox_iou_coco([0, 0, 10, 10], [0, 0, 10, 10]), 1.0)

    def test_13_orphan_annotation(self):
        coco = empty_coco_dataset()
        coco["annotations"].append({"id": 1, "image_id": 99, "category_id": 1, "bbox": [0, 0, 1, 1]})
        self.assertTrue(any("orphan" in item for item in validate_coco_structure(coco)))

    def test_14_validator_valid_fixture(self):
        report = validate_dataset(build_dataset(self.root).root)
        self.assertEqual(report["status"], "VALID")

    def test_15_validator_class_distribution(self):
        report = validate_dataset(build_dataset(self.root).root)
        self.assertEqual(report["class_distribution"]["ball"], 3)

    def test_16_validator_contact_sheet(self):
        paths = build_dataset(self.root)
        validate_dataset(paths.root)
        self.assertTrue((paths.reports / "contact_sheet.jpg").is_file())

    def test_17_license_metadata(self):
        paths = build_dataset(self.root)
        self.assertTrue(load_source_registry(paths.source_registry)[0].approved_for_v3)

    def test_18_unapproved_license(self):
        source = approved_source().to_dict()
        source["commercial_weight_training_allowed"] = False
        self.assertFalse(DatasetSource.from_dict(source).approved_for_v3)

    def test_19_split_by_match(self):
        result = assign_matches({"a": 10, "b": 10, "c": 10}, seed=1)
        self.assertEqual(set(result.values()), {"train", "val", "test"})

    def test_20_split_deterministic(self):
        sizes = {"a": 7, "b": 6, "c": 5, "d": 4}
        self.assertEqual(assign_matches(sizes, seed=42), assign_matches(sizes, seed=42))

    def test_21_split_no_leakage(self):
        paths = build_dataset(self.root)
        manifest = split_dataset(paths.root, materialize=False)
        self.assertEqual(len(manifest["assignments"]), 3)
        self.assertEqual(len(manifest["frozen_test"]["sha256"]), 64)

    def test_22_rfdetr_export(self):
        paths = build_dataset(self.root)
        split_dataset(paths.root)
        self.assertTrue((paths.cache / "rfdetr_dataset" / "train" / "_annotations.coco.json").is_file())

    def test_23_training_config(self):
        config = load_training_config(CONFIG)
        self.assertEqual(config.class_names, CLASS_NAMES)

    def test_24_training_config_forbids_vertical_flip(self):
        values = json.loads(CONFIG.read_text(encoding="utf-8"))
        values["augmentations"]["VerticalFlip"] = {"p": 0.5}
        path = self.root / "bad.yaml"
        path.write_text(json.dumps(values), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "forbidden"):
            load_training_config(path)

    def test_25_insufficient_dataset_gate(self):
        paths = build_dataset(self.root)
        split_dataset(paths.root, materialize=False)
        report = evaluate_training_gate(load_training_config(CONFIG), paths.root)
        self.assertEqual(report["status"], "DATASET_NOT_READY")

    def test_26_checkpoint_metadata(self):
        checkpoint = self.root / "best.pth"
        checkpoint.write_bytes(b"synthetic")
        payload = write_checkpoint_metadata(self.root / "best.json", checkpoint=checkpoint, values={"seed": 42})
        self.assertEqual(len(payload["checkpoint_sha256"]), 64)

    def test_27_iou_xyxy(self):
        self.assertEqual(iou_xyxy([0, 0, 10, 10], [0, 0, 10, 10]), 1.0)

    def test_28_average_precision(self):
        self.assertAlmostEqual(average_precision([(0.9, 1)], 1), 1.0)

    def test_29_per_class_metrics(self):
        truth = [{"image_id": 1, "class_name": "player", "bbox": [0, 0, 10, 10], "area": 100}]
        predictions = [{"image_id": 1, "class_name": "player", "bbox": [0, 0, 10, 10], "score": 0.9, "area": 100}]
        self.assertEqual(evaluate_detection_metrics(truth, predictions)["per_class"]["player"]["recall"], 1.0)

    def test_30_ball_metrics_separate(self):
        truth = [{"image_id": 1, "class_name": "ball", "bbox": [0, 0, 4, 4], "area": 16}]
        self.assertEqual(evaluate_detection_metrics(truth, [])["ball"]["false_negative"], 1)

    def test_31_confusion_matrix(self):
        result = evaluate_detection_metrics([], [{"image_id": 1, "class_name": "referee", "bbox": [0, 0, 4, 4], "score": 0.8}])
        self.assertEqual(result["confusion_matrix"]["background"]["referee"], 1)

    def test_32_overlay_class_mapping(self):
        self.assertIn("BALL", [value[1] for value in CLASS_STYLE.values()])

    def test_33_overlay_draws_without_error(self):
        _, np = require_cv2_numpy()
        frame = np.zeros((100, 160, 3), dtype=np.uint8)
        output = draw_detections(frame, [{"class_name": "ball", "bbox_xyxy": [10, 10, 20, 20], "score": 0.8}])
        self.assertEqual(output.shape, frame.shape)

    def test_34_visual_comparison_sheet(self):
        _, np = require_cv2_numpy()
        frame = np.zeros((100, 160, 3), dtype=np.uint8)
        output = self.root / "sheet.jpg"
        comparison_sheet(frame, frame, frame, output)
        self.assertTrue(output.is_file())

    def test_35_no_product_imports_or_routes(self):
        texts = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "research" / "vision_spike" / "v3").rglob("*.py"))
        self.assertNotIn("from main import", texts)
        self.assertNotIn("APIRouter", texts)
        self.assertNotIn("frontend/", texts)

    def test_36_cli_help(self):
        modules = (
            "extract_frames", "validate_dataset", "split_dataset", "training_gate", "train_rfdetr",
            "evaluate_dataset", "benchmark_v3", "visual_comparison",
        )
        for module in modules:
            result = subprocess.run(
                [sys.executable, "-m", f"research.vision_spike.v3.{module}", "--help"],
                cwd=ROOT, capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(result.returncode, 0, msg=f"{module}: {result.stderr}")


if __name__ == "__main__":
    unittest.main()
