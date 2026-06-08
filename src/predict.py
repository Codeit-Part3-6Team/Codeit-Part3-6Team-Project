from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_config
from src.artifacts import resolve_experiment_dir
from src.data import read_ppm_mean_rgb
from src.models.centroid import MeanRgbCentroidClassifier
from src.models.huggingface_text import MODEL_TYPE, HuggingFaceSequenceClassifier
from src.models.text_keyword import KeywordTextClassifier


def predict_one(config_path: str | Path, project_root: str | Path, input_path: str | Path) -> str:
    """config가 가리키는 실험 artifact를 사용해 입력 하나를 예측합니다."""
    root = Path(project_root)
    config = load_config(config_path)
    model_path = resolve_experiment_dir(root, config) / "best_model.json"
    payload = json.loads(model_path.read_text(encoding="utf-8"))
    task = config["data"]["task"]
    if payload["model_type"] == "mean_rgb_centroid":
        model = MeanRgbCentroidClassifier.from_dict(payload)
        return model.predict_one(read_ppm_mean_rgb(root / input_path))
    if payload["model_type"] == "keyword_text_classifier":
        model = KeywordTextClassifier.from_dict(payload)
        if task == "text_classification":
            candidate = Path(input_path)
            text_path = candidate if candidate.is_absolute() else root / candidate
            input_text = text_path.read_text(encoding="utf-8") if text_path.exists() else str(input_path)
            return model.predict_one(input_text)
    if payload["model_type"] == MODEL_TYPE:
        model = HuggingFaceSequenceClassifier.from_artifact(model_path.parent)
        candidate = Path(input_path)
        text_path = candidate if candidate.is_absolute() else root / candidate
        input_text = text_path.read_text(encoding="utf-8") if text_path.exists() else str(input_path)
        return model.predict_one(input_text)
    raise ValueError(f"Unsupported model artifact: {payload.get('model_type')}")


def main() -> None:
    """공식 scripts 진입점으로 CLI 처리를 위임합니다."""
    from scripts.run_predict import main as script_main

    script_main()


if __name__ == "__main__":
    main()
