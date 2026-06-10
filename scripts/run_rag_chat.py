from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    # scripts/를 직접 실행해도 src 패키지를 찾을 수 있게 project root를 추가합니다.
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.pipeline import run_rag_chat, run_rag_evaluation


def main() -> None:
    """RAG 답변을 생성하거나 평가 질문 세트를 실행합니다."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rag/rag_smoke_test.yaml")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--question")
    parser.add_argument("--evaluate", action="store_true")
    args = parser.parse_args()

    if args.evaluate:
        print(run_rag_evaluation(args.config, args.project_root))
        return
    if not args.question:
        raise SystemExit("--question 또는 --evaluate 중 하나가 필요합니다.")
    print(run_rag_chat(args.config, args.project_root, args.question))


if __name__ == "__main__":
    main()
