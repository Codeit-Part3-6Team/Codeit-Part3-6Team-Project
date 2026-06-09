from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src.rag.pipeline import run_rag_chat, run_rag_evaluation, run_rag_ingest, run_rag_retrieve


def test_rag_smoke_pipeline_writes_artifacts(isolated_project: Path):
    config = isolated_project / "configs" / "rag_smoke_test.yaml"

    ingest_summary = run_rag_ingest(config, isolated_project)
    retrieval = run_rag_retrieve(config, isolated_project, "예산이 얼마야?")
    answer = run_rag_chat(config, isolated_project, "예산이 얼마야?")
    metrics = run_rag_evaluation(config, isolated_project)

    output_dir = isolated_project / "experiments" / "rag_smoke_test"
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

    saved_metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))
    assert saved_metrics["answer_contains_expected_rate"] == 1.0
    assert "question,expected_answer" in (output_dir / "bad_retrievals.csv").read_text(encoding="utf-8")


def test_run_rag_chat_script_supports_evaluation(isolated_project: Path, repo_root: Path):
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "run_rag_chat.py"),
            "--project-root",
            str(isolated_project),
            "--config",
            str(isolated_project / "configs" / "rag_smoke_test.yaml"),
            "--evaluate",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "'retrieval_hit_rate': 1.0" in result.stdout
