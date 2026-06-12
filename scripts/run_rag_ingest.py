from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    # scripts/를 직접 실행해도 src 패키지를 찾을 수 있게 project root를 추가합니다.
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.pipeline import run_rag_ingest


def main() -> None:
    """RAG 문서를 chunk 산출물로 변환합니다."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/experiments/rag/rag_semantic.yaml")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    print(run_rag_ingest(args.config, args.project_root))


if __name__ == "__main__":
    main()
