from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from src.artifacts import resolve_experiment_dir, write_run_info
from src.config import load_config, write_config_copy, write_json
from src.rag.answerer import build_answer
from src.rag.chunker import chunk_documents
from src.rag.document_loader import load_text_documents
from src.rag.retriever import retrieve_chunks
from src.utils.paths import ensure_dir


DOCUMENT_COLUMNS = ["document_id", "title", "source_path", "page", "section", "text"]
CHUNK_COLUMNS = [
    "chunk_id",
    "document_id",
    "source_path",
    "page_start",
    "page_end",
    "section",
    "text",
    "token_count",
]


def run_rag_ingest(config_path: str | Path, project_root: str | Path = ".") -> dict[str, int]:
    """RAG 원본 문서를 읽고 parsed_documents.csv와 chunks.csv를 저장합니다."""
    root = Path(project_root)
    config = load_config(config_path)
    output_dir = resolve_experiment_dir(root, config)
    ensure_dir(output_dir)

    raw_docs_dir = config["paths"]["raw_docs_dir"]
    chunk_cfg = config.get("rag", {}).get("chunk", {})
    documents = load_text_documents(root, raw_docs_dir)
    chunks = chunk_documents(
        documents,
        chunk_size=int(chunk_cfg.get("size", 500)),
        overlap=int(chunk_cfg.get("overlap", 80)),
    )

    write_config_copy(config_path, output_dir)
    _write_csv(output_dir / "parsed_documents.csv", documents, DOCUMENT_COLUMNS)
    _write_csv(output_dir / "chunks.csv", chunks, CHUNK_COLUMNS)
    write_run_info(output_dir, config)
    return {"documents": len(documents), "chunks": len(chunks)}


def run_rag_retrieve(
    config_path: str | Path,
    project_root: str | Path,
    question: str,
) -> dict[str, Any]:
    """저장된 chunk를 읽어 질문에 대한 검색 결과를 JSON 호환 dict로 반환합니다."""
    root = Path(project_root)
    config = load_config(config_path)
    output_dir = resolve_experiment_dir(root, config)
    chunks_path = output_dir / "chunks.csv"
    if not chunks_path.exists():
        # 사용자가 retrieve부터 실행해도 최소 파이프라인은 자동으로 준비되게 합니다.
        run_rag_ingest(config_path, root)

    retriever_cfg = config.get("rag", {}).get("retriever", {})
    chunks = _read_csv(chunks_path)
    retrieved = retrieve_chunks(
        question,
        chunks,
        top_k=int(retriever_cfg.get("top_k", 3)),
        score_threshold=float(retriever_cfg.get("score_threshold", 0.0)),
    )
    payload = {
        "question": question,
        "top_k": int(retriever_cfg.get("top_k", 3)),
        "retrieved_chunks": retrieved,
    }
    _append_jsonl(output_dir / "retrieval_results.jsonl", payload)
    return payload


def run_rag_chat(config_path: str | Path, project_root: str | Path, question: str) -> dict[str, Any]:
    """검색 결과를 바탕으로 추출형 답변과 citation을 생성합니다."""
    config = load_config(config_path)
    output_dir = resolve_experiment_dir(project_root, config)
    retrieval = run_rag_retrieve(config_path, project_root, question)
    answer_cfg = config.get("rag", {}).get("answerer", {})
    answer = build_answer(
        question,
        retrieval["retrieved_chunks"],
        fallback_message=answer_cfg.get("fallback_message", "문서에서 확인하지 못했습니다."),
    )
    _append_jsonl(output_dir / "answers.jsonl", answer)
    return answer


def run_rag_evaluation(config_path: str | Path, project_root: str | Path = ".") -> dict[str, float]:
    """작은 평가 질문 세트로 retrieval/answer/citation metric을 계산합니다."""
    root = Path(project_root)
    config = load_config(config_path)
    output_dir = resolve_experiment_dir(root, config)
    questions_path = _resolve_path(root, config.get("evaluation", {}).get("questions_path", ""))
    if not questions_path.exists():
        raise FileNotFoundError(f"RAG evaluation questions not found: {questions_path}")

    rows = _read_csv(questions_path)
    answer_cfg = config.get("rag", {}).get("answerer", {})
    result_rows: list[dict[str, str]] = []
    for row in rows:
        retrieval = run_rag_retrieve(config_path, root, row["question"])
        answer = build_answer(
            row["question"],
            retrieval["retrieved_chunks"],
            fallback_message=answer_cfg.get("fallback_message", "문서에서 확인하지 못했습니다."),
        )
        _append_jsonl(output_dir / "answers.jsonl", answer)
        expected_chunk_ids = _split_expected_ids(row["expected_chunk_ids"])
        retrieved_ids = {str(item["chunk_id"]) for item in retrieval["retrieved_chunks"]}
        citation_ids = {str(item["chunk_id"]) for item in answer["citations"]}
        result_rows.append(
            {
                "question": row["question"],
                "retrieval_hit": str(bool(expected_chunk_ids & retrieved_ids)).lower(),
                "answer_contains_expected": str(row["expected_answer"] in answer["answer"]).lower(),
                "citation_correct": str(bool(expected_chunk_ids & citation_ids)).lower(),
                "status": answer["status"],
            }
        )

    metrics = _calculate_metrics(result_rows)
    _write_csv(
        output_dir / "evaluation_results.csv",
        result_rows,
        ["question", "retrieval_hit", "answer_contains_expected", "citation_correct", "status"],
    )
    write_json(output_dir / "metrics.json", metrics)
    return metrics


def _calculate_metrics(rows: list[dict[str, str]]) -> dict[str, float]:
    total = len(rows) or 1
    return {
        "retrieval_hit_rate": _ratio(rows, "retrieval_hit", total),
        "answer_contains_expected_rate": _ratio(rows, "answer_contains_expected", total),
        "citation_correct_rate": _ratio(rows, "citation_correct", total),
        "not_found_rate": sum(row["status"] == "not_found" for row in rows) / total,
    }


def _ratio(rows: list[dict[str, str]], column: str, total: int) -> float:
    return sum(row[column] == "true" for row in rows) / total


def _split_expected_ids(value: str) -> set[str]:
    return {item.strip() for item in value.replace("|", ",").split(",") if item.strip()}


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(path: str | Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _append_jsonl(path: str | Path, payload: dict[str, Any]) -> None:
    import json

    with Path(path).open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _resolve_path(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate
