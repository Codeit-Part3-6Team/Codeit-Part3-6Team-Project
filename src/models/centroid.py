from __future__ import annotations

import math
from collections import defaultdict
from typing import Any


class MeanRgbCentroidClassifier:
    """Tiny image classifier used only to verify the pipeline wiring.

    It averages RGB values per class and predicts the nearest class centroid.
    This is intentionally simple; it is not meant to be a production model.
    """

    def __init__(self) -> None:
        self.centroids: dict[str, tuple[float, float, float]] = {}

    def fit(self, samples: list[tuple[tuple[float, float, float], str]]) -> None:
        """Store the mean RGB centroid for each label."""
        grouped: dict[str, list[tuple[float, float, float]]] = defaultdict(list)
        for features, label in samples:
            grouped[label].append(features)
        self.centroids = {
            label: tuple(sum(values[i] for values in items) / len(items) for i in range(3))
            for label, items in grouped.items()
        }

    def predict_one(self, features: tuple[float, float, float]) -> str:
        """Predict the nearest centroid label for one RGB feature vector."""
        if not self.centroids:
            raise RuntimeError("Model is not fitted")
        return min(
            self.centroids,
            key=lambda label: math.dist(features, self.centroids[label]),
        )

    def predict(self, features: list[tuple[float, float, float]]) -> list[str]:
        """Predict labels for multiple RGB feature vectors."""
        return [self.predict_one(item) for item in features]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the lightweight model to JSON-compatible data."""
        return {"model_type": "mean_rgb_centroid", "centroids": self.centroids}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MeanRgbCentroidClassifier":
        """Restore a model saved by `to_dict`."""
        model = cls()
        model.centroids = {
            label: tuple(float(v) for v in values)
            for label, values in payload["centroids"].items()
        }
        return model
