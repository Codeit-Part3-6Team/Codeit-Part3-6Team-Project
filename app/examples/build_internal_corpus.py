"""내부 RFP 문서 전체 인덱스 생성 예시.

VM의 `/shared/data/raw_docs/`처럼 내부 문서가 모여 있는 디렉토리를
한 번에 ingest해서 전체 문서 선택 UI가 재사용할 run을 만듭니다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = PROJECT_ROOT / "app"
for path in (PROJECT_ROOT, APP_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from services.rag_service import create_and_ingest, get_documents


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-docs-dir",
        default="/shared/data/raw_docs",
        help="내부 RFP 원문 문서가 모여 있는 디렉토리",
    )
    args = parser.parse_args()

    result = create_and_ingest(args.raw_docs_dir)
    if result.get("status") != "ready":
        raise RuntimeError(result.get("error") or "internal corpus ingest failed")

    run_id = result["run_id"]
    documents = get_documents(run_id)
    print(f"created internal corpus run: {run_id}")
    print(f"documents={len(documents)} chunks={result['chunks']} embeddings={result['embeddings']}")
    print("이 run_id는 UI에 보여주지 않고 내부 문서 인덱스로만 사용합니다.")


if __name__ == "__main__":
    main()
