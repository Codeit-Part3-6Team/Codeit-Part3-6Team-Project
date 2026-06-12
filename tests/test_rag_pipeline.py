from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src.rag.comparison import compare_rag_retrievers
from src.rag.pipeline import run_rag_chat, run_rag_evaluation, run_rag_ingest, run_rag_retrieve


def test_rag_config_pipeline_writes_artifacts(isolated_project: Path):
    config = isolated_project / "configs" / "experiments" / "rag" / "rag_semantic.yaml"

    ingest_summary = run_rag_ingest(config, isolated_project)
    retrieval = run_rag_retrieve(config, isolated_project, "예산이 얼마야?")
    answer = run_rag_chat(config, isolated_project, "예산이 얼마야?")
    metrics = run_rag_evaluation(config, isolated_project)

    output_dir = isolated_project / "experiments" / "rag_semantic"
    assert ingest_summary == {"documents": 3, "chunks": 3, "embeddings": 3}
    assert retrieval["retriever_method"] == "semantic"
    assert retrieval["retrieved_chunks"][0]["chunk_id"] == "rfp_sample_chunk_0001"
    assert answer["status"] == "answered"
    assert "5천만 원" in answer["answer"]
    assert answer["citations"][0]["chunk_id"] == "rfp_sample_chunk_0001"
    assert metrics["retrieval_hit_rate"] == 1.0
    assert metrics["citation_correct_rate"] == 1.0
    assert (output_dir / "parsed_documents.csv").exists()
    assert (output_dir / "chunks.csv").exists()
    assert (output_dir / "embeddings.jsonl").exists()
    assert (output_dir / "evaluation_results.csv").exists()
    assert (output_dir / "bad_retrievals.csv").exists()
    assert (output_dir / "unsupported_answers.csv").exists()
    assert (output_dir / "failed_questions.csv").exists()
    assert (output_dir / "metrics.json").exists()
    assert (output_dir / "run_status.json").exists()
    assert (output_dir / "rag_ingest_checkpoint.json").exists()

    saved_metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))
    run_status = json.loads((output_dir / "run_status.json").read_text(encoding="utf-8"))
    ingest_checkpoint = json.loads((output_dir / "rag_ingest_checkpoint.json").read_text(encoding="utf-8"))
    assert saved_metrics["answer_contains_expected_rate"] == 1.0
    assert run_status["operation"] == "rag_evaluation"
    assert run_status["status"] == "success"
    assert ingest_checkpoint["stage"] == "embeddings"
    assert ingest_checkpoint["counts"] == {"documents": 3, "chunks": 3, "embeddings": 3}
    assert "question,expected_answer" in (output_dir / "bad_retrievals.csv").read_text(encoding="utf-8")


def test_rag_ingest_resumes_from_existing_document_and_chunk_artifacts(isolated_project: Path):
    config = isolated_project / "configs" / "experiments" / "rag" / "rag_semantic.yaml"
    output_dir = isolated_project / "experiments" / "rag_semantic"

    first_summary = run_rag_ingest(config, isolated_project)
    (output_dir / "embeddings.jsonl").unlink()
    second_summary = run_rag_ingest(config, isolated_project)

    checkpoint = json.loads((output_dir / "rag_ingest_checkpoint.json").read_text(encoding="utf-8"))
    assert first_summary == second_summary
    assert (output_dir / "parsed_documents.csv").exists()
    assert (output_dir / "chunks.csv").exists()
    assert (output_dir / "embeddings.jsonl").exists()
    assert checkpoint["stage"] == "embeddings"


def test_rag_evaluation_accepts_utf8_bom_questions_csv(isolated_project: Path):
    questions_path = isolated_project / "data" / "rag_sample" / "eval_questions.csv"
    original = questions_path.read_text(encoding="utf-8")
    questions_path.write_text(original, encoding="utf-8-sig")

    config = isolated_project / "configs" / "experiments" / "rag" / "rag_semantic.yaml"
    run_rag_ingest(config, isolated_project)
    metrics = run_rag_evaluation(config, isolated_project)

    assert metrics["retrieval_hit_rate"] == 1.0
    assert metrics["answer_contains_expected_rate"] == 1.0


