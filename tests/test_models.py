from __future__ import annotations

from src.models import build_model
from src.models.centroid import MeanRgbCentroidClassifier
from src.models.huggingface_text import _is_improved, is_huggingface_model
from src.models.text_keyword import KeywordTextClassifier


def test_build_model_uses_registry():
    assert isinstance(build_model("mean_rgb_centroid"), MeanRgbCentroidClassifier)
    assert isinstance(build_model("keyword_text_classifier"), KeywordTextClassifier)


def test_registry_marks_huggingface_model_as_config_driven():
    assert is_huggingface_model("huggingface_sequence_classifier")


def test_huggingface_metric_improvement_uses_mode_and_min_delta():
    assert _is_improved(0.8, None, mode="max", min_delta=0.0)
    assert _is_improved(0.9, 0.8, mode="max", min_delta=0.01)
    assert not _is_improved(0.805, 0.8, mode="max", min_delta=0.01)
    assert _is_improved(0.1, 0.2, mode="min", min_delta=0.01)
    assert not _is_improved(0.195, 0.2, mode="min", min_delta=0.01)


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
