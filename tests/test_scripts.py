from __future__ import annotations

import json
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
            "data/examples/classification/text_processed",
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
    config = isolated_project / "configs" / "examples" / "classification" / "smoke_test_text.yaml"

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
            "data/examples/classification/text_processed/sample_positive.txt",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    output_dir = isolated_project / "experiments" / "smoke_test_text"
    assert "'prediction': 'positive'" in result.stdout
    assert (output_dir / "predictions.csv").exists()
    assert (output_dir / "README.md").exists()
    assert (output_dir / "run_status.json").exists()
    run_status = json.loads((output_dir / "run_status.json").read_text(encoding="utf-8"))
    assert run_status["operation"] == "predict"
    assert run_status["status"] == "success"


def test_run_train_script_resolves_config_from_project_root(
    isolated_project: Path,
    repo_root: Path,
    tmp_path: Path,
):
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "run_train.py"),
            "--project-root",
            str(isolated_project),
            "--config",
            "configs/examples/classification/smoke_test_text.yaml",
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )

    assert "'valid_accuracy': 1.0" in result.stdout
    assert (isolated_project / "experiments" / "smoke_test_text" / "run_status.json").exists()


def test_run_predict_script_resolves_config_from_project_root(
    isolated_project: Path,
    repo_root: Path,
    tmp_path: Path,
):
    subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "run_train.py"),
            "--project-root",
            str(isolated_project),
            "--config",
            "configs/examples/classification/smoke_test_text.yaml",
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "run_predict.py"),
            "--project-root",
            str(isolated_project),
            "--config",
            "configs/examples/classification/smoke_test_text.yaml",
            "--input",
            "data/examples/classification/text_processed/sample_positive.txt",
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )

    assert "'prediction': 'positive'" in result.stdout


def test_run_predict_script_writes_failure_artifacts(isolated_project: Path, repo_root: Path):
    config = isolated_project / "configs" / "examples" / "classification" / "smoke_test_text.yaml"
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

    model_path = isolated_project / "experiments" / "smoke_test_text" / "best_model.json"
    model_path.write_text('{"model_type": "unknown"}', encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "run_predict.py"),
            "--project-root",
            str(isolated_project),
            "--config",
            str(config),
            "--input",
            "data/examples/classification/text_processed/sample_positive.txt",
        ],
        capture_output=True,
        text=True,
    )

    output_dir = isolated_project / "experiments" / "smoke_test_text"
    run_status = json.loads((output_dir / "run_status.json").read_text(encoding="utf-8"))
    failure_log = (output_dir / "failure.log").read_text(encoding="utf-8")

    assert result.returncode != 0
    assert run_status["operation"] == "predict"
    assert run_status["status"] == "failed"
    assert run_status["error"]["type"] == "ValueError"
    assert "Unsupported model artifact" in failure_log
