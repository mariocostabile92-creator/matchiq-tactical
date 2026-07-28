from __future__ import annotations

from typing import Iterable

from .contracts import (
    TEAM_A,
    TEAM_B,
    UNKNOWN,
    ClusterAssignment,
    ColorSample,
)


def _initialize_centers(matrix: object, quality: object) -> tuple[object, object]:
    import numpy as np

    count = len(matrix)
    distances = np.linalg.norm(matrix[:, None, :] - matrix[None, :, :], axis=2)
    support_radius = 0.30
    support = np.sum(distances <= support_radius, axis=1)
    minimum_support = max(2, int(round(count * 0.08)))

    best: tuple[float, int, int] | None = None
    for first in range(count):
        for second in range(first + 1, count):
            if support[first] < minimum_support or support[second] < minimum_support:
                continue
            distance = float(distances[first, second])
            score = distance * min(float(support[first]), float(support[second]))
            score *= float((quality[first] * quality[second]) ** 0.5)
            candidate = (score, -first, -second)
            if best is None or candidate > best:
                best = candidate

    if best is None:
        first, second = np.unravel_index(np.argmax(distances), distances.shape)
    else:
        first, second = -best[1], -best[2]
    return matrix[int(first)].copy(), matrix[int(second)].copy()


def cluster_team_samples(
    samples: Iterable[ColorSample],
    *,
    minimum_confidence: float,
    minimum_separation: float,
) -> tuple[dict[str, ClusterAssignment], dict[str, object]]:
    import numpy as np

    ordered = sorted(samples, key=lambda sample: sample.sample_id)
    if len(ordered) < 2:
        assignments = {
            sample.sample_id: ClusterAssignment(UNKNOWN, 0.0, None, "not_enough_color_samples")
            for sample in ordered
        }
        return assignments, {
            "method": "deterministic_kmeans_2",
            "status": "insufficient_samples",
            "sample_count": len(ordered),
            "centers": [],
            "separation": 0.0,
        }

    matrix = np.asarray([sample.feature for sample in ordered], dtype=np.float64)
    quality = np.asarray([sample.quality for sample in ordered], dtype=np.float64)
    first, second = _initialize_centers(matrix, quality)
    centers = np.stack([first, second], axis=0)
    labels = np.zeros(len(matrix), dtype=np.int32)

    for _ in range(50):
        distances = np.linalg.norm(matrix[:, None, :] - centers[None, :, :], axis=2)
        new_labels = np.argmin(distances, axis=1).astype(np.int32)
        if len(set(new_labels.tolist())) < 2:
            farthest = int(np.argmax(np.min(distances, axis=1)))
            new_labels[farthest] = 1 - int(new_labels[farthest])
        new_centers = np.stack([
            np.average(matrix[new_labels == cluster], axis=0, weights=quality[new_labels == cluster] + 0.05)
            for cluster in (0, 1)
        ])
        if np.array_equal(new_labels, labels) and np.allclose(new_centers, centers, atol=1e-8):
            labels = new_labels
            centers = new_centers
            break
        labels = new_labels
        centers = new_centers

    stable_order = sorted(range(2), key=lambda index: tuple(np.round(centers[index], 8).tolist()))
    remap = {old: new for new, old in enumerate(stable_order)}
    centers = centers[stable_order]
    labels = np.asarray([remap[int(label)] for label in labels], dtype=np.int32)
    distances = np.linalg.norm(matrix[:, None, :] - centers[None, :, :], axis=2)
    separation = float(np.linalg.norm(centers[0] - centers[1]))
    own_distances = distances[np.arange(len(matrix)), labels]
    pooled_radius = float(np.median(own_distances))
    separation_ratio = separation / max(pooled_radius, 1e-6)
    supports = [int(np.sum(labels == cluster)) for cluster in (0, 1)]
    radii = [
        float(np.median(own_distances[labels == cluster])) if supports[cluster] else 0.0
        for cluster in (0, 1)
    ]
    minimum_separation_ratio = 1.10
    clusters_reliable = (
        separation >= minimum_separation
        and separation_ratio >= minimum_separation_ratio
        and min(supports) >= 2
    )

    assignments: dict[str, ClusterAssignment] = {}
    for index, sample in enumerate(ordered):
        cluster_id = int(labels[index])
        own = float(distances[index, cluster_id])
        other = float(distances[index, 1 - cluster_id])
        margin = max(0.0, min(1.0, (other - own) / max(other + own, 1e-8)))
        proximity = max(0.0, min(1.0, 1.0 - own / max(separation, 1e-8)))
        confidence = (0.65 * margin + 0.35 * proximity) * float(sample.quality)
        outlier_limit = max(0.12, radii[cluster_id] * 2.75, separation * 0.50)

        if not clusters_reliable:
            assignment = ClusterAssignment(UNKNOWN, 0.0, cluster_id, "clusters_not_reliable")
        elif own > outlier_limit:
            assignment = ClusterAssignment(
                UNKNOWN,
                round(max(0.0, min(1.0, confidence)), 6),
                cluster_id,
                "color_outlier",
            )
        elif confidence < minimum_confidence:
            assignment = ClusterAssignment(
                UNKNOWN,
                round(max(0.0, min(1.0, confidence)), 6),
                cluster_id,
                "ambiguous_team_color",
            )
        else:
            team = TEAM_A if cluster_id == 0 else TEAM_B
            assignment = ClusterAssignment(
                team,
                round(max(0.0, min(1.0, confidence)), 6),
                cluster_id,
                "deterministic_color_cluster",
            )
        assignments[sample.sample_id] = assignment

    metadata = {
        "method": "deterministic_kmeans_2",
        "status": "ready" if clusters_reliable else "unreliable",
        "sample_count": len(ordered),
        "minimum_team_confidence": minimum_confidence,
        "minimum_cluster_separation": minimum_separation,
        "minimum_separation_ratio": minimum_separation_ratio,
        "centers": [
            [round(float(value), 8) for value in center.tolist()]
            for center in centers
        ],
        "separation": round(separation, 8),
        "pooled_radius": round(pooled_radius, 8),
        "separation_ratio": round(separation_ratio, 8),
        "cluster_support": supports,
        "cluster_radius": [round(radius, 8) for radius in radii],
        "labels_are_anonymous": True,
    }
    return assignments, metadata
