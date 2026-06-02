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
    return tmp_path

