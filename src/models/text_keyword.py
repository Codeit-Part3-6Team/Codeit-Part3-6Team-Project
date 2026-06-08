from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


class KeywordTextClassifier:
    """텍스트 파이프라인 smoke test를 위한 작은 keyword-count 분류기입니다.

    label별 token 빈도를 기억한 뒤 overlap이 가장 큰 label을 예측합니다.
    실제 성능 모델이 아니라 HuggingFace 모델을 붙이기 전 파이프라인을 검증하기 위한 모델입니다.
    """

    def __init__(self) -> None:
        self.label_token_counts: dict[str, dict[str, int]] = {}
        self.label_counts: dict[str, int] = {}

    def fit(self, samples: list[tuple[str, str]]) -> None:
        """`(text, label)` sample에서 label별 token 빈도를 셉니다."""
        token_counts: dict[str, Counter[str]] = defaultdict(Counter)
        label_counts: Counter[str] = Counter()
        for text, label in samples:
            label_counts[label] += 1
            # 형태소 분석 없이 공백 token만 사용해 외부 NLP 의존성을 만들지 않습니다.
            token_counts[label].update(_tokenize(text))
        self.label_counts = dict(label_counts)
        self.label_token_counts = {
            label: dict(counts) for label, counts in token_counts.items()
        }

    def predict_one(self, text: str) -> str:
        """label별 vocabulary와 token overlap을 비교해 label 하나를 예측합니다."""
        if not self.label_token_counts:
            raise RuntimeError("Model is not fitted")
        tokens = _tokenize(text)
        scores: dict[str, int] = {}
        for label, counts in self.label_token_counts.items():
            scores[label] = sum(counts.get(token, 0) for token in tokens)
        # 점수가 같으면 학습 샘플이 더 많은 label을 선택해 결과가 deterministic하게 나오도록 합니다.
        return max(scores, key=lambda label: (scores[label], self.label_counts.get(label, 0)))

    def predict(self, texts: list[str]) -> list[str]:
        """여러 텍스트에 대한 label을 예측합니다."""
        return [self.predict_one(text) for text in texts]

    def to_dict(self) -> dict[str, Any]:
        """가벼운 모델 상태를 JSON-compatible dict로 변환합니다."""
        return {
            "model_type": "keyword_text_classifier",
            "label_token_counts": self.label_token_counts,
            "label_counts": self.label_counts,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "KeywordTextClassifier":
        """`to_dict`로 저장한 모델 상태를 복원합니다."""
        model = cls()
        model.label_token_counts = {
            label: {token: int(count) for token, count in counts.items()}
            for label, counts in payload["label_token_counts"].items()
        }
        model.label_counts = {
            label: int(count) for label, count in payload["label_counts"].items()
        }
        return model


def _tokenize(text: str) -> list[str]:
    """외부 NLP 의존성 없이 smoke test에 필요한 수준으로만 tokenize합니다."""
    return [
        token.strip(".,!?;:()[]{}\"'").lower()
        for token in text.split()
        if token.strip(".,!?;:()[]{}\"'")
    ]
