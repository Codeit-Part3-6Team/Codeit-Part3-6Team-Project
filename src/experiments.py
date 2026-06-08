from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from src.config import load_config, write_json
from src.data import read_json
from src.utils.paths import ensure_dir


SUMMARY_COLUMNS = [
    "experiment",
    "model",
    "base_model",
    "task",
    "data_dir",
    "seed",
    "contract_version",
    "valid_accuracy",
    "test_accuracy",
    "result_path",
    "config_path",
    "status",
]


def collect_experiment_summaries(
    project_root: str | Path,
    experiments_dir: str | Path = "experiments",
) -> list[dict[str, Any]]:
    """Collect one summary row per experiment directory."""
    root = Path(project_root)
    base_dir = _resolve_path(root, experiments_dir)
    if not base_dir.exists():
        return []

    rows: list[dict[str, Any]] = []
    for experiment_dir in sorted(path for path in base_dir.iterdir() if path.is_dir()):
        if experiment_dir.name.startswith("."):
            continue
        rows.append(_summarize_experiment(root, experiment_dir))
    return rows


def write_experiment_summary(
    project_root: str | Path,
    output_path: str | Path = "reports/experiment_summary.csv",
    experiments_dir: str | Path = "experiments",
) -> list[dict[str, Any]]:
    """Write experiment comparison reports as CSV and JSON."""
    root = Path(project_root)
    rows = collect_experiment_summaries(root, experiments_dir)
    target = _resolve_path(root, output_path)
    ensure_dir(target.parent)
    with target.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(_normalize_row(row) for row in rows)
    write_json(target.with_suffix(".json"), {"experiments": rows})
    return rows


def _summarize_experiment(project_root: Path, experiment_dir: Path) -> dict[str, Any]:
    """Build a summary row from config, metrics, and run metadata."""
    config_path = experiment_dir / "config.yaml"
    metrics_path = experiment_dir / "metrics.json"
    run_info_path = experiment_dir / "run_info.json"

    config = load_config(config_path) if config_path.exists() else {}
    metrics = read_json(metrics_path) if metrics_path.exists() else {}
    run_info = read_json(run_info_path) if run_info_path.exists() else {}

    experiment = config.get("experiment", run_info.get("experiment", {}))
    model = config.get("model", {})
    data = config.get("data", {})
    paths = config.get("paths", {})
    status = "ok" if metrics_path.exists() else "missing_metrics"

    return {
        "experiment": experiment.get("name", experiment_dir.name),
        "model": model.get("name", ""),
        "base_model": model.get("model_name") or model.get("hf_model_name") or "",
        "task": data.get("task", ""),
        "data_dir": paths.get("data_dir", ""),
        "seed": experiment.get("seed", ""),
        "contract_version": experiment.get("contract_version", ""),
        "valid_accuracy": metrics.get("valid_accuracy", ""),
        "test_accuracy": metrics.get("test_accuracy", ""),
        "result_path": _relative_path(project_root, experiment_dir),
        "config_path": _relative_path(project_root, config_path) if config_path.exists() else "",
        "status": status,
    }


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Keep CSV output stable even when future summary rows add fields."""
    return {column: row.get(column, "") for column in SUMMARY_COLUMNS}


def _relative_path(root: Path, path: Path) -> str:
    """Prefer project-relative paths in human-facing reports."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _resolve_path(root: Path, path: str | Path) -> Path:
    """Resolve paths for both local runs and absolute Colab/Drive paths."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate
