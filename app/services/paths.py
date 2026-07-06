"""앱 서비스가 공유하는 경로 헬퍼."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SHARED_STREAMLIT_EXPERIMENTS = Path("/shared/experiments/streamlit")


def streamlit_experiments_dir() -> Path:
    """Streamlit RAG run 산출물과 DB를 저장할 디렉터리를 반환합니다.

    VM 공용 환경에서는 `/shared/experiments/streamlit`을 기본으로 쓰고,
    로컬처럼 `/shared/experiments`가 없으면 프로젝트 내부
    `experiments/streamlit`로 fallback합니다.
    `RAG_STREAMLIT_EXPERIMENTS`가 있으면 그 값을 우선합니다.
    """
    configured = os.environ.get("RAG_STREAMLIT_EXPERIMENTS", "").strip()
    if configured:
        path = Path(configured).expanduser()
        return path if path.is_absolute() else PROJECT_ROOT / path
    if os.name != "nt" and DEFAULT_SHARED_STREAMLIT_EXPERIMENTS.parent.exists():
        return DEFAULT_SHARED_STREAMLIT_EXPERIMENTS
    return PROJECT_ROOT / "experiments" / "streamlit"
