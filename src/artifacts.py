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

_CHECKPOINT_FILE_SUFFIXES = {".pt", ".pth", ".ckpt", ".safetensors", ".bin"}
_CHECKPOINT_DIR_NAMES = {"checkpoint", "checkpoints", "hf_model", "model"}


def resolve_experiment_dir(project_root: str | Path, config: dict[str, Any]) -> Path:
    """config 기준으로 실험 산출물을 저장할 폴더를 결정합니다."""
    root = Path(project_root)
    experiment_name = config.get("experiment", {}).get("name")
    if not experiment_name:
        raise ValueError("config.experiment.name is required")
    output_dir = config.get("paths", {}).get("output_dir")
    if output_dir:
        # Colab/Drive처럼 절대경로나 명시 경로가 필요할 때는 config의 output_dir를 우선합니다.
        base_dir = root / output_dir
    else:
        # output_dir가 없으면 실험 이름을 기준으로 표준 experiments 폴더를 사용합니다.
        base_dir = root / "experiments" / str(experiment_name)
    run_id = _artifact_policy(config).get("run_id") or config.get("experiment", {}).get("run_id")
    return base_dir / _sanitize_run_id(run_id) if run_id else base_dir


def prepare_experiment_dir(
    project_root: str | Path,
    config: dict[str, Any],
    check_existing: bool = False,
) -> Path:
    """artifact policy를 적용한 뒤 실험 산출물 폴더를 준비합니다."""
    output_dir = resolve_experiment_dir(project_root, config)
    if check_existing:
        _check_existing_policy(output_dir, config)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _check_existing_policy(output_dir: Path, config: dict[str, Any]) -> None:
    policy = _artifact_policy(config)
    on_existing = policy.get("on_existing", "overwrite")
    if on_existing not in {"overwrite", "fail"}:
        raise ValueError(f"Unsupported artifact_policy.on_existing: {on_existing}")
    if on_existing == "fail" and output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Experiment output_dir already exists: {output_dir}")


def _artifact_policy(config: dict[str, Any]) -> dict[str, Any]:
    policy = config.get("artifact_policy", {})
    return policy if isinstance(policy, dict) else {}


def _sanitize_run_id(run_id: Any) -> str:
    text = str(run_id).strip().replace("\\", "_").replace("/", "_")
    if not text or text in {".", ".."}:
        raise ValueError("artifact_policy.run_id must not be empty")
    return text


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
    output_path = Path(output_dir)
    if status in {"running", "success"}:
        # 이전 실패 실행에서 남은 failure.log가 현재 성공 상태와 충돌하지 않도록 정리합니다.
        output_path.joinpath("failure.log").unlink(missing_ok=True)
    write_json(output_path / "run_status.json", payload)


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


def maybe_backup(
    output_dir: str | Path,
    backup_dir: str | Path | None,
    *,
    include_logs: bool = True,
    include_checkpoints: bool = True,
) -> None:
    """실험 산출물을 Google Drive 같은 백업 경로로 복사합니다.

    include_logs를 끄면 *.log 파일을 제외하고, include_checkpoints를 끄면
    모델 weight나 checkpoint 디렉터리처럼 용량이 커지기 쉬운 산출물을 제외합니다.
    metrics/config/run_status 같은 작은 메타데이터는 항상 백업 대상으로 남깁니다.
    """
    if not backup_dir:
        return
    source = Path(output_dir)
    target = Path(backup_dir)
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if not _should_backup_item(item, include_logs=include_logs, include_checkpoints=include_checkpoints):
            continue
        if item.is_file():
            shutil.copy2(item, target / item.name)
        elif item.is_dir():
            destination = target / item.name
            if destination.exists():
                shutil.rmtree(destination)
            # HuggingFace의 hf_model/처럼 폴더 단위 artifact도 백업 대상입니다.
            shutil.copytree(item, destination)


def _should_backup_item(item: Path, *, include_logs: bool, include_checkpoints: bool) -> bool:
    """config의 백업 정책에 따라 파일/디렉터리 복사 여부를 결정합니다."""
    if not include_logs and item.is_file() and item.suffix == ".log":
        return False
    if include_checkpoints:
        return True
    if item.is_dir() and (item.name in _CHECKPOINT_DIR_NAMES or item.name.startswith("checkpoint")):
        return False
    if item.is_file() and item.suffix in _CHECKPOINT_FILE_SUFFIXES:
        return False
    return True
