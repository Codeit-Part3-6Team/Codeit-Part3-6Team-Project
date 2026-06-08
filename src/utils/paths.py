from __future__ import annotations

from pathlib import Path


def resolve_project_path(project_root: str | Path, path: str | Path) -> Path:
    """Resolve a path that may be absolute or relative to the project root."""
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return Path(project_root) / candidate


def ensure_dir(path: str | Path) -> Path:
    """Create a directory if needed and return it as a Path."""
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target
