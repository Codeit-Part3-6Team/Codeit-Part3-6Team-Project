"""내부 corpus run 상태 점검 스크립트.

프론트가 어떤 run 을 '내부 문서 인덱스'로 잡는지, 문서가 몇 건인지 확인합니다.
목록이 1건만 뜨거나 요약이 비어 보일 때 먼저 이걸로 상태를 확인하세요.

실행 (app/ 상위 프로젝트 루트에서, conda 환경 활성화 상태):
    python app/examples/list_corpus_runs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = PROJECT_ROOT / "app"
for path in (PROJECT_ROOT, APP_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from services.rag_service import list_runs  # noqa: E402


def main() -> None:
    runs = list_runs()
    if not runs:
        print("run 이 하나도 없습니다. build_internal_corpus.py 로 먼저 ingest 하세요.")
        return

    print(f"총 {len(runs)}개 run:\n")
    header = f"{'run_id':<28} {'문서수':>6}  {'상태':<10} 생성시각"
    print(header)
    print("-" * len(header))
    for r in runs:
        print(f"{str(r.get('run_id','')):<28} "
              f"{int(r.get('documents') or 0):>6}  "
              f"{str(r.get('status','')):<10} "
              f"{r.get('created_at','')}")

    best = max(runs, key=lambda r: int(r.get("documents") or 0))
    print(f"\n→ 프론트가 선택할 run: {best['run_id']} "
          f"(문서 {int(best.get('documents') or 0)}건)")
    if int(best.get("documents") or 0) < 10:
        print("  ⚠️ 문서가 너무 적습니다. 전체 내부 corpus(약 98건)를 ingest 하세요:")
        print("     python app/examples/build_internal_corpus.py --raw-docs-dir <원문 폴더>")


if __name__ == "__main__":
    main()
