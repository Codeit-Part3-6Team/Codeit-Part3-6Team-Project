from __future__ import annotations

import csv
import shutil
from pathlib import Path

from src.validate_data import validate_data


def test_validate_image_data_contract_passes(repo_root):
    result = validate_data(repo_root / "data" / "processed")

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["splits"]["train"] == {"red": 3, "blue": 3}


def test_validate_text_data_contract_passes(repo_root):
    result = validate_data(repo_root / "data" / "text_processed")

    assert result["ok"] is True
    assert result["errors"] == []
    assert result["splits"]["valid"] == {"positive": 1, "negative": 1}


def test_validate_text_data_contract_rejects_empty_text(tmp_path: Path, repo_root: Path):
    source = repo_root / "data" / "text_processed"
    target = tmp_path / "text_processed"
    shutil.copytree(source, target)

    train_csv = target / "train.csv"
    rows = list(csv.DictReader(train_csv.open("r", encoding="utf-8", newline="")))
    rows[0]["text"] = ""
    with train_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "label"])
        writer.writeheader()
        writer.writerows(rows)

    result = validate_data(target)

    assert result["ok"] is False
    assert any("empty text" in error for error in result["errors"])

