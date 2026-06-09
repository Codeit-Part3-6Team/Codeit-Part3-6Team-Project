from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.artifacts import (
    maybe_backup,
    prepare_experiment_dir,
    resolve_experiment_dir,
    write_failure_artifact,
    write_experiment_readme,
    write_history,
    write_run_info,
    write_run_status,
)
from src.config import load_config, write_config_copy, write_json
from src.data import load_dataset, read_json, read_ppm_mean_rgb
from src.metrics import accuracy
from src.models import build_model
from src.models.huggingface_text import (
    HuggingFaceSequenceClassifier,
    build_label_map,
    is_huggingface_model,
)
from src.utils.logger import setup_logger
from src.utils.paths import ensure_dir
from src.utils.seed import set_seed
from src.validate_data import validate_data


def _features(rows: list[dict[str, str]], task: str) -> list[tuple[float, float, float]] | list[str]:
    """split row를 smoke model이 받을 수 있는 feature 형태로 변환합니다."""
    if task == "image_classification":
        return [read_ppm_mean_rgb(row["absolute_image_path"]) for row in rows]
    if task == "text_classification":
        return [row["text"] for row in rows]
    raise ValueError(f"Unsupported task: {task}")


def run_training(config_path: str | Path, project_root: str | Path) -> dict[str, float]:
    """config 하나를 기준으로 학습을 실행하고 표준 실험 산출물을 저장합니다."""
    root = Path(project_root)
    config_path = _resolve_path(root, config_path)
    config = load_config(config_path)
    data_dir = root / config["paths"]["data_dir"]
    output_dir = prepare_experiment_dir(root, config, check_existing=True)
    logger = setup_logger("train", output_dir / "train.log")
    set_seed(config.get("experiment", {}).get("seed"))

    write_run_status(output_dir, "train", "running")
    try:
        logger.info("Start training: %s", config.get("experiment", {}).get("name"))

        validation = validate_data(data_dir)
        if not validation["ok"]:
            raise RuntimeError(f"Data validation failed: {validation['errors']}")
        logger.info("Data validation passed")

        # train/valid/test를 같은 loader로 읽어야 split 간 입력 계약 차이를 빨리 발견할 수 있습니다.
        train_rows = load_dataset(data_dir, config["data"]["train_csv"])
        valid_rows = load_dataset(data_dir, config["data"]["valid_csv"])
        test_rows = load_dataset(data_dir, config["data"]["test_csv"])
        task = config["data"]["task"]
        model_name = config["model"]["name"]

        # HuggingFace 모델은 base model, label map 같은 config 값이 더 필요하므로
        # 가벼운 smoke model registry를 거치지 않고 전용 학습 경로로 보냅니다.
        if is_huggingface_model(model_name):
            metrics = _run_huggingface_training(
                config_path=config_path,
                project_root=root,
                config=config,
                output_dir=output_dir,
                train_rows=train_rows,
                valid_rows=valid_rows,
                test_rows=test_rows,
                logger=logger,
            )
            write_run_status(output_dir, "train", "success", result=metrics)
            return metrics

        model = build_model(model_name)
        logger.info("Model built: %s", model_name)
        train_features = _features(train_rows, task)
        train_labels = [row["label"] for row in train_rows]
        model.fit(list(zip(train_features, train_labels)))

        valid_pred = model.predict(_features(valid_rows, task))
        valid_true = [row["label"] for row in valid_rows]
        test_pred = model.predict(_features(test_rows, task))
        test_true = [row["label"] for row in test_rows]

        # 현재 scaffold는 accuracy만 계산하지만, 이 지점이 macro f1/confusion matrix 확장 위치입니다.
        metrics = {
            "valid_accuracy": accuracy(valid_true, valid_pred),
            "test_accuracy": accuracy(test_true, test_pred),
        }
        history = [{"epoch": 1, **metrics}]

        command = f"python scripts/run_train.py --config {Path(config_path).as_posix()} --project-root {root.as_posix()}"
        # 아래 파일들이 실험 재현과 팀원 간 결과 공유의 최소 단위입니다.
        write_config_copy(config_path, output_dir)
        write_json(output_dir / "best_model.json", model.to_dict())
        write_json(output_dir / "metrics.json", metrics)
        write_history(output_dir / "history.csv", history)
        write_run_info(output_dir, config)
        write_experiment_readme(output_dir, config, metrics, command)
        logger.info("Artifacts saved to %s", output_dir)

        backup_cfg = config.get("backup", {})
        if backup_cfg.get("enabled") and backup_cfg.get("on_finish"):
            # Colab 런타임이 끊겨도 결과를 잃지 않도록 Drive 같은 외부 경로에 복사할 수 있습니다.
            maybe_backup(output_dir, config["paths"].get("backup_dir"))
            logger.info("Artifacts backed up to %s", config["paths"].get("backup_dir"))

        logger.info("Training finished: %s", metrics)
        write_run_status(output_dir, "train", "success", result=metrics)
        return metrics
    except Exception as exc:
        logger.exception("Training failed")
        write_failure_artifact(output_dir, "train", exc)
        raise


