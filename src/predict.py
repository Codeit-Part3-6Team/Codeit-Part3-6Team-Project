from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_config
from src.data import read_ppm_mean_rgb
from src.models.centroid import MeanRgbCentroidClassifier
from src.models.text_keyword import KeywordTextClassifier
from src.utils.logger import setup_logger
from src.utils.paths import ensure_dir


def predict_one(config_path: str | Path, project_root: str | Path, input_path: str | Path) -> str:
    root = Path(project_root)
    config = load_config(config_path)
    model_path = root / config["paths"]["output_dir"] / "best_model.json"
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
    raise ValueError(f"Unsupported model artifact: {payload.get('model_type')}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    label = predict_one(args.config, args.project_root, args.input)
    output_dir = Path(args.project_root) / load_config(args.config)["paths"]["output_dir"]
    ensure_dir(output_dir)
    logger = setup_logger("predict", output_dir / "predict.log")
    with (output_dir / "predictions.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["input", "prediction"])
        writer.writeheader()
        writer.writerow({"input": args.input, "prediction": label})
    logger.info("Prediction saved: %s -> %s", args.input, label)
    print({"input": args.input, "prediction": label})


if __name__ == "__main__":
    main()
