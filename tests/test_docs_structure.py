from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_docs_markdown_files_have_html_counterparts() -> None:
    md_dir = ROOT / "docs" / "md"
    html_dir = ROOT / "docs" / "html"

    md_files = sorted(path for path in md_dir.rglob("*.md"))
    assert md_files, "docs/md에는 최소 하나 이상의 Markdown 문서가 있어야 합니다."

    missing = [
        str(path.relative_to(md_dir))
        for path in md_files
        if not (html_dir / path.relative_to(md_dir).with_suffix(".html")).exists()
    ]
    assert not missing, f"HTML 대응 문서가 없습니다: {missing}"


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
