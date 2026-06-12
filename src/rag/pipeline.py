from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from src.artifacts import (
    prepare_experiment_dir,
    resolve_experiment_dir,
    write_failure_artifact,
    write_run_info,
    write_run_status,
)
from src.config import load_config, write_config_copy, write_json
from src.rag.document_loader import load_documents
from src.rag.engines import build_rag_engine
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
EVALUATION_COLUMNS = [
    "question",
    "expected_answer",
    "expected_chunk_ids",
    "retrieved_chunk_ids",
    "citation_chunk_ids",
    "answer",
    "retrieval_hit",
    "answer_contains_expected",
    "citation_correct",
    "status",
]


def run_rag_ingest(config_path: str | Path, project_root: str | Path = ".") -> dict[str, int]:
    """RAG 원본 문서를 읽고 document/chunk/embedding 산출물을 저장합니다."""
    root = Path(project_root)
    config_path = _resolve_path(root, config_path)
    config = load_config(config_path)
    output_dir = prepare_experiment_dir(root, config, check_existing=True)

    _write_run_status(output_dir, "rag_ingest", "running")
    try:
        rag_cfg = config.get("rag", {})
        checkpoint_cfg = rag_cfg.get("checkpoint", {})
        resume_enabled = bool(checkpoint_cfg.get("enabled", True) and checkpoint_cfg.get("resume", True))
        loader_cfg = config.get("rag", {}).get("loader", {})
        raw_docs_dir = config["paths"]["raw_docs_dir"]
        documents_path = output_dir / "parsed_documents.csv"
        chunks_path = output_dir / "chunks.csv"
        embeddings_path = output_dir / "embeddings.jsonl"
        engine = build_rag_engine(config, output_dir)

        write_config_copy(config_path, output_dir)
        # RAG resume은 현재 stage 단위입니다.
        # 이미 저장된 artifact가 있으면 해당 stage를 다시 계산하지 않고 재사용합니다.
        if resume_enabled and documents_path.exists():
            documents = _read_csv(documents_path)
        else:
            documents = load_documents(root, raw_docs_dir, loader_cfg.get("file_types", ["txt"]))
            _write_csv(documents_path, documents, DOCUMENT_COLUMNS)
        _write_rag_ingest_checkpoint(output_dir, "documents", documents=len(documents))

        if resume_enabled and chunks_path.exists():
            chunks = _read_csv(chunks_path)
        else:
            chunks = engine.chunk_documents(documents)
            _write_csv(chunks_path, chunks, CHUNK_COLUMNS)
        _write_rag_ingest_checkpoint(output_dir, "chunks", documents=len(documents), chunks=len(chunks))

        if resume_enabled and embeddings_path.exists():
            embeddings = _read_jsonl(embeddings_path)
        else:
            embeddings = engine.embed_chunks(chunks)
            _write_jsonl(embeddings_path, embeddings)
        _write_rag_ingest_checkpoint(
            output_dir,
            "embeddings",
            documents=len(documents),
            chunks=len(chunks),
            embeddings=len(embeddings),
        )
        write_run_info(output_dir, config)
        result = {"documents": len(documents), "chunks": len(chunks), "embeddings": len(embeddings)}
        _write_run_status(output_dir, "rag_ingest", "success", result=result)
        return result
    except Exception as exc:
        _write_failure_artifact(output_dir, "rag_ingest", exc)
        raise


def run_rag_retrieve(
    config_path: str | Path,
    project_root: str | Path,
    question: str,
) -> dict[str, Any]:
    """저장된 chunk를 읽어 질문에 대한 검색 결과를 JSON 호환 dict로 반환합니다."""
    root = Path(project_root)
    config_path = _resolve_path(root, config_path)
    config = load_config(config_path)
    output_dir = resolve_experiment_dir(root, config)
    ensure_dir(output_dir)
    _write_run_status(output_dir, "rag_retrieve", "running")
    try:
        return _run_rag_retrieve_checked(config_path, root, config, output_dir, question)
    except Exception as exc:
        _write_failure_artifact(output_dir, "rag_retrieve", exc)
        raise


