from __future__ import annotations

import json
from pathlib import Path

from src.predict import predict_one
from src.train import run_training


def test_image_smoke_training_writes_artifacts(isolated_project: Path):
    metrics = run_training(
        isolated_project / "configs" / "smoke_test.yaml",
        isolated_project,
    )
    output_dir = isolated_project / "outputs" / "smoke_test"

    assert metrics == {"valid_accuracy": 1.0, "test_accuracy": 1.0}
    assert (output_dir / "best_model.json").exists()
    assert (output_dir / "metrics.json").exists()
    assert (output_dir / "history.csv").exists()
    assert (output_dir / "run_info.json").exists()
    assert (output_dir / "train.log").exists()

    saved_metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))
    assert saved_metrics["valid_accuracy"] == 1.0


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
    assert (isolated_project / "outputs" / "smoke_test_text" / "best_model.json").exists()

