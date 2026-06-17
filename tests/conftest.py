from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def repo_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture()
def isolated_project(tmp_path: Path, repo_root: Path) -> Path:
    for dirname in ["configs", "data"]:
        shutil.copytree(repo_root / dirname, tmp_path / dirname)
    # VM 절대경로를 테스트용 상대경로로 덮어씁니다
    for yaml_file in tmp_path.glob("configs/**/*.yaml"):
        content = yaml_file.read_text(encoding="utf-8")
        if "/shared/data/raw_docs" in content:
            yaml_file.write_text(
                content.replace("/shared/data/raw_docs", "data/rag_sample"),
                encoding="utf-8",
            )
    return tmp_path

