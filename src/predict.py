from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.artifacts import resolve_experiment_dir
from src.config import load_config
from src.data import read_ppm_mean_rgb
from src.models.centroid import MeanRgbCentroidClassifier
from src.models.huggingface_text import MODEL_TYPE, HuggingFaceSequenceClassifier
from src.models.text_keyword import KeywordTextClassifier


def predict_one(config_path: str | Path, project_root: str | Path, input_path: str | Path) -> str:
    """config가 가리키는 실험 artifact를 사용해 입력 하나를 예측합니다."""
    root = Path(project_root)
    config_path = _resolve_path(root, config_path)
    config = load_config(config_path)
    model_path = resolve_experiment_dir(root, config) / "best_model.json"
    payload = json.loads(model_path.read_text(encoding="utf-8"))
    task = config["data"]["task"]
    # best_model.json의 model_type을 기준으로 저장된 artifact를 어떤 클래스로 복원할지 결정합니다.
    if payload["model_type"] == "mean_rgb_centroid":
        model = MeanRgbCentroidClassifier.from_dict(payload)
        image_path = _resolve_path(root, input_path)
        return model.predict_one(read_ppm_mean_rgb(image_path))
    if payload["model_type"] == "keyword_text_classifier":
        model = KeywordTextClassifier.from_dict(payload)
        if task == "text_classification":
            candidate = Path(input_path)
            text_path = candidate if candidate.is_absolute() else root / candidate
            # 텍스트 예측은 파일 경로와 직접 입력 문자열을 모두 허용해 데모/테스트를 쉽게 합니다.
            input_text = text_path.read_text(encoding="utf-8") if text_path.exists() else str(input_path)
            return model.predict_one(input_text)
    if payload["model_type"] == MODEL_TYPE:
        model = HuggingFaceSequenceClassifier.from_artifact(model_path.parent)
        candidate = Path(input_path)
        text_path = candidate if candidate.is_absolute() else root / candidate
        # HuggingFace 경로도 keyword smoke model과 같은 입력 규칙을 유지합니다.
        input_text = text_path.read_text(encoding="utf-8") if text_path.exists() else str(input_path)
        return model.predict_one(input_text)
    raise ValueError(f"Unsupported model artifact: {payload.get('model_type')}")


def _resolve_path(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def main() -> None:
    """공식 scripts 진입점으로 CLI 처리를 위임합니다."""
    from scripts.run_predict import main as script_main

    script_main()


if __name__ == "__main__":
    main()
