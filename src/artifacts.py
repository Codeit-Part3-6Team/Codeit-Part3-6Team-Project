from __future__ import annotations

import csv
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any

from src.config import write_json


def resolve_experiment_dir(project_root: str | Path, config: dict[str, Any]) -> Path:
    root = Path(project_root)
    experiment_name = config.get("experiment", {}).get("name")
    if not experiment_name:
        raise ValueError("config.experiment.name is required")
    output_dir = config.get("paths", {}).get("output_dir")
    if output_dir:
        return root / output_dir
    return root / "experiments" / str(experiment_name)


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


def write_experiment_readme(
    output_dir: str | Path,
    config: dict[str, Any],
    metrics: dict[str, float],
    command: str,
) -> None:
    experiment = config.get("experiment", {})
    data = config.get("data", {})
    model = config.get("model", {})
    metric_lines = "\n".join(f"- {key}: {value}" for key, value in metrics.items())
    text = f"""# {experiment.get("name", "experiment")}

## 목적

config 기반 실험 실행 결과입니다. 자세한 해석은 담당자가 추가로 작성합니다.

## 실행 명령

```bash
{command}
```

## 주요 설정

- task: {data.get("task")}
- model: {model.get("name")}
- seed: {experiment.get("seed")}
- contract_version: {experiment.get("contract_version")}

## 결과

{metric_lines}

## 산출물

- config.yaml
- metrics.json
- history.csv
- run_info.json
- best_model.json
- train.log
"""
    Path(output_dir, "README.md").write_text(text, encoding="utf-8")


def maybe_backup(output_dir: str | Path, backup_dir: str | Path | None) -> None:
    if not backup_dir:
        return
    source = Path(output_dir)
    target = Path(backup_dir)
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if item.is_file():
            shutil.copy2(item, target / item.name)
