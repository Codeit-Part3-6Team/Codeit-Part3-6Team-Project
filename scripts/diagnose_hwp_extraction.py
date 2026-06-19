from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.document_loader import _parse_hwp_document, _parse_pdf_document


MIN_CHARS = 500

ISSUE_DOCS = [
    ("20240827859", "EIP3.0 고압가스 안전관리 시스템 구축 용역"),
    ("20240821865", "스포츠윤리센터 LMS(학습지원시스템) 기능개선"),
    ("", "학업성취도 다차원 종단분석 통합시스템 1차 고도화 용역"),
    ("20240910050", "2025 구미아시아육상경기선수권대회 종합정보시스템 및 홈페이지 등 구축 용역"),
    ("", "2024년 건설기술에 관한 특허·실용신안 활용실적 관리시스템 개편 용역"),
    ("20240903688", "JST 공유대학(원) xAPI기반 LRS시스템 구축"),
    ("", "사업장 사회보험료 지원 고시 개정에 따른 정보시스템 보완 개발"),
]


def _find_file(files_dir: Path, doc_id: str, title: str, filename: str) -> Path | None:
    if filename:
        candidate = files_dir / filename
        if candidate.exists():
            return candidate
    title_slug = title.replace(" ", "").replace("/", "").replace("·", "")
    for path in sorted(files_dir.rglob("*")):
        if path.is_file() and (doc_id in path.stem or title_slug[:10] in path.stem.replace(" ", "")):
            return path
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="문제 HWP/PDF 문서를 파이프라인 직접 파서로 추출 테스트합니다."
    )
    parser.add_argument(
        "--csv", default="data/raw/data_list.csv",
        help="data_list.csv 경로 (기본: data/raw/data_list.csv)",
    )
    parser.add_argument(
        "--files-dir", default="data/raw/files",
        help="원본 HWP/PDF 파일 디렉터리 (기본: data/raw/files)",
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument(
        "--min-chars", type=int, default=MIN_CHARS,
        help=f"텍스트 부족 판정 기준 문자 수 (기본: {MIN_CHARS})",
    )
    args = parser.parse_args()

    proj = Path(args.project_root).resolve()
    csv_path = proj / args.csv
    files_dir = proj / args.files_dir

    if not csv_path.exists():
        print(f"[ERROR] data_list.csv 없음: {csv_path}")
        sys.exit(1)

    csv.field_size_limit(int(1e9))
    with csv_path.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    results: list[dict] = []
    for doc_id, title in ISSUE_DOCS:
        matched = None
        for row in rows:
            row_id = row.get("공고 번호", "").strip()
            row_title = row.get("사업명", "").strip()
            if doc_id and row_id == doc_id:
                matched = row
                break
            if not doc_id and row_title == title:
                matched = row
                break
            if row_title[:15] == title[:15]:
                matched = row
                break

        if matched is None:
            results.append({"title": title, "error": "data_list.csv에서 매칭 실패"})
            continue

        csv_text = matched.get("텍스트", "").strip()
        csv_len = len(csv_text)
        filename = matched.get("파일명", "").strip()
        file_path = _find_file(files_dir, doc_id, title, filename)

        result = {
            "title": title,
            "doc_id": doc_id or "(없음)",
            "csv_len": csv_len,
            "csv_status": "정상" if csv_len >= args.min_chars else "부족",
        }

        if file_path is None:
            result["direct_parse"] = "파일 없음"
            result["direct_len"] = 0
            result["direct_status"] = "-"
        else:
            suffix = file_path.suffix.lower().lstrip(".")
            try:
                if suffix == "hwp":
                    parsed = _parse_hwp_document(proj, file_path)
                elif suffix == "pdf":
                    parsed = _parse_pdf_document(proj, file_path)
                elif suffix == "hwpx":
                    from src.rag.document_loader import _parse_hwpx_document
                    parsed = _parse_hwpx_document(proj, file_path)
                else:
                    result["direct_parse"] = f"지원 안 함: {suffix}"
                    result["direct_len"] = 0
                    result["direct_status"] = "-"
                    results.append(result)
                    continue

                direct_text = " ".join(p["text"] for p in parsed)
                direct_len = len(direct_text)
                result["direct_parse"] = "성공" if parsed else "빈 결과"
                result["direct_len"] = direct_len
                result["direct_status"] = "정상" if direct_len >= args.min_chars else "부족"
            except Exception as exc:
                result["direct_parse"] = f"오류: {exc}"
                result["direct_len"] = 0
                result["direct_status"] = "-"

        results.append(result)

    print("=" * 80)
    print("HWP/PDF 직접 파서 진단 결과")
    print(f"기준: {args.min_chars}자 이상이면 정상")
    print("=" * 80)
    print()

    recovered = 0
    still_fail = 0
    no_file = 0

    for r in results:
        print(f"문서: {r['title'][:60]}")
        print(f"  공고번호: {r['doc_id']}")
        print(f"  CSV 텍스트: {r['csv_len']}자 ({r['csv_status']})")
        print(f"  직접 파싱:   {r['direct_len']}자 ({r.get('direct_parse', '-')})")
        print()

        if r.get("direct_parse") in ("파일 없음",):
            no_file += 1
        elif isinstance(r.get("direct_parse"), str) and r["direct_parse"].startswith("오류"):
            still_fail += 1
        elif r.get("direct_status") == "정상":
            recovered += 1
        else:
            still_fail += 1

    print("=" * 80)
    print(f"회복 가능: {recovered}개  |  여전히 부족: {still_fail}개  |  파일 없음: {no_file}개")
    print("=" * 80)


if __name__ == "__main__":
    main()
