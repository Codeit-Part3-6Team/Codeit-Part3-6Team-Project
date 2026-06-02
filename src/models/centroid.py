from __future__ import annotations

import math
from collections import defaultdict
from typing import Any


class MeanRgbCentroidClassifier:
    """파이프라인 검증용 의존성 없는 더미 분류기."""

    def __init__(self) -> None:
        self.centroids: dict[str, tuple[float, float, float]] = {}

    def fit(self, samples: list[tuple[tuple[float, float, float], str]]) -> None:
        grouped: dict[str, list[tuple[float, float, float]]] = defaultdict(list)
        for features, label in samples:
            grouped[label].append(features)
        self.centroids = {
            label: tuple(sum(values[i] for values in items) / len(items) for i in range(3))
            for label, items in grouped.items()
        }

    def predict_one(self, features: tuple[float, float, float]) -> str:
        if not self.centroids:
            raise RuntimeError("Model is not fitted")
        return min(
            self.centroids,
            key=lambda label: math.dist(features, self.centroids[label]),
        )

    def predict(self, features: list[tuple[float, float, float]]) -> list[str]:
        return [self.predict_one(item) for item in features]

    def to_dict(self) -> dict[str, Any]:
        return {"model_type": "mean_rgb_centroid", "centroids": self.centroids}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MeanRgbCentroidClassifier":
        model = cls()
        model.centroids = {
            label: tuple(float(v) for v in values)
            for label, values in payload["centroids"].items()
        }
        return model