def _run_huggingface_training(
    config_path: str | Path,
    project_root: Path,
    config: dict[str, Any],
    output_dir: Path,
    train_rows: list[dict[str, str]],
    valid_rows: list[dict[str, str]],
    test_rows: list[dict[str, str]],
    logger,
) -> dict[str, float]:
    """HuggingFace 텍스트 분류 모델을 학습하고 표준 산출물 구조로 저장합니다."""
    if config["data"]["task"] != "text_classification":
        raise ValueError("HuggingFace sequence classification requires text_classification data.")

    data_cfg = config["data"]
    model_cfg = config["model"]
    text_col = data_cfg.get("text_col", "text")
    label_col = data_cfg.get("label_col", "label")
    class_map_path = data_cfg.get("class_map")
    if class_map_path:
        # class_map.json이 있으면 데이터 계약에 정의된 label id를 우선 사용합니다.
        label2id = {
            label: int(index)
            for label, index in read_json(project_root / config["paths"]["data_dir"] / class_map_path).items()
        }
    else:
        label2id = build_label_map(train_rows, label_col=label_col)

    base_model_name = model_cfg.get("model_name") or model_cfg.get("hf_model_name")
    if not base_model_name:
        raise ValueError("model.model_name or model.hf_model_name is required for HuggingFace training.")

    logger.info("HuggingFace base model: %s", base_model_name)
    model = HuggingFaceSequenceClassifier(
        model_name=base_model_name,
        label2id=label2id,
        max_length=int(data_cfg.get("max_length", 128)),
    )
    hf_metrics, history = model.fit(
        train_rows=train_rows,
        valid_rows=valid_rows,
        output_dir=output_dir,
        train_config=config.get("train", {}),
        text_col=text_col,
        label_col=label_col,
    )
    test_pred = model.predict(
        [row[text_col] for row in test_rows],
        batch_size=int(config.get("train", {}).get("batch_size", 8)),
    )
    test_true = [row[label_col] for row in test_rows]
    # HF 경로도 smoke model과 같은 metrics.json 형식을 유지해 summary 스크립트를 공유합니다.
    metrics = {
        **hf_metrics,
        "test_accuracy": accuracy(test_true, test_pred),
    }

    command = (
        f"python scripts/run_train.py --config {Path(config_path).as_posix()} "
        f"--project-root {project_root.as_posix()}"
    )
    write_config_copy(config_path, output_dir)
    write_json(output_dir / "best_model.json", model.to_dict())
    write_json(output_dir / "metrics.json", metrics)
    write_history(output_dir / "history.csv", history)
    write_run_info(output_dir, config)
    write_experiment_readme(output_dir, config, metrics, command)
    logger.info("HuggingFace artifacts saved to %s", output_dir)

    backup_cfg = config.get("backup", {})
    if backup_cfg.get("enabled") and backup_cfg.get("on_finish"):
        # HuggingFace weight는 폴더 artifact라서 maybe_backup이 디렉터리까지 복사합니다.
        maybe_backup(output_dir, config["paths"].get("backup_dir"))
        logger.info("Artifacts backed up to %s", config["paths"].get("backup_dir"))

    logger.info("Training finished: %s", metrics)
    return metrics


def _resolve_path(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def main() -> None:
    """공식 scripts 진입점으로 CLI 처리를 위임합니다."""
    from scripts.run_train import main as script_main

    script_main()


if __name__ == "__main__":
    main()
