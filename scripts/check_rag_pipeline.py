from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    # scripts/를 직접 실행해도 src 패키지를 찾을 수 있게 project root를 추가합니다.
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.validation import check_rag_pipeline


def main() -> None:
    """RAG pipeline 실행 전 config와 입력 경로를 점검합니다."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/experiments/rag/rag_smoke_test.yaml")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    result = check_rag_pipeline(args.config, args.project_root)
    print(result)
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
