from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


class KeywordTextClassifier:
    """Tiny keyword-count classifier used for text pipeline smoke tests.

    The model memorizes token counts per label and predicts the label with the
    largest overlap. It exists to validate data loading, artifact writing, and
    prediction plumbing before a real HuggingFace model is used.
    """

    def __init__(self) -> None:
        self.label_token_counts: dict[str, dict[str, int]] = {}
        self.label_counts: dict[str, int] = {}

    def fit(self, samples: list[tuple[str, str]]) -> None:
        """Count tokens per label from `(text, label)` samples."""
        token_counts: dict[str, Counter[str]] = defaultdict(Counter)
        label_counts: Counter[str] = Counter()
        for text, label in samples:
            label_counts[label] += 1
            token_counts[label].update(_tokenize(text))
        self.label_counts = dict(label_counts)
        self.label_token_counts = {
            label: dict(counts) for label, counts in token_counts.items()
        }

    def predict_one(self, text: str) -> str:
        """Predict one label by token overlap with each label vocabulary."""
        if not self.label_token_counts:
            raise RuntimeError("Model is not fitted")
        tokens = _tokenize(text)
        scores: dict[str, int] = {}
        for label, counts in self.label_token_counts.items():
            scores[label] = sum(counts.get(token, 0) for token in tokens)
        return max(scores, key=lambda label: (scores[label], self.label_counts.get(label, 0)))

    def predict(self, texts: list[str]) -> list[str]:
        """Predict labels for multiple texts."""
        return [self.predict_one(text) for text in texts]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the lightweight model to JSON-compatible data."""
        return {
            "model_type": "keyword_text_classifier",
            "label_token_counts": self.label_token_counts,
            "label_counts": self.label_counts,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "KeywordTextClassifier":
        """Restore a model saved by `to_dict`."""
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
    """Tokenize enough for smoke tests without adding external NLP dependencies."""
    return [
        token.strip(".,!?;:()[]{}\"'").lower()
        for token in text.split()
        if token.strip(".,!?;:()[]{}\"'")
    ]