def _run_rag_retrieve_checked(
    config_path: Path,
    root: Path,
    config: dict[str, Any],
    output_dir: Path,
    question: str,
) -> dict[str, Any]:
    chunks_path = output_dir / "chunks.csv"
    embeddings_path = output_dir / "embeddings.jsonl"
    if not chunks_path.exists() or not embeddings_path.exists():
        # 사용자가 retrieve부터 실행해도 최소 파이프라인은 자동으로 준비되게 합니다.
        run_rag_ingest(config_path, root)

    retriever_cfg = config.get("rag", {}).get("retriever", {})
    chunks = _read_csv(chunks_path)
    method = retriever_cfg.get("method", "keyword")
    engine = build_rag_engine(config, output_dir)
    retrieved = engine.retrieve(
        question,
        chunks,
        _read_jsonl(embeddings_path),
    )
    payload = {
        "question": question,
        "top_k": int(retriever_cfg.get("top_k", 3)),
        "retriever_method": method,
        "retrieved_chunks": retrieved,
    }
    _append_jsonl(output_dir / "retrieval_results.jsonl", payload)
    _write_run_status(output_dir, "rag_retrieve", "success", result={"retrieved": len(retrieved)})
    return payload


def run_rag_chat(config_path: str | Path, project_root: str | Path, question: str) -> dict[str, Any]:
    """검색 결과를 바탕으로 추출형 답변과 citation을 생성합니다."""
    root = Path(project_root)
    config_path = _resolve_path(root, config_path)
    config = load_config(config_path)
    output_dir = resolve_experiment_dir(root, config)
    ensure_dir(output_dir)
    _write_run_status(output_dir, "rag_chat", "running")
    try:
        retrieval = run_rag_retrieve(config_path, root, question)
        answer = build_rag_engine(config, output_dir).answer(question, retrieval["retrieved_chunks"])
        _append_jsonl(output_dir / "answers.jsonl", answer)
        _write_run_status(output_dir, "rag_chat", "success", result={"status": answer["status"]})
        return answer
    except Exception as exc:
        _write_failure_artifact(output_dir, "rag_chat", exc)
        raise


def run_rag_evaluation(config_path: str | Path, project_root: str | Path = ".") -> dict[str, float]:
    """작은 평가 질문 세트로 retrieval/answer/citation metric을 계산합니다."""
    root = Path(project_root)
    config_path = _resolve_path(root, config_path)
    config = load_config(config_path)
    output_dir = resolve_experiment_dir(root, config)
    ensure_dir(output_dir)
    _write_run_status(output_dir, "rag_evaluation", "running")
    try:
        questions_path = _resolve_path(root, config.get("evaluation", {}).get("questions_path", ""))
        if not questions_path.exists():
            raise FileNotFoundError(f"RAG evaluation questions not found: {questions_path}")

        rows = _read_csv(questions_path)
        result_rows: list[dict[str, str]] = []
        analysis_rows: list[dict[str, str]] = []
        engine = build_rag_engine(config, output_dir)
        for row in rows:
            retrieval = run_rag_retrieve(config_path, root, row["question"])
            answer = engine.answer(row["question"], retrieval["retrieved_chunks"])
            _append_jsonl(output_dir / "answers.jsonl", answer)
            expected_chunk_ids = _split_expected_ids(row["expected_chunk_ids"])
            retrieved_ids = {str(item["chunk_id"]) for item in retrieval["retrieved_chunks"]}
            citation_ids = {str(item["chunk_id"]) for item in answer["citations"]}
            retrieval_hit = bool(expected_chunk_ids & retrieved_ids)
            answer_contains_expected = row["expected_answer"] in answer["answer"]
            citation_correct = bool(expected_chunk_ids & citation_ids)
            result_rows.append(
                {
                    "question": row["question"],
                    "retrieval_hit": str(retrieval_hit).lower(),
                    "answer_contains_expected": str(answer_contains_expected).lower(),
                    "citation_correct": str(citation_correct).lower(),
                    "status": answer["status"],
                }
            )
            analysis_rows.append(
                {
                    "question": row["question"],
                    "expected_answer": row["expected_answer"],
                    "expected_chunk_ids": _join_ids(expected_chunk_ids),
                    "retrieved_chunk_ids": _join_ids(retrieved_ids),
                    "citation_chunk_ids": _join_ids(citation_ids),
                    "answer": answer["answer"],
                    "retrieval_hit": str(retrieval_hit).lower(),
                    "answer_contains_expected": str(answer_contains_expected).lower(),
                    "citation_correct": str(citation_correct).lower(),
                    "status": answer["status"],
                }
            )

        metrics = _calculate_metrics(result_rows)
        _write_csv(
            output_dir / "evaluation_results.csv",
            result_rows,
            ["question", "retrieval_hit", "answer_contains_expected", "citation_correct", "status"],
        )
        _write_error_analysis(output_dir, analysis_rows)
        write_json(output_dir / "metrics.json", metrics)
        _write_run_status(output_dir, "rag_evaluation", "success", result=metrics)
        return metrics
    except Exception as exc:
        _write_failure_artifact(output_dir, "rag_evaluation", exc)
        raise


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


