from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from src.rag.validation import check_rag_pipeline


def test_check_rag_pipeline_accepts_smoke_config(isolated_project: Path):
    result = check_rag_pipeline("configs/rag_smoke_test.yaml", isolated_project)

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["summary"]["experiment"] == "rag_smoke_test"
    assert result["summary"]["document_counts"]["txt"] == 1
    assert result["summary"]["retriever_method"] == "semantic"


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
  retriever:
    method: unknown
    top_k: 0
  answerer:
    mode: generative
evaluation:
  questions_path: data/rag_smoke/missing.csv
""",
        encoding="utf-8",
    )

    result = check_rag_pipeline(config_path, isolated_project)

    assert result["ok"] is False
    assert any("unsupported file types" in error for error in result["errors"])
    assert any("overlap must be smaller" in error for error in result["errors"])
    assert any("unsupported retriever method" in error for error in result["errors"])
    assert any("top_k must be positive" in error for error in result["errors"])
    assert any("unsupported answerer mode" in error for error in result["errors"])
    assert any("evaluation questions not found" in error for error in result["errors"])


def test_check_rag_pipeline_script_uses_exit_code(isolated_project: Path, repo_root: Path):
    ok_result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "check_rag_pipeline.py"),
            "--project-root",
            str(isolated_project),
            "--config",
            "configs/rag_smoke_test.yaml",
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
