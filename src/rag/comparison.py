from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from src.artifacts import resolve_experiment_dir
from src.config import load_config, write_json
from src.rag.pipeline import run_rag_evaluation
from src.utils.paths import ensure_dir


COMPARISON_COLUMNS = [
    "experiment",
    "retriever_method",
    "retrieval_hit_rate",
    "answer_contains_expected_rate",
    "citation_correct_rate",
    "not_found_rate",
    "result_path",
    "config_path",
]


def compare_rag_retrievers(
    config_paths: list[str | Path],
    project_root: str | Path = ".",
    output_path: str | Path = "reports/rag_retriever_comparison.csv",
) -> list[dict[str, Any]]:
    """여러 RAG config를 같은 평가 질문으로 실행하고 비교 리포트를 저장합니다."""
    root = Path(project_root)
    rows: list[dict[str, Any]] = []
    for config_path in config_paths:
        resolved_config_path = _resolve_path(root, config_path)
        config = load_config(resolved_config_path)
        metrics = run_rag_evaluation(resolved_config_path, root)
        output_dir = resolve_experiment_dir(root, config)
        experiment = config.get("experiment", {})
        retriever = config.get("rag", {}).get("retriever", {})
        rows.append(
            {
                "experiment": experiment.get("name", output_dir.name),
                "retriever_method": retriever.get("method", "keyword"),
                "retrieval_hit_rate": metrics.get("retrieval_hit_rate", ""),
                "answer_contains_expected_rate": metrics.get("answer_contains_expected_rate", ""),
                "citation_correct_rate": metrics.get("citation_correct_rate", ""),
                "not_found_rate": metrics.get("not_found_rate", ""),
                "result_path": _relative_path(root, output_dir),
                "config_path": _relative_path(root, resolved_config_path),
            }
        )

    target = _resolve_path(root, output_path)
    ensure_dir(target.parent)
    _write_csv(target, rows)
    write_json(target.with_suffix(".json"), {"retrievers": rows})
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COMPARISON_COLUMNS)
        writer.writeheader()
        writer.writerows({column: row.get(column, "") for column in COMPARISON_COLUMNS} for row in rows)


def _resolve_path(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
