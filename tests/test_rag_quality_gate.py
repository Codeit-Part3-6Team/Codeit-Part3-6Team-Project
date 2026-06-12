from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from src.rag.validation import check_rag_pipeline
from src.rag.pipeline import run_rag_chat, run_rag_evaluation, run_rag_ingest, run_rag_retrieve


def test_rag_quality_gate_reproducibility_and_contracts(isolated_project: Path):
    """RAG config pipeline의 재현성, 입출력 계약, 산출물 품질을 함께 확인합니다."""
    config = isolated_project / "configs" / "experiments" / "rag" / "rag_langchain.yaml"
    output_dir = isolated_project / "experiments" / "rag_langchain"

    first_ingest = run_rag_ingest(config, isolated_project)
    first_chunks = (output_dir / "chunks.csv").read_text(encoding="utf-8")
    first_embeddings = (output_dir / "embeddings.jsonl").read_text(encoding="utf-8")
    first_metrics = run_rag_evaluation(config, isolated_project)

    second_ingest = run_rag_ingest(config, isolated_project)
    second_metrics = run_rag_evaluation(config, isolated_project)

    assert first_ingest == second_ingest == {"documents": 3, "chunks": 3, "embeddings": 3}
    assert first_metrics == second_metrics
    assert (output_dir / "chunks.csv").read_text(encoding="utf-8") == first_chunks
    assert (output_dir / "embeddings.jsonl").read_text(encoding="utf-8") == first_embeddings

    documents = _read_csv(output_dir / "parsed_documents.csv")
    chunks = _read_csv(output_dir / "chunks.csv")
    embeddings = _read_jsonl(output_dir / "embeddings.jsonl")
    evaluation_rows = _read_csv(output_dir / "evaluation_results.csv")

    _assert_required_columns(documents, {"document_id", "title", "source_path", "page", "section", "text"})
    _assert_required_columns(
        chunks,
        {"chunk_id", "document_id", "source_path", "page_start", "page_end", "section", "text", "token_count"},
    )
    assert all(row["text"].strip() for row in documents)
    assert all(row["text"].strip() and int(row["token_count"]) > 0 for row in chunks)
    assert {row["chunk_id"] for row in chunks} == {row["chunk_id"] for row in embeddings}
    assert all(len(row["vector"]) == 64 for row in embeddings)

    retrieval = run_rag_retrieve(config, isolated_project, "예산이 얼마야?")
    answer = run_rag_chat(config, isolated_project, "예산이 얼마야?")

    _assert_retrieval_payload(retrieval)
    _assert_answer_payload(answer)
    retrieved_ids = {str(row["chunk_id"]) for row in retrieval["retrieved_chunks"]}
    citation_ids = {str(row["chunk_id"]) for row in answer["citations"]}
    assert citation_ids <= retrieved_ids
    assert answer["status"] == "answered"

    assert {row["status"] for row in evaluation_rows} == {"answered"}
    assert all(row["retrieval_hit"] == "true" for row in evaluation_rows)
    assert all(row["citation_correct"] == "true" for row in evaluation_rows)
    assert not (output_dir / "failure.log").exists()


def test_rag_quality_gate_error_analysis_headers_exist(isolated_project: Path):
    config = isolated_project / "configs" / "experiments" / "rag" / "rag_langchain.yaml"
    output_dir = isolated_project / "experiments" / "rag_langchain"

    run_rag_evaluation(config, isolated_project)

    expected_header = [
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
    for filename in ["bad_retrievals.csv", "unsupported_answers.csv", "failed_questions.csv"]:
        with (output_dir / filename).open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            assert next(reader) == expected_header


def test_rag_quality_gate_realistic_docx_hwpx_e2e(isolated_project: Path):
    """준실제 DOCX/HWPX fixture가 check부터 평가까지 같은 계약으로 동작하는지 확인합니다."""
    config = isolated_project / "configs" / "experiments" / "rag" / "rag_realistic_docs.yaml"
    output_dir = isolated_project / "experiments" / "rag_realistic_docs"

    check = check_rag_pipeline(config, isolated_project)
    assert check["ok"], check
    assert check["summary"]["document_counts"] == {"docx": 1, "hwpx": 1}
    assert check["summary"]["engine"] == "langchain"

    ingest = run_rag_ingest(config, isolated_project)
    metrics = run_rag_evaluation(config, isolated_project)

    assert ingest == {"documents": 6, "chunks": 6, "embeddings": 6}
    assert metrics == {
        "retrieval_hit_rate": 1.0,
        "answer_contains_expected_rate": 1.0,
        "citation_correct_rate": 1.0,
        "not_found_rate": 0.0,
    }

    documents = _read_csv(output_dir / "parsed_documents.csv")
    chunks = _read_csv(output_dir / "chunks.csv")
    evaluation_rows = _read_csv(output_dir / "evaluation_results.csv")

    assert {Path(row["source_path"]).suffix for row in documents} == {".docx", ".hwpx"}
    assert {row["section"] for row in chunks} >= {"사업 개요", "제출 일정", "참가 자격"}
    assert {row["status"] for row in evaluation_rows} == {"answered"}
    assert all(row["retrieval_hit"] == "true" for row in evaluation_rows)
    assert all(row["answer_contains_expected"] == "true" for row in evaluation_rows)
    assert all(row["citation_correct"] == "true" for row in evaluation_rows)

    for filename in ["bad_retrievals.csv", "unsupported_answers.csv", "failed_questions.csv"]:
        assert (output_dir / filename).exists()
    assert not (output_dir / "failure.log").exists()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _assert_required_columns(rows: list[dict[str, str]], required_columns: set[str]) -> None:
    assert rows
    assert required_columns <= set(rows[0])


def _assert_retrieval_payload(payload: dict[str, Any]) -> None:
    assert {"question", "top_k", "retriever_method", "retrieved_chunks"} <= set(payload)
    assert payload["retrieved_chunks"]
    required_chunk_keys = {"rank", "score", "chunk_id", "document_id", "source_path", "page", "section", "text"}
    assert required_chunk_keys <= set(payload["retrieved_chunks"][0])


def _assert_answer_payload(payload: dict[str, Any]) -> None:
    assert {"question", "answer", "citations", "status"} <= set(payload)
    assert payload["citations"]
    required_citation_keys = {"chunk_id", "document_id", "source_path", "page", "section"}
    assert required_citation_keys <= set(payload["citations"][0])
