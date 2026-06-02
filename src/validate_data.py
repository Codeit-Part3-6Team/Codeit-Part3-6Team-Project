from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import read_json, read_split_csv, summarize_labels


def validate_data(data_dir: str | Path) -> dict[str, object]:
    base = Path(data_dir)
    required_files = ["train.csv", "valid.csv", "test.csv", "class_map.json", "dataset_info.json"]
    errors: list[str] = []
    warnings: list[str] = []

    for filename in required_files:
        if not (base / filename).exists():
            errors.append(f"Missing required file: {filename}")

    if errors:
        return {"ok": False, "errors": errors, "warnings": warnings}

    class_map = read_json(base / "class_map.json")
    dataset_info = read_json(base / "dataset_info.json")
    task = dataset_info.get("task", "image_classification")
    valid_labels = set(class_map)
    seen_paths: dict[str, str] = {}
    split_summaries: dict[str, dict[str, int]] = {}
    required_columns_by_task = {
        "image_classification": ["image_path", "label"],
        "text_classification": ["text", "label"],
    }
    required_columns = required_columns_by_task.get(str(task), ["label"])

    for split in ["train", "valid", "test"]:
        rows = read_split_csv(base / f"{split}.csv")
        if not rows:
            errors.append(f"{split}.csv is empty")
            continue
        columns = set(rows[0])
        for required_col in required_columns:
            if required_col not in columns:
                errors.append(f"{split}.csv missing column: {required_col}")
        for index, row in enumerate(rows, start=2):
            label = row.get("label", "")
            if task == "image_classification":
                image_path = row.get("image_path", "")
                if not image_path:
                    errors.append(f"{split}.csv line {index}: empty image_path")
                    continue
                if not (base / image_path).exists():
                    errors.append(f"{split}.csv line {index}: file not found: {image_path}")
                previous_split = seen_paths.get(image_path)
                if previous_split and previous_split != split:
                    errors.append(f"Duplicate sample across splits: {image_path} in {previous_split} and {split}")
                seen_paths[image_path] = split
            if task == "text_classification" and not row.get("text", "").strip():
                errors.append(f"{split}.csv line {index}: empty text")
            if label not in valid_labels:
                errors.append(f"{split}.csv line {index}: unknown label: {label}")
        split_summaries[split] = summarize_labels(rows)

    if dataset_info.get("contract_version") is None:
        warnings.append("dataset_info.json has no contract_version")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "class_map": class_map,
        "splits": split_summaries,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/processed")
    args = parser.parse_args()
    result = validate_data(args.data_dir)
    print(result)
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
