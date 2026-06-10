from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_docs_markdown_files_have_html_counterparts() -> None:
    md_dir = ROOT / "docs" / "md"
    html_dir = ROOT / "docs" / "html"

    md_files = sorted(path for path in md_dir.glob("*.md"))
    assert md_files, "docs/md에는 최소 하나 이상의 Markdown 문서가 있어야 합니다."

    missing = [
        path.name
        for path in md_files
        if not (html_dir / f"{path.stem}.html").exists()
    ]
    assert not missing, f"HTML 대응 문서가 없습니다: {missing}"


def test_key_directories_have_readme() -> None:
    required_dirs = [
        "app",
        "artifacts",
        "checkpoints",
        "configs",
        "data",
        "docs",
        "docs/html",
        "docs/md",
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
