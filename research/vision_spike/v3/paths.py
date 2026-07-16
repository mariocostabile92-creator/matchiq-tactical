from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DatasetPaths:
    root: Path

    @classmethod
    def from_root(cls, root: str | Path) -> "DatasetPaths":
        return cls(Path(root).expanduser().resolve())

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def extracted(self) -> Path:
        return self.root / "extracted"

    @property
    def annotations(self) -> Path:
        return self.root / "annotations"

    @property
    def images(self) -> Path:
        return self.root / "images"

    @property
    def labels(self) -> Path:
        return self.root / "labels"

    @property
    def manifests(self) -> Path:
        return self.root / "manifests"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    @property
    def checkpoints(self) -> Path:
        return self.root / "checkpoints"

    @property
    def training_output(self) -> Path:
        return self.root / "training_output"

    @property
    def source_registry(self) -> Path:
        return self.manifests / "sources.json"

    @property
    def frame_manifest(self) -> Path:
        return self.manifests / "frames.jsonl"

    @property
    def split_manifest(self) -> Path:
        return self.manifests / "split_manifest.json"

    @property
    def canonical_annotations(self) -> Path:
        return self.annotations / "dataset.coco.json"

    def image_split(self, split: str) -> Path:
        return self.images / split

    def label_split(self, split: str) -> Path:
        return self.labels / split

    def initialize(self) -> None:
        directories = [
            self.raw,
            self.extracted,
            self.annotations,
            self.manifests,
            self.reports,
            self.cache,
            self.checkpoints,
            self.training_output,
            self.root / "tensorboard",
            self.root / "wandb",
            self.root / "logs",
        ]
        for split in ("train", "val", "test"):
            directories.extend((self.image_split(split), self.label_split(split)))
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


def assert_external_dataset_path(root: Path, repository_root: Path) -> None:
    dataset = root.resolve()
    repository = repository_root.resolve()
    try:
        dataset.relative_to(repository)
    except ValueError:
        return
    raise ValueError(
        "The V3 dataset must live outside the repository. Choose an external local directory."
    )
