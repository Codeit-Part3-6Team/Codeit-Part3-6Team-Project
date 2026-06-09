from __future__ import annotations

import csv
import platform
import shutil
import subprocess
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import write_json


def resolve_experiment_dir(project_root: str | Path, config: dict[str, Any]) -> Path:
    """config 기준으로 실험 산출물을 저장할 폴더를 결정합니다."""
    root = Path(project_root)
    experiment_name = config.get("experiment", {}).get("name")
    if not experiment_name:
        raise ValueError("config.experiment.name is required")
    output_dir = config.get("paths", {}).get("output_dir")
    if output_dir:
        # Colab/Drive처럼 절대경로나 명시 경로가 필요할 때는 config의 output_dir를 우선합니다.
        return root / output_dir
    # output_dir가 없으면 실험 이름을 기준으로 표준 experiments 폴더를 사용합니다.
    return root / "experiments" / str(experiment_name)


def get_git_commit() -> str | None:
    """현재 Git commit hash를 가져옵니다. Git 정보가 없으면 None을 반환합니다."""
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
    """재현성을 위해 실행 환경과 실험 정보를 run_info.json으로 저장합니다."""
    payload = {
        "experiment": config.get("experiment", {}),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "git_commit": get_git_commit(),
    }
    write_json(Path(output_dir) / "run_info.json", payload)


def write_run_status(
    output_dir: str | Path,
    operation: str,
    status: str,
    result: dict[str, Any] | None = None,
    error: dict[str, str] | None = None,
) -> None:
    """실행 상태를 run_status.json으로 저장합니다."""
    payload: dict[str, Any] = {
        "operation": operation,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if result is not None:
        payload["result"] = result
    if error is not None:
        payload["error"] = error
    write_json(Path(output_dir) / "run_status.json", payload)


def write_failure_artifact(output_dir: str | Path, operation: str, exc: Exception) -> None:
    """실패 상태와 traceback을 저장해 나중에 원인을 확인할 수 있게 합니다."""
    error = {"type": type(exc).__name__, "message": str(exc)}
    write_run_status(output_dir, operation, "failed", error=error)
    failure_text = (
        f"operation: {operation}\n"
        f"failed_at: {datetime.now(timezone.utc).isoformat()}\n"
        f"error_type: {type(exc).__name__}\n"
        f"message: {exc}\n\n"
        f"{traceback.format_exc()}"
    )
    Path(output_dir, "failure.log").write_text(failure_text, encoding="utf-8")


def write_history(path: str | Path, rows: list[dict[str, Any]]) -> None:
    """epoch별 metric과 loss를 history.csv로 저장합니다."""
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
    """실험 폴더 안에 사람이 이어서 기록할 수 있는 README를 생성합니다."""
    experiment = config.get("experiment", {})
    data = config.get("data", {})
    model = config.get("model", {})
    metric_lines = "\n".join(f"- {key}: {value}" for key, value in metrics.items())
    text = f"""# {experiment.get("name", "experiment")}

## 목적

config 기반 실험 실행 결과입니다. 자세한 해석과 다음 액션은 담당자가 이 파일에 이어서 기록합니다.

## 실행 명령

```bash
{command}
```

## 주요 설정

- task: {data.get("task")}
- model: {model.get("name")}
- base_model: {model.get("model_name") or model.get("hf_model_name") or "-"}
- seed: {experiment.get("seed")}
- contract_version: {experiment.get("contract_version")}

## 결과

{metric_lines}

## 결론

- TODO: 이 실험에서 확인한 점을 적습니다.

## 다음 액션

- TODO: 다음 실험에서 바꿀 항목이나 확인할 리스크를 적습니다.

## 실패/주의 사항

- TODO: 실패했다면 원인, 재현 방법, 해결 후보를 적습니다.

## 산출물

- config.yaml
- metrics.json
- history.csv
- run_info.json
- best_model.json
- hf_model/ (HuggingFace 모델인 경우)
- train.log
"""
    Path(output_dir, "README.md").write_text(text, encoding="utf-8")


def maybe_backup(output_dir: str | Path, backup_dir: str | Path | None) -> None:
    """실험 산출물을 Google Drive 같은 백업 경로로 복사합니다."""
    if not backup_dir:
        return
    source = Path(output_dir)
    target = Path(backup_dir)
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if item.is_file():
            shutil.copy2(item, target / item.name)
        elif item.is_dir():
            destination = target / item.name
            if destination.exists():
                shutil.rmtree(destination)
            # HuggingFace의 hf_model/처럼 폴더 단위 artifact도 백업 대상입니다.
            shutil.copytree(item, destination)
