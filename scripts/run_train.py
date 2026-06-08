from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    # scripts/를 어디서 실행하든 src 패키지를 import할 수 있게 project root를 경로에 추가합니다.
    sys.path.insert(0, str(PROJECT_ROOT))

from src.train import run_training


def main() -> None:
    """config 파일 하나로 실험 학습을 실행하고 최종 metric을 출력합니다."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    metrics = run_training(args.config, args.project_root)
    print(metrics)


if __name__ == "__main__":
    main()
