from __future__ import annotations

from pathlib import Path


def resolve_project_path(project_root: str | Path, path: str | Path) -> Path:
    """절대경로 또는 project root 기준 상대경로를 Path로 해석합니다."""
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return Path(project_root) / candidate


def ensure_dir(path: str | Path) -> Path:
    """폴더가 없으면 생성하고 Path 객체로 반환합니다."""
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target
