from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from src.artifacts import maybe_backup
from src.experiments import collect_experiment_summaries, write_experiment_summary
from src.rag.pipeline import run_rag_evaluation
from src.train import run_training


def test_write_experiment_summary_collects_metrics(isolated_project: Path):
    run_training(isolated_project / "configs" / "smoke_test_text.yaml", isolated_project)

    rows = write_experiment_summary(isolated_project)
    summary_csv = isolated_project / "reports" / "experiment_summary.csv"
    summary_json = isolated_project / "reports" / "experiment_summary.json"

    assert len(rows) == 1
    assert rows[0]["experiment"] == "smoke_test_text"
    assert rows[0]["model"] == "keyword_text_classifier"
    assert rows[0]["valid_accuracy"] == 1.0
    assert rows[0]["test_accuracy"] == 1.0
    assert summary_csv.exists()
    assert summary_json.exists()

    with summary_csv.open("r", encoding="utf-8", newline="") as f:
        saved_rows = list(csv.DictReader(f))
    assert saved_rows[0]["experiment"] == "smoke_test_text"
    assert saved_rows[0]["status"] == "ok"

    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    assert payload["experiments"][0]["experiment"] == "smoke_test_text"


def test_collect_experiment_summaries_handles_empty_experiments_dir(isolated_project: Path):
    rows = collect_experiment_summaries(isolated_project)

    assert rows == []


def test_write_experiment_summary_accepts_absolute_paths(isolated_project: Path):
    run_training(isolated_project / "configs" / "smoke_test_text.yaml", isolated_project)
    output_path = isolated_project / "reports" / "absolute_summary.csv"

    rows = write_experiment_summary(
        isolated_project,
        output_path=output_path,
        experiments_dir=isolated_project / "experiments",
    )

    assert len(rows) == 1
    assert output_path.exists()
    assert output_path.with_suffix(".json").exists()


def test_write_experiment_summary_collects_nested_run_id(isolated_project: Path):
    config = isolated_project / "configs" / "summary_run_id.yaml"
    config.write_text(
        """
experiment:
  name: summary_run_id
  seed: 42
paths:
  data_dir: data/text_processed
  output_dir: experiments/summary_run_id
data:
  task: text_classification
  train_csv: train.csv
  valid_csv: valid.csv
  test_csv: test.csv
model:
  name: keyword_text_classifier
artifact_policy:
  run_id: run_a
""",
        encoding="utf-8",
    )
    run_training(config, isolated_project)

    rows = write_experiment_summary(isolated_project)

    assert any(row["result_path"] == "experiments/summary_run_id/run_a" for row in rows)


def test_write_experiment_summary_collects_rag_metrics(isolated_project: Path):
    run_rag_evaluation(isolated_project / "configs" / "rag_smoke_test.yaml", isolated_project)

    rows = write_experiment_summary(isolated_project)

    assert rows[0]["experiment"] == "rag_smoke_test"
    assert rows[0]["retrieval_hit_rate"] == 1.0
    assert rows[0]["citation_correct_rate"] == 1.0


def test_summarize_experiments_script_writes_report(isolated_project: Path, repo_root: Path):
    run_training(isolated_project / "configs" / "smoke_test_text.yaml", isolated_project)

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "summarize_experiments.py"),
            "--project-root",
            str(isolated_project),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "wrote reports/experiment_summary.csv (1 experiments)" in result.stdout
    assert (isolated_project / "reports" / "experiment_summary.csv").exists()


def test_maybe_backup_copies_files_and_model_directories(tmp_path: Path):
    output_dir = tmp_path / "experiments" / "unit"
    model_dir = output_dir / "hf_model"
    model_dir.mkdir(parents=True)
    (output_dir / "metrics.json").write_text("{}", encoding="utf-8")
    (model_dir / "config.json").write_text("{}", encoding="utf-8")

    maybe_backup(output_dir, tmp_path / "drive_backup" / "unit")

    assert (tmp_path / "drive_backup" / "unit" / "metrics.json").exists()
    assert (tmp_path / "drive_backup" / "unit" / "hf_model" / "config.json").exists()
