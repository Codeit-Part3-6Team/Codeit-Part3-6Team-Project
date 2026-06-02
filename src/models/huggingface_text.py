from __future__ import annotations


class HuggingFaceSequenceClassifier:
    """HuggingFace Transformers 기반 텍스트 분류 모델 adapter 자리."""

    def __init__(self, model_name: str, num_labels: int) -> None:
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            raise ImportError(
                "HuggingFace 모델을 사용하려면 `pip install transformers`가 필요합니다."
            ) from exc

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            num_labels=num_labels,
        )

