from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.predict import predict_one
from src.train import run_training


def test_image_smoke_training_writes_artifacts(isolated_project: Path):
    metrics = run_training(
        isolated_project / "configs" / "smoke_test.yaml",
        isolated_project,
    )
    output_dir = isolated_project / "experiments" / "smoke_test"

    assert metrics == {"valid_accuracy": 1.0, "test_accuracy": 1.0}
    assert (output_dir / "best_model.json").exists()
    assert (output_dir / "config.yaml").exists()
    assert (output_dir / "metrics.json").exists()
    assert (output_dir / "history.csv").exists()
    assert (output_dir / "run_info.json").exists()
    assert (output_dir / "README.md").exists()
    assert (output_dir / "train.log").exists()
    assert (output_dir / "run_status.json").exists()

    saved_metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))
    run_status = json.loads((output_dir / "run_status.json").read_text(encoding="utf-8"))
    assert saved_metrics["valid_accuracy"] == 1.0
    assert run_status["operation"] == "train"
    assert run_status["status"] == "success"


def test_text_smoke_training_and_prediction(isolated_project: Path):
    config = isolated_project / "configs" / "smoke_test_text.yaml"
    metrics = run_training(config, isolated_project)

    prediction = predict_one(
        config,
        isolated_project,
        "data/text_processed/sample_positive.txt",
    )

    assert metrics == {"valid_accuracy": 1.0, "test_accuracy": 1.0}
    assert prediction == "positive"
    assert (isolated_project / "experiments" / "smoke_test_text" / "best_model.json").exists()


def test_training_writes_failure_artifacts(isolated_project: Path):
    config = isolated_project / "configs" / "train_failure.yaml"
    config.write_text(
        """
experiment:
  name: train_failure
  seed: 42
paths:
  data_dir: data/missing_dataset
  output_dir: experiments/train_failure
data:
  task: text_classification
  train_csv: train.csv
  valid_csv: valid.csv
  test_csv: test.csv
model:
  name: keyword_text_classifier
""",
        encoding="utf-8",
    )

    try:
        run_training(config, isolated_project)
    except RuntimeError:
        pass
    else:
        raise AssertionError("run_training should fail when data validation fails")

    output_dir = isolated_project / "experiments" / "train_failure"
    run_status = json.loads((output_dir / "run_status.json").read_text(encoding="utf-8"))
    failure_log = (output_dir / "failure.log").read_text(encoding="utf-8")

    assert run_status["operation"] == "train"
    assert run_status["status"] == "failed"
    assert run_status["error"]["type"] == "RuntimeError"
    assert "Data validation failed" in failure_log


def test_training_accepts_configured_run_id(isolated_project: Path):
    config = isolated_project / "configs" / "smoke_test_text_run_id.yaml"
    config.write_text(
        """
experiment:
  name: smoke_test_text_run_id
  seed: 42
paths:
  data_dir: data/text_processed
  output_dir: experiments/smoke_test_text_run_id
data:
  task: text_classification
  train_csv: train.csv
  valid_csv: valid.csv
  test_csv: test.csv
model:
  name: keyword_text_classifier
artifact_policy:
  run_id: unit_run_001
  on_existing: overwrite
""",
        encoding="utf-8",
    )

    metrics = run_training(config, isolated_project)
    prediction = predict_one(config, isolated_project, "data/text_processed/sample_positive.txt")
    output_dir = isolated_project / "experiments" / "smoke_test_text_run_id" / "unit_run_001"

    assert metrics["valid_accuracy"] == 1.0
    assert prediction == "positive"
    assert (output_dir / "best_model.json").exists()
    assert (output_dir / "run_status.json").exists()


def test_training_can_reject_existing_output_dir(isolated_project: Path):
    config = isolated_project / "configs" / "smoke_test_text_fail_existing.yaml"
    config.write_text(
        """
experiment:
  name: smoke_test_text_fail_existing
  seed: 42
paths:
  data_dir: data/text_processed
  output_dir: experiments/smoke_test_text_fail_existing
data:
  task: text_classification
  train_csv: train.csv
  valid_csv: valid.csv
  test_csv: test.csv
model:
  name: keyword_text_classifier
artifact_policy:
  on_existing: fail
""",
        encoding="utf-8",
    )
    output_dir = isolated_project / "experiments" / "smoke_test_text_fail_existing"
    output_dir.mkdir(parents=True)
    (output_dir / "existing.txt").write_text("keep me", encoding="utf-8")

    with pytest.raises(FileExistsError):
        run_training(config, isolated_project)
