from __future__ import annotations

from src.models.centroid import MeanRgbCentroidClassifier
from src.models.huggingface_text import is_huggingface_model
from src.models.text_keyword import KeywordTextClassifier


def build_model(name: str) -> MeanRgbCentroidClassifier | KeywordTextClassifier:
    if name == "mean_rgb_centroid":
        return MeanRgbCentroidClassifier()
    if name == "keyword_text_classifier":
        return KeywordTextClassifier()
    if is_huggingface_model(name):
        raise ValueError(
            "HuggingFace models need config values such as model.model_name and labels. "
            "Use scripts/run_train.py with a HuggingFace config instead."
        )
    raise ValueError(
        f"Unsupported model '{name}'. Add it to src/models/registry.py."
    )
