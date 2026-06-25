"""eval_questions.csv의 expected_answer를 chunks.csv에서 자동 검색하여
expected_chunk_ids를 재생성합니다.

사용법:
    python scripts/auto_label_chunks.py \
        --chunks experiments/rag_hybrid/chunks.csv \
        --questions data/rag_sample/eval_questions.csv \
        --output data/rag_sample/eval_questions_relabeled.csv

동작:
    1. 각 질문의 expected_answer를 정규화
    2. 같은 문서(source_doc_id)의 chunk text에서 substring 검색
    3. 매칭된 chunk_id를 expected_chunk_ids로 설정
    4. unmatched 질문은 별도 CSV로 저장
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    csv.field_size_limit(int(1e9))
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(path: str | Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _extract_doc_id(chunk_id: str) -> str:
    """chunk_id에서 문서 ID prefix를 추출합니다.

    chunk_id 형식:
        - 20241001798_chunk_0001  (숫자로 시작)
        - R25BK00559883_chunk_0041 (R로 시작)
        - P2024-00202-1_chunk_0253 (P로 시작, 하이픈 포함)
        - B5202401778_chunk_0001    (B로 시작)
        - 9244492_chunk_0001       (숫자만)
    """
    match = re.match(r"(.+?)_chunk_\d+$", chunk_id)
    if match:
        return match.group(1)
    return chunk_id


def _normalize(text: str) -> str:
    """공백, 쉼표, 따옴표, 줄바꿈 제거."""
    text = text.strip("\"' \n\r")
    text = re.sub(r"[\s,，]+", "", text)
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description="eval_questions.csv expected_chunk_ids 자동 라벨링")
    parser.add_argument("--chunks", required=True, help="chunks.csv 경로")
    parser.add_argument("--questions", required=True, help="eval_questions.csv 경로")
    parser.add_argument("--output", default=None, help="출력 CSV 경로 (기본값: --questions 옆에 _relabeled)")
    args = parser.parse_args()

    chunks_path = Path(args.chunks)
    questions_path = Path(args.questions)
    output_path = Path(args.output) if args.output else questions_path.with_name(
        f"{questions_path.stem}_relabeled{questions_path.suffix}"
    )

    if not chunks_path.exists():
        raise FileNotFoundError(f"chunks.csv not found: {chunks_path}")
    if not questions_path.exists():
        raise FileNotFoundError(f"eval_questions.csv not found: {questions_path}")

    chunks_rows = _read_csv(chunks_path)
    question_rows = _read_csv(questions_path)

    chunks_by_doc: dict[str, list[dict[str, str]]] = {}
    for chunk in chunks_rows:
        doc_id = _extract_doc_id(chunk.get("chunk_id", ""))
        chunks_by_doc.setdefault(doc_id, []).append(chunk)

    relabeled: list[dict[str, str]] = []
    unmatched: list[dict[str, str]] = []
    total = len(question_rows)
    matched_count = 0

    for row in question_rows:
        question = row.get("question", "")
        expected_answer = row.get("expected_answer", "")
        source_doc_id = row.get("source_doc_id", "")

        norm_expected = _normalize(expected_answer)
        if not norm_expected:
            unmatched.append(row)
            continue

        candidate_chunks = chunks_by_doc.get(source_doc_id, [])
        if not candidate_chunks and source_doc_id:
            unmatched.append(row)
            continue

        if not candidate_chunks:
            for doc_id, chunks in chunks_by_doc.items():
                for chunk in chunks:
                    norm_text = _normalize(str(chunk.get("text", "")))
                    if norm_expected in norm_text:
                        candidate_chunks.append(chunk)
                if candidate_chunks:
                    source_doc_id = doc_id
                    break

        found_ids: list[str] = []
        for chunk in candidate_chunks:
            norm_text = _normalize(str(chunk.get("text", "")))
            if norm_expected in norm_text:
                found_ids.append(chunk.get("chunk_id", ""))

        if found_ids:
            new_row = dict(row)
            new_row["expected_chunk_ids"] = "|".join(found_ids)
            if source_doc_id and "source_doc_id" not in new_row:
                new_row["source_doc_id"] = source_doc_id
            relabeled.append(new_row)
            matched_count += 1
        else:
            unmatched.append(row)

    output_columns = list(relabeled[0].keys()) if relabeled else list(question_rows[0].keys())
    _write_csv(output_path, relabeled, output_columns)

    unmatched_path = output_path.with_name(f"{output_path.stem}_unmatched{output_path.suffix}")
    if unmatched:
        _write_csv(unmatched_path, unmatched, list(question_rows[0].keys()))

    print(f"총 질문: {total}")
    print(f"매칭 성공: {matched_count} ({matched_count / total * 100:.1f}%)")
    print(f"매칭 실패: {len(unmatched)} ({len(unmatched) / total * 100:.1f}%)")
    print(f"출력: {output_path}")
    if unmatched:
        print(f"unmatched: {unmatched_path}")


if __name__ == "__main__":
    main()
