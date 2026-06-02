from __future__ import annotations

import csv
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any

from src.config import write_json


def get_git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return result.stdout.strip()


def write_run_info(output_dir: str | Path, config: dict[str, Any]) -> None:
    payload = {
        "experiment": config.get("experiment", {}),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "git_commit": get_git_commit(),
    }
    write_json(Path(output_dir) / "run_info.json", payload)


def write_history(path: str | Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def maybe_backup(output_dir: str | Path, backup_dir: str | Path | None) -> None:
    if not backup_dir:
        return
    source = Path(output_dir)
    target = Path(backup_dir)
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if item.is_file():
            shutil.copy2(item, target / item.name)

