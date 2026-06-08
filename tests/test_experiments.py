from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from src.experiments import collect_experiment_summaries, write_experiment_summary
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
