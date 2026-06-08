from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.artifacts import resolve_experiment_dir
from src.config import load_config
from src.predict import predict_one
from src.utils.logger import setup_logger
from src.utils.paths import ensure_dir


def main() -> None:
    """입력 하나를 예측하고 결과를 실험 폴더에 저장합니다."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    label = predict_one(args.config, args.project_root, args.input)
    output_dir = resolve_experiment_dir(args.project_root, load_config(args.config))
    ensure_dir(output_dir)
    logger = setup_logger("predict", output_dir / "predict.log")
    # 예측 결과도 실험 산출물에 남겨야 발표/디버깅 때 어떤 입력을 넣었는지 추적할 수 있습니다.
    with (output_dir / "predictions.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["input", "prediction"])
        writer.writeheader()
        writer.writerow({"input": args.input, "prediction": label})
    logger.info("Prediction saved: %s -> %s", args.input, label)
    print({"input": args.input, "prediction": label})


if __name__ == "__main__":
    main()