def test_run_rag_chat_script_supports_evaluation(isolated_project: Path, repo_root: Path):
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "run_rag_chat.py"),
            "--project-root",
            str(isolated_project),
            "--config",
            str(isolated_project / "configs" / "experiments" / "rag" / "rag_semantic.yaml"),
            "--evaluate",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "'retrieval_hit_rate': 1.0" in result.stdout


def test_run_rag_chat_script_resolves_config_from_project_root(
    isolated_project: Path,
    repo_root: Path,
    tmp_path: Path,
):
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "run_rag_chat.py"),
            "--project-root",
            str(isolated_project),
            "--config",
            "configs/experiments/rag/rag_semantic.yaml",
            "--evaluate",
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )

    assert "'retrieval_hit_rate': 1.0" in result.stdout


def test_compare_rag_retrievers_writes_report(isolated_project: Path, repo_root: Path):
    rows = compare_rag_retrievers(
        [
            isolated_project / "configs" / "experiments" / "rag" / "rag_keyword.yaml",
            isolated_project / "configs" / "experiments" / "rag" / "rag_semantic.yaml",
            isolated_project / "configs" / "experiments" / "rag" / "rag_hybrid.yaml",
        ],
        isolated_project,
    )

    assert [row["retriever_method"] for row in rows] == ["keyword", "semantic", "hybrid"]
    assert [row["engine"] for row in rows] == ["local", "local", "local"]
    assert rows[0]["retrieval_hit_rate"] == 1.0
    assert (isolated_project / "reports" / "rag_retriever_comparison.csv").exists()

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "compare_rag_retrievers.py"),
            "--project-root",
            str(isolated_project),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "wrote reports/rag_retriever_comparison.csv (4 retrievers)" in result.stdout
    assert "rag_langchain,langchain,similarity,local,local" in result.stdout


def test_rag_langchain_default_config_runs_pipeline(isolated_project: Path):
    config = isolated_project / "configs" / "experiments" / "rag" / "rag_langchain.yaml"

    metrics = run_rag_evaluation(config, isolated_project)

    assert metrics["retrieval_hit_rate"] == 1.0
    assert metrics["citation_correct_rate"] == 1.0
    assert (isolated_project / "experiments" / "rag_langchain" / "metrics.json").exists()


def test_rag_hybrid_retriever_config_runs_pipeline(isolated_project: Path):
    config = isolated_project / "configs" / "experiments" / "rag" / "rag_hybrid.yaml"

    metrics = run_rag_evaluation(config, isolated_project)

    assert metrics["retrieval_hit_rate"] == 1.0
    assert (isolated_project / "experiments" / "rag_hybrid" / "metrics.json").exists()


def test_rag_evaluation_writes_failure_artifacts(isolated_project: Path):
    config_path = isolated_project / "configs" / "rag_failure.yaml"
    config_path.write_text(
        """
experiment:
  name: rag_failure
paths:
  raw_docs_dir: data/rag_sample
  output_dir: experiments/rag_failure
rag:
  loader:
    file_types: [txt]
  chunk:
    size: 500
    overlap: 80
  retriever:
    method: semantic
    top_k: 3
  answerer:
    mode: extractive
evaluation:
  questions_path: data/rag_sample/missing_questions.csv
""",
        encoding="utf-8",
    )

    try:
        run_rag_evaluation(config_path, isolated_project)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("run_rag_evaluation should fail for missing questions file")

    output_dir = isolated_project / "experiments" / "rag_failure"
    run_status = json.loads((output_dir / "run_status.json").read_text(encoding="utf-8"))
    failure_log = (output_dir / "failure.log").read_text(encoding="utf-8")

    assert run_status["operation"] == "rag_evaluation"
    assert run_status["status"] == "failed"
    assert run_status["error"]["type"] == "FileNotFoundError"
    assert "missing_questions.csv" in failure_log
