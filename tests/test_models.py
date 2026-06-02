from __future__ import annotations

from src.models import build_model
from src.models.centroid import MeanRgbCentroidClassifier
from src.models.text_keyword import KeywordTextClassifier


def test_build_model_uses_registry():
    assert isinstance(build_model("mean_rgb_centroid"), MeanRgbCentroidClassifier)
    assert isinstance(build_model("keyword_text_classifier"), KeywordTextClassifier)


def test_centroid_classifier_predicts_nearest_label_after_roundtrip():
    model = MeanRgbCentroidClassifier()
    model.fit([
        ((1.0, 0.0, 0.0), "red"),
        ((0.9, 0.1, 0.1), "red"),
        ((0.0, 0.0, 1.0), "blue"),
    ])

    restored = MeanRgbCentroidClassifier.from_dict(model.to_dict())

    assert restored.predict_one((0.95, 0.05, 0.05)) == "red"
    assert restored.predict_one((0.0, 0.1, 0.9)) == "blue"


def test_keyword_text_classifier_predicts_keyword_label_after_roundtrip():
    model = KeywordTextClassifier()
    model.fit([
        ("great bright good", "positive"),
        ("bad slow wrong", "negative"),
    ])

    restored = KeywordTextClassifier.from_dict(model.to_dict())

    assert restored.predict_one("great result") == "positive"
    assert restored.predict_one("slow and wrong") == "negative"

