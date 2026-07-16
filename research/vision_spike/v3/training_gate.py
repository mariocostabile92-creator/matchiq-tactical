from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .licenses import load_source_registry
from .paths import DatasetPaths
from .training_config import TrainingConfig, load_training_config
from .validate_dataset import validate_dataset


@dataclass(frozen=True, slots=True)
class GateCheck:
    name: str
    passed: bool
    detail: str


def _hardware_status(device: str) -> tuple[bool, str, dict[str, Any]]:
    details: dict[str, Any] = {"requested_device": device}
    if device == "cpu":
        details["accelerator"] = "cpu"
        return True, "CPU explicitly selected; training will be slow", details
    try:
        import torch
        available = bool(torch.cuda.is_available())
        details.update(
            torch_version=str(torch.__version__),
            cuda_available=available,
            cuda_version=str(torch.version.cuda),
        )
        if available:
            details["device_name"] = str(torch.cuda.get_device_name(0))
            details["vram_gb"] = round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2)
            return True, f"CUDA available: {details['device_name']}", details
        return False, "CUDA requested but unavailable", details
    except ImportError:
        return False, "PyTorch is not installed in this environment", details


def evaluate_training_gate(config: TrainingConfig, dataset_root: Path) -> dict[str, Any]:
    paths = DatasetPaths.from_root(dataset_root)
    checks: list[GateCheck] = []
    checks.append(GateCheck("dataset_available", paths.canonical_annotations.is_file(), str(paths.root.name)))
    if paths.canonical_annotations.is_file():
        validation = validate_dataset(paths.root, seed=config.seed)
    else:
        validation = {"status": "INVALID", "images": 0, "matches": 0, "class_distribution": {}, "critical_errors": 1}
    minimums = config.values["minimums"]
    checks.append(GateCheck("validator", validation.get("status") == "VALID", f"critical={validation.get('critical_errors', 0)}"))
    checks.append(GateCheck("minimum_images", int(validation.get("images", 0)) >= int(minimums["images"]), f"{validation.get('images', 0)}/{minimums['images']}"))
    checks.append(GateCheck("minimum_matches", int(validation.get("matches", 0)) >= int(minimums["matches"]), f"{validation.get('matches', 0)}/{minimums['matches']}"))
    class_distribution = validation.get("class_distribution", {})
    for name, required in minimums["class_examples"].items():
        actual = int(class_distribution.get(name, 0))
        checks.append(GateCheck(f"class_{name}", actual >= int(required), f"{actual}/{required}"))
    sources = load_source_registry(paths.source_registry)
    approved = [source for source in sources if source.approved_for_v3]
    checks.append(GateCheck("licenses", bool(sources) and len(approved) == len(sources), f"approved={len(approved)}/{len(sources)}"))
    split_manifest: dict[str, Any] = {}
    if paths.split_manifest.is_file():
        split_manifest = json.loads(paths.split_manifest.read_text(encoding="utf-8"))
    frozen = split_manifest.get("frozen_test", {})
    checks.append(GateCheck("match_level_split", bool(split_manifest.get("assignments")), "split manifest present" if split_manifest else "missing"))
    checks.append(GateCheck("frozen_test", bool(frozen.get("sha256") and frozen.get("image_ids")), str(frozen.get("sha256", "missing"))[:16]))
    free_gb = shutil.disk_usage(paths.root if paths.root.exists() else paths.root.parent).free / 1024**3
    checks.append(GateCheck("disk_space", free_gb >= float(minimums["free_disk_gb"]), f"{free_gb:.2f} GB free"))
    hardware_ok, hardware_detail, hardware = _hardware_status(str(config.values["device"]))
    checks.append(GateCheck("hardware", hardware_ok, hardware_detail))
    ready = all(item.passed for item in checks)
    report = {
        "status": "READY" if ready else "DATASET_NOT_READY",
        "ready": ready,
        "checks": [asdict(item) for item in checks],
        "validation": validation,
        "hardware": hardware,
        "config": config.source_path.name,
    }
    paths.reports.mkdir(parents=True, exist_ok=True)
    (paths.reports / "training_gate.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate the V3 dataset, license, split and hardware training gate.")
    parser.add_argument("--config", type=Path, default=Path(__file__).parent / "configs" / "rfdetr_small_football.yaml")
    parser.add_argument("--dataset", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_training_config(args.config)
    dataset = config.resolved_dataset_path(args.dataset)
    report = evaluate_training_gate(config, dataset)
    print(json.dumps(report, indent=2))
    return 0 if report["ready"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
