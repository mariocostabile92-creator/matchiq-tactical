from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

from .checkpoint_metadata import write_checkpoint_metadata
from .paths import DatasetPaths
from .training_config import load_training_config
from .training_gate import evaluate_training_gate


def train(config_path: Path, dataset_root: Path, *, confirm_training: bool) -> dict[str, object]:
    config = load_training_config(config_path)
    gate = evaluate_training_gate(config, dataset_root)
    if not gate["ready"]:
        return {"status": "DATASET_NOT_READY", "training_executed": False, "gate": gate}
    if not confirm_training:
        return {"status": "CONFIRMATION_REQUIRED", "training_executed": False, "gate": gate}
    try:
        import torch
        from rfdetr import RFDETRSmall
    except ImportError as exc:
        raise RuntimeError("RF-DETR training dependencies are not installed") from exc
    paths = DatasetPaths.from_root(dataset_root)
    output_dir = paths.training_output / datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
    output_dir.mkdir(parents=True, exist_ok=False)
    values = config.values
    model = RFDETRSmall()
    started = time.perf_counter()
    model.train(
        dataset_dir=str(paths.cache / "rfdetr_dataset"),
        output_dir=str(output_dir),
        epochs=int(values["epochs"]),
        batch_size=int(values["batch_size"]),
        grad_accum_steps=int(values["gradient_accumulation"]),
        lr=float(values["learning_rate"]),
        lr_encoder=float(values.get("encoder_learning_rate", values["learning_rate"] / 10)),
        weight_decay=float(values["weight_decay"]),
        warmup_epochs=int(values["warmup_epochs"]),
        early_stopping=bool(values["early_stopping"]),
        early_stopping_patience=int(values.get("early_stopping_patience", 8)),
        eval_interval=int(values["evaluation_interval"]),
        num_workers=int(values["workers"]),
        seed=int(values["seed"]),
        class_names=list(values["class_names"]),
        dataset_file="roboflow",
        aug_config=dict(values["augmentations"]),
        tensorboard=True,
        wandb=False,
        run_test=False,
        accelerator="gpu" if values["device"] == "cuda" else "cpu",
        devices=1,
        amp_dtype="fp16" if bool(values["mixed_precision"]) and values["device"] == "cuda" else "auto",
        notes={"purpose": "MatchIQ Vision Engine V3 isolated football fine-tuning"},
    )
    duration = time.perf_counter() - started
    candidates = sorted(output_dir.glob("**/*.pth"), key=lambda item: item.stat().st_mtime, reverse=True)
    manifest = {
        "status": "TRAINED",
        "training_executed": True,
        "duration_seconds": round(duration, 3),
        "seed": int(values["seed"]),
        "python": platform.python_version(),
        "torch": str(torch.__version__),
        "cuda": str(torch.version.cuda),
        "device": str(torch.cuda.get_device_name(0)) if torch.cuda.is_available() else "cpu",
        "config": values,
        "test_evaluated": False,
    }
    (output_dir / "training_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if candidates:
        write_checkpoint_metadata(output_dir / "best_checkpoint.json", checkpoint=candidates[0], values=manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fine-tune RF-DETR Small on an approved MatchIQ V3 football dataset.")
    parser.add_argument("--config", type=Path, default=Path(__file__).parent / "configs" / "rfdetr_small_football.yaml")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--confirm-training", action="store_true", help="Required in addition to a READY training gate.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = train(args.config, args.dataset, confirm_training=args.confirm_training)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "TRAINED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