def _join_ids(values: set[str]) -> str:
    return "|".join(sorted(values))


def _write_error_analysis(output_dir: Path, rows: list[dict[str, str]]) -> None:
    """RAG 평가 결과를 실패 유형별 오답노트 CSV로 나눠 저장합니다."""
    # 검색 실패와 답변 근거 실패를 분리해야 retriever를 고칠지 answerer를 고칠지 판단하기 쉽습니다.
    bad_retrievals = [row for row in rows if row["retrieval_hit"] != "true"]
    unsupported_answers = [
        row
        for row in rows
        if row["status"] == "answered"
        and (row["citation_correct"] != "true" or row["answer_contains_expected"] != "true")
    ]
    failed_questions = [row for row in rows if row["status"] != "answered"]

    _write_csv(output_dir / "bad_retrievals.csv", bad_retrievals, EVALUATION_COLUMNS)
    _write_csv(output_dir / "unsupported_answers.csv", unsupported_answers, EVALUATION_COLUMNS)
    _write_csv(output_dir / "failed_questions.csv", failed_questions, EVALUATION_COLUMNS)


def _write_run_status(
    output_dir: str | Path,
    operation: str,
    status: str,
    result: dict[str, Any] | None = None,
    error: dict[str, str] | None = None,
) -> None:
    write_run_status(output_dir, operation, status, result=result, error=error)


def _write_failure_artifact(output_dir: str | Path, operation: str, exc: Exception) -> None:
    """실패 원인과 traceback을 파일로 남긴 뒤 호출부가 예외를 다시 올리게 합니다."""
    write_failure_artifact(output_dir, operation, exc)


def _write_rag_ingest_checkpoint(output_dir: str | Path, stage: str, **counts: int) -> None:
    """RAG ingest 단계별 완료 상태를 남겨 다음 실행에서 산출물을 재사용할 수 있게 합니다."""
    payload = {
        "operation": "rag_ingest",
        "stage": stage,
        "counts": counts,
        "artifacts": {
            "documents": "parsed_documents.csv",
            "chunks": "chunks.csv",
            "embeddings": "embeddings.jsonl",
        },
    }
    write_json(Path(output_dir) / "rag_ingest_checkpoint.json", payload)


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    # Windows/Excel에서 저장한 CSV는 UTF-8 BOM을 포함할 수 있으므로 utf-8-sig로 읽습니다.
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
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


def _write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    import json

    with Path(path).open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    import json

    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _resolve_path(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate
