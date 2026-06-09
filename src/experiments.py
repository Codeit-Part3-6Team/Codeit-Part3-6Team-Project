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
    "retrieval_hit_rate",
    "answer_contains_expected_rate",
    "citation_correct_rate",
    "not_found_rate",
    "result_path",
    "config_path",
    "status",
]


def collect_experiment_summaries(
    project_root: str | Path,
    experiments_dir: str | Path = "experiments",
) -> list[dict[str, Any]]:
    """실험 폴더마다 비교용 summary row를 하나씩 수집합니다."""
    root = Path(project_root)
    base_dir = _resolve_path(root, experiments_dir)
    if not base_dir.exists():
        return []

    rows: list[dict[str, Any]] = []
    for experiment_dir in _iter_experiment_dirs(base_dir):
        rows.append(_summarize_experiment(root, experiment_dir))
    return rows


def write_experiment_summary(
    project_root: str | Path,
    output_path: str | Path = "reports/experiment_summary.csv",
    experiments_dir: str | Path = "experiments",
) -> list[dict[str, Any]]:
    """실험 비교 리포트를 CSV와 JSON으로 저장합니다."""
    root = Path(project_root)
    rows = collect_experiment_summaries(root, experiments_dir)
    target = _resolve_path(root, output_path)
    ensure_dir(target.parent)
    # CSV는 사람이 표로 보기 좋고, JSON은 나중에 대시보드/자동화에서 재사용하기 좋습니다.
    with target.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(_normalize_row(row) for row in rows)
    write_json(target.with_suffix(".json"), {"experiments": rows})
    return rows


def _summarize_experiment(project_root: Path, experiment_dir: Path) -> dict[str, Any]:
    """config, metrics, run metadata를 모아 summary row를 만듭니다."""
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
    # metrics.json이 없으면 실패/미완료 실험일 가능성이 높으므로 상태를 따로 표시합니다.
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
        "retrieval_hit_rate": metrics.get("retrieval_hit_rate", ""),
        "answer_contains_expected_rate": metrics.get("answer_contains_expected_rate", ""),
        "citation_correct_rate": metrics.get("citation_correct_rate", ""),
        "not_found_rate": metrics.get("not_found_rate", ""),
        "result_path": _relative_path(project_root, experiment_dir),
        "config_path": _relative_path(project_root, config_path) if config_path.exists() else "",
        "status": status,
    }


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    """나중에 field가 추가되어도 CSV column 순서를 안정적으로 유지합니다."""
    return {column: row.get(column, "") for column in SUMMARY_COLUMNS}


def _iter_experiment_dirs(base_dir: Path) -> list[Path]:
    """config/metrics/status 산출물이 있는 폴더를 실험 단위로 봅니다."""
    experiment_dirs: list[Path] = []
    for path in sorted(item for item in base_dir.rglob("*") if item.is_dir()):
        if any(part.startswith(".") for part in path.relative_to(base_dir).parts):
            continue
        if _looks_like_experiment_dir(path):
            experiment_dirs.append(path)
    return experiment_dirs


def _looks_like_experiment_dir(path: Path) -> bool:
    return any((path / filename).exists() for filename in ["config.yaml", "metrics.json", "run_status.json"])


def _relative_path(root: Path, path: Path) -> str:
    """사람이 읽는 리포트에는 가능한 project-relative path를 사용합니다."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _resolve_path(root: Path, path: str | Path) -> Path:
    """로컬 상대경로와 Colab/Drive 절대경로를 모두 처리합니다."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate
