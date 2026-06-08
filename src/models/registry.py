from __future__ import annotations

from src.models.centroid import MeanRgbCentroidClassifier
from src.models.huggingface_text import is_huggingface_model
from src.models.text_keyword import KeywordTextClassifier


def build_model(name: str) -> MeanRgbCentroidClassifier | KeywordTextClassifier:
    """config의 `model.name`에 맞는 가벼운 smoke model을 생성합니다.

    HuggingFace 모델은 base model 이름, label map, weight 저장 폴더가 필요하므로
    이 registry가 아니라 `src.train`의 전용 경로에서 처리합니다.
    """
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
