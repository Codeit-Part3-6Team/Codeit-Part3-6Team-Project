from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_run_validate_script_accepts_project_root(isolated_project: Path, repo_root: Path):
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "run_validate.py"),
            "--project-root",
            str(isolated_project),
            "--data-dir",
            "data/text_processed",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "'ok': True" in result.stdout


def test_run_train_and_predict_scripts_write_experiment_artifacts(
    isolated_project: Path,
    repo_root: Path,
):
    config = isolated_project / "configs" / "smoke_test_text.yaml"

    subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "run_train.py"),
            "--project-root",
            str(isolated_project),
            "--config",
            str(config),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "run_predict.py"),
            "--project-root",
            str(isolated_project),
            "--config",
            str(config),
            "--input",
            "data/text_processed/sample_positive.txt",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    output_dir = isolated_project / "experiments" / "smoke_test_text"
    assert "'prediction': 'positive'" in result.stdout
    assert (output_dir / "predictions.csv").exists()
    assert (output_dir / "README.md").exists()
