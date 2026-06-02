from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_split_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_dataset(data_dir: str | Path, split_csv: str) -> list[dict[str, str]]:
    data_path = Path(data_dir)
    rows = read_split_csv(data_path / split_csv)
    for row in rows:
        if "image_path" in row:
            row["absolute_image_path"] = str(data_path / row["image_path"])
    return rows


def summarize_labels(rows: list[dict[str, str]], label_col: str = "label") -> dict[str, int]:
    return dict(Counter(row[label_col] for row in rows))


def read_ppm_mean_rgb(path: str | Path) -> tuple[float, float, float]:
    """Read a tiny P3 ASCII PPM image and return mean RGB values in 0..1 scale."""
    tokens: list[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            tokens.extend(line.split())
    if len(tokens) < 4 or tokens[0] != "P3":
        raise ValueError(f"{path} is not a P3 ASCII PPM file")
    width = int(tokens[1])
    height = int(tokens[2])
    max_value = int(tokens[3])
    values = [int(item) for item in tokens[4:]]
    expected = width * height * 3
    if len(values) != expected:
        raise ValueError(f"{path} has {len(values)} RGB values, expected {expected}")
    channels = [values[i::3] for i in range(3)]
    scale = float(max_value)
    return tuple(sum(channel) / len(channel) / scale for channel in channels)  # type: ignore[return-value]
