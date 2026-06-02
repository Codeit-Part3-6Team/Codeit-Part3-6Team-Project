from __future__ import annotations

import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.artifacts import (
    maybe_backup,
    resolve_experiment_dir,
    write_experiment_readme,
    write_history,
    write_run_info,
)
from src.config import load_config, write_config_copy, write_json
from src.data import load_dataset, read_ppm_mean_rgb
from src.metrics import accuracy
from src.models import build_model
from src.utils.logger import setup_logger
from src.utils.paths import ensure_dir
from src.utils.seed import set_seed
from src.validate_data import validate_data


def _features(rows: list[dict[str, str]], task: str) -> list[tuple[float, float, float]] | list[str]:
    if task == "image_classification":
        return [read_ppm_mean_rgb(row["absolute_image_path"]) for row in rows]
    if task == "text_classification":
        return [row["text"] for row in rows]
    raise ValueError(f"Unsupported task: {task}")


def run_training(config_path: str | Path, project_root: str | Path) -> dict[str, float]:
    root = Path(project_root)
    config = load_config(config_path)
    data_dir = root / config["paths"]["data_dir"]
    output_dir = resolve_experiment_dir(root, config)
    ensure_dir(output_dir)
    logger = setup_logger("train", output_dir / "train.log")
    set_seed(config.get("experiment", {}).get("seed"))

    logger.info("Start training: %s", config.get("experiment", {}).get("name"))

    validation = validate_data(data_dir)
    if not validation["ok"]:
        raise RuntimeError(f"Data validation failed: {validation['errors']}")
    logger.info("Data validation passed")

    train_rows = load_dataset(data_dir, config["data"]["train_csv"])
    valid_rows = load_dataset(data_dir, config["data"]["valid_csv"])
    test_rows = load_dataset(data_dir, config["data"]["test_csv"])
    task = config["data"]["task"]

    model = build_model(config["model"]["name"])
    logger.info("Model built: %s", config["model"]["name"])
    train_features = _features(train_rows, task)
    train_labels = [row["label"] for row in train_rows]
    model.fit(list(zip(train_features, train_labels)))

    valid_pred = model.predict(_features(valid_rows, task))
    valid_true = [row["label"] for row in valid_rows]
    test_pred = model.predict(_features(test_rows, task))
    test_true = [row["label"] for row in test_rows]

    metrics = {
        "valid_accuracy": accuracy(valid_true, valid_pred),
        "test_accuracy": accuracy(test_true, test_pred),
    }
    history = [{"epoch": 1, **metrics}]

    command = f"python scripts/run_train.py --config {Path(config_path).as_posix()} --project-root {root.as_posix()}"
    write_config_copy(config_path, output_dir)
    write_json(output_dir / "best_model.json", model.to_dict())
    write_json(output_dir / "metrics.json", metrics)
    write_history(output_dir / "history.csv", history)
    write_run_info(output_dir, config)
    write_experiment_readme(output_dir, config, metrics, command)
    logger.info("Artifacts saved to %s", output_dir)

    backup_cfg = config.get("backup", {})
    if backup_cfg.get("enabled") and backup_cfg.get("on_finish"):
        maybe_backup(output_dir, config["paths"].get("backup_dir"))
        logger.info("Artifacts backed up to %s", config["paths"].get("backup_dir"))

    logger.info("Training finished: %s", metrics)
    return metrics


def main() -> None:
    from scripts.run_train import main as script_main

    script_main()


if __name__ == "__main__":
    main()
