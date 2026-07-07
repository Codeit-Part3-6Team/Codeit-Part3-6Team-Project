"""앱 서비스가 공유하는 경로 헬퍼."""

from __future__ import annotations

from pathlib import Path


DEFAULT_SHARED_STREAMLIT_EXPERIMENTS = Path("/shared/experiments/streamlit")


def streamlit_experiments_dir() -> Path:
    """Streamlit RAG run 산출물과 DB를 저장할 디렉터리를 반환합니다.

    VM 공용 환경 기준 `/shared/experiments/streamlit`을 기본으로 씁니다.
    `RAG_STREAMLIT_EXPERIMENTS`가 있으면 그 값을 우선합니다.
    """
    import os

    configured = os.environ.get("RAG_STREAMLIT_EXPERIMENTS", "").strip()
    if configured:
        path = Path(configured).expanduser()
        return path if path.is_absolute() else Path.cwd() / path
    return DEFAULT_SHARED_STREAMLIT_EXPERIMENTS
