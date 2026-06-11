from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from src.rag.validation import check_rag_pipeline


def test_check_rag_pipeline_accepts_smoke_config(isolated_project: Path):
    result = check_rag_pipeline("configs/experiments/rag/rag_smoke_test.yaml", isolated_project)

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["summary"]["experiment"] == "rag_smoke_test"
    assert result["summary"]["document_counts"]["txt"] == 1
    assert result["summary"]["retriever_method"] == "semantic"
    assert result["summary"]["embedding_provider"] == "local"
    assert result["summary"]["vector_store_type"] == "memory"
    assert result["summary"]["reranker_enabled"] is False
    assert result["summary"]["answerer_mode"] == "extractive"
    assert result["summary"]["checkpoint_enabled"] is True
    assert result["summary"]["checkpoint_resume"] is True


def test_check_rag_pipeline_reports_bad_config_values(isolated_project: Path):
    config_path = isolated_project / "configs" / "bad_rag.yaml"
    config_path.write_text(
        """
experiment:
  name: bad_rag
paths:
  raw_docs_dir: data/rag_smoke
  output_dir: experiments/bad_rag
rag:
  loader:
    file_types: [pptx]
  chunk:
    size: 10
    overlap: 10
  checkpoint:
    enabled: maybe
    resume: maybe
  retriever:
    method: unknown
    top_k: 0
    score_threshold: -1
  embedding:
    provider: unknown
    dimension: 0
    device: tpu
  vector_store:
    type: faiss
  reranker:
    enabled: true
    provider: huggingface
    top_k: 0
  answerer:
    mode: llm
    provider: local
artifact_policy:
  on_existing: invalid
evaluation:
  questions_path: data/rag_smoke/missing.csv
""",
        encoding="utf-8",
    )

    result = check_rag_pipeline(config_path, isolated_project)

    assert result["ok"] is False
    assert any("unsupported file types" in error for error in result["errors"])
    assert any("overlap must be smaller" in error for error in result["errors"])
    assert any("checkpoint.enabled must be a boolean" in error for error in result["errors"])
    assert any("checkpoint.resume must be a boolean" in error for error in result["errors"])
    assert any("unsupported retriever method" in error for error in result["errors"])
    assert any("top_k must be positive" in error for error in result["errors"])
    assert any("score_threshold must be zero or positive" in error for error in result["errors"])
    assert any("unsupported embedding provider" in error for error in result["errors"])
    assert any("embedding.dimension must be positive" in error for error in result["errors"])
    assert any("unsupported embedding device" in error for error in result["errors"])
    assert any("vector_store.path is required" in error for error in result["errors"])
    assert any("reranker.top_k must be positive" in error for error in result["errors"])
    assert any("reranker.model_name is required" in error for error in result["errors"])
    assert any("answerer.provider must be openai, huggingface, or ollama" in error for error in result["errors"])
    assert any("unsupported artifact_policy.on_existing" in error for error in result["errors"])
    assert any("evaluation questions not found" in error for error in result["errors"])


def test_check_rag_pipeline_validates_llm_answerer_contract(isolated_project: Path):
    config_path = isolated_project / "configs" / "bad_llm_answerer.yaml"
    config_path.write_text(
        """
experiment:
  name: bad_llm_answerer
paths:
  raw_docs_dir: data/rag_smoke
  output_dir: experiments/bad_llm_answerer
rag:
  loader:
    file_types: [txt]
  chunk:
    size: 500
    overlap: 80
  embedding:
    provider: huggingface
    model_name:
    dimension: 384
  vector_store:
    type: elasticsearch
    collection_name:
  retriever:
    method: hybrid
    top_k: 3
  answerer:
    mode: llm
    provider: openai
evaluation:
  questions_path: data/rag_smoke/eval_questions.csv
""",
        encoding="utf-8",
    )

    result = check_rag_pipeline(config_path, isolated_project)

    assert result["ok"] is False
    assert any("embedding.model_name is required" in error for error in result["errors"])
    assert any("vector_store.url is required" in error for error in result["errors"])
    assert any("vector_store.index_name is required" in error for error in result["errors"])
    assert any("answerer.model_name is required" in error for error in result["errors"])


def test_check_rag_pipeline_accepts_contract_only_llm_answerer(isolated_project: Path):
    config_path = isolated_project / "configs" / "llm_answerer_contract.yaml"
    config_path.write_text(
        """
experiment:
  name: llm_answerer_contract
paths:
  raw_docs_dir: data/rag_smoke
  output_dir: experiments/llm_answerer_contract
rag:
  loader:
    file_types: [txt]
  chunk:
    size: 500
    overlap: 80
  embedding:
    provider: local
    dimension: 64
  vector_store:
    type: memory
  retriever:
    method: semantic
    top_k: 3
  answerer:
    mode: llm
    provider: openai
    model_name: gpt-4o-mini
    temperature: 0.2
    max_tokens: 512
    api_key_env: OPENAI_API_KEY
    require_citations: true
evaluation:
  questions_path: data/rag_smoke/eval_questions.csv
""",
        encoding="utf-8",
    )

    result = check_rag_pipeline(config_path, isolated_project)

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["summary"]["answerer_mode"] == "llm"
    assert result["summary"]["answerer_provider"] == "openai"
    assert result["summary"]["answerer_model"] == "gpt-4o-mini"
    assert any("answerer provider 'openai' is config-ready" in warning for warning in result["warnings"])


def test_check_rag_pipeline_validates_ollama_answerer_contract(isolated_project: Path):
    config_path = isolated_project / "configs" / "bad_ollama_answerer.yaml"
    config_path.write_text(
        """
experiment:
  name: bad_ollama_answerer
paths:
  raw_docs_dir: data/rag_smoke
  output_dir: experiments/bad_ollama_answerer
rag:
  loader:
    file_types: [txt]
  chunk:
    size: 500
    overlap: 80
  embedding:
    provider: local
  vector_store:
    type: memory
  retriever:
    method: semantic
  answerer:
    mode: llm
    provider: ollama
    model_name: llama3.1
    base_url:
    temperature: -0.1
    max_tokens: 0
    require_citations: required
evaluation:
  questions_path: data/rag_smoke/eval_questions.csv
""",
        encoding="utf-8",
    )

    result = check_rag_pipeline(config_path, isolated_project)

    assert result["ok"] is False
    assert any("answerer.temperature must be zero or positive" in error for error in result["errors"])
    assert any("answerer.max_tokens must be positive" in error for error in result["errors"])
    assert any("answerer.require_citations must be a boolean" in error for error in result["errors"])
    assert any("answerer.base_url must not be empty" in error for error in result["errors"])


def test_check_rag_pipeline_script_uses_exit_code(isolated_project: Path, repo_root: Path):
    ok_result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "check_rag_pipeline.py"),
            "--project-root",
            str(isolated_project),
            "--config",
            "configs/experiments/rag/rag_smoke_test.yaml",
        ],
        capture_output=True,
        text=True,
    )

    bad_result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "check_rag_pipeline.py"),
            "--project-root",
            str(isolated_project),
            "--config",
            "configs/missing.yaml",
        ],
        capture_output=True,
        text=True,
    )

    assert ok_result.returncode == 0
    assert "'ok': True" in ok_result.stdout
    assert bad_result.returncode == 1
    assert "config file not found" in bad_result.stdout
