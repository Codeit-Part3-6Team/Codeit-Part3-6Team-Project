from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_docs_core_directories_exist() -> None:
    """팀 공유 문서, 세부 문서, HTML 자료, LLM 문맥 디렉터리를 확인합니다."""
    required_dirs = [
        ROOT / "docs" / "team",
        ROOT / "docs" / "md",
        ROOT / "docs" / "html",
        ROOT / "docs" / "llm",
    ]

    missing = [str(path.relative_to(ROOT)) for path in required_dirs if not path.is_dir()]
    assert not missing, f"필수 문서 디렉터리가 없습니다: {missing}"


def test_key_directories_have_readme() -> None:
    required_dirs = [
        "app",
        "artifacts",
        "checkpoints",
        "configs",
        "configs/examples",
        "configs/examples/classification",
        "configs/experiments",
        "configs/experiments/rag",
        "configs/preprocess",
        "configs/smoke",
        "data",
        "docs",
        "docs/team",
        "docs/html",
        "docs/html/data",
        "docs/html/experiments",
        "docs/html/kickoff",
        "docs/html/overview",
        "docs/html/rag",
        "docs/html/workflow",
        "docs/llm",
        "docs/md",
        "docs/md/data",
        "docs/md/experiments",
        "docs/md/kickoff",
        "docs/md/overview",
        "docs/md/rag",
        "docs/md/workflow",
        "experiments",
        "models",
        "notebooks",
        "outputs",
        "reports",
        "scripts",
        "src",
        "src/models",
        "src/rag",
        "src/utils",
        "tests",
    ]

    missing = [
        directory
        for directory in required_dirs
        if not (ROOT / directory / "README.md").exists()
    ]
    assert not missing, f"README.md가 필요한 디렉터리에 없습니다: {missing}"
