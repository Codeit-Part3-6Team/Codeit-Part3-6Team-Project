from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    # scripts/를 직접 실행해도 src 패키지를 찾을 수 있게 project root를 추가합니다.
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.comparison import COMPARISON_COLUMNS, compare_rag_retrievers


def main() -> None:
    """여러 RAG retriever config를 평가하고 비교 리포트를 생성합니다."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument(
        "--configs",
        nargs="+",
        default=[
            "configs/experiments/rag/rag_smoke_keyword.yaml",
            "configs/experiments/rag/rag_smoke_test.yaml",
            "configs/experiments/rag/rag_smoke_hybrid.yaml",
        ],
    )
    parser.add_argument("--output", default="reports/rag_retriever_comparison.csv")
    args = parser.parse_args()

    rows = compare_rag_retrievers(args.configs, args.project_root, args.output)
    print(f"wrote {args.output} ({len(rows)} retrievers)")
    print(",".join(COMPARISON_COLUMNS))
    for row in rows:
        print(",".join(str(row.get(column, "")) for column in COMPARISON_COLUMNS))


if __name__ == "__main__":
    main()
