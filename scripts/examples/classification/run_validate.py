from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    # scripts/examples/classification/를 어디서 실행하든 src 패키지를 import할 수 있게 project root를 경로에 추가합니다.
    sys.path.insert(0, str(PROJECT_ROOT))

from src.validate_data import validate_data


def main() -> None:
    """학습/예측 전에 processed dataset이 계약을 만족하는지 검증합니다."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/examples/classification/image_processed")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = Path(args.project_root) / data_dir

    result = validate_data(data_dir)
    print(result)
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
