from __future__ import annotations

from src.models.centroid import MeanRgbCentroidClassifier
from src.models.text_keyword import KeywordTextClassifier


def build_model(name: str) -> MeanRgbCentroidClassifier | KeywordTextClassifier:
    if name == "mean_rgb_centroid":
        return MeanRgbCentroidClassifier()
    if name == "keyword_text_classifier":
        return KeywordTextClassifier()
    raise ValueError(
        f"Unsupported model '{name}'. Add it to src/models/registry.py."
    )
