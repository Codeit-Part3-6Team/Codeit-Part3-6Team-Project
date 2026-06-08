from __future__ import annotations

import math
from collections import defaultdict
from typing import Any


class MeanRgbCentroidClassifier:
    """파이프라인 연결을 검증하기 위한 아주 작은 이미지 분류기입니다.

    class별 평균 RGB centroid를 저장하고 가장 가까운 centroid를 예측합니다.
    실제 성능 모델이 아니라 data/load/train/predict/artifact 흐름을 확인하기 위한 모델입니다.
    """

    def __init__(self) -> None:
        self.centroids: dict[str, tuple[float, float, float]] = {}

    def fit(self, samples: list[tuple[tuple[float, float, float], str]]) -> None:
        """label별 평균 RGB centroid를 저장합니다."""
        grouped: dict[str, list[tuple[float, float, float]]] = defaultdict(list)
        for features, label in samples:
            grouped[label].append(features)
        self.centroids = {
            label: tuple(sum(values[i] for values in items) / len(items) for i in range(3))
            for label, items in grouped.items()
        }

    def predict_one(self, features: tuple[float, float, float]) -> str:
        """RGB feature 하나에 대해 가장 가까운 centroid label을 예측합니다."""
        if not self.centroids:
            raise RuntimeError("Model is not fitted")
        return min(
            self.centroids,
            key=lambda label: math.dist(features, self.centroids[label]),
        )

    def predict(self, features: list[tuple[float, float, float]]) -> list[str]:
        """여러 RGB feature에 대한 label을 예측합니다."""
        return [self.predict_one(item) for item in features]

    def to_dict(self) -> dict[str, Any]:
        """가벼운 모델 상태를 JSON-compatible dict로 변환합니다."""
        return {"model_type": "mean_rgb_centroid", "centroids": self.centroids}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MeanRgbCentroidClassifier":
        """`to_dict`로 저장한 모델 상태를 복원합니다."""
        model = cls()
        model.centroids = {
            label: tuple(float(v) for v in values)
            for label, values in payload["centroids"].items()
        }
        return model
