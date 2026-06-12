import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_notebook(path: str) -> dict:
    notebook_path = ROOT / path
    assert notebook_path.exists(), f"Notebook not found: {path}"
    return json.loads(notebook_path.read_text(encoding="utf-8"))


def _joined_source(notebook: dict) -> str:
    return "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook.get("cells", [])
    )


def test_rag_config_run_notebook_structure() -> None:
    notebook = _load_notebook("notebooks/rag/rag_config_run.ipynb")

    assert notebook["nbformat"] == 4
    assert len(notebook["cells"]) >= 10
    source = _joined_source(notebook)

    expected_file_refs = [
        "scripts/check_rag_pipeline.py",
        "scripts/run_rag_ingest.py",
        "scripts/run_rag_retrieve.py",
        "scripts/run_rag_chat.py",
        "scripts/run_rag_rehearsal.py",
        "scripts/compare_rag_retrievers.py",
        "configs/experiments/rag/rag_langchain.yaml",
        "configs/experiments/rag/rag_realistic_docs.yaml",
        "configs/experiments/rag/rag_hybrid.yaml",
        "data/rag_sample/eval_questions.csv",
    ]
    expected_texts = [
        "display_metrics",
        "display_answers",
        "display_failure_tables",
        "display_rehearsal",
        "REALISTIC_OUTPUT_DIR",
        "source_path",
    ]
    for ref in expected_file_refs:
        assert ref in source
        assert (ROOT / ref).exists(), f"Notebook reference does not exist: {ref}"
    for text in expected_texts:
        assert text in source


def test_colab_drive_run_notebook_structure() -> None:
    notebook = _load_notebook("notebooks/rag/rag_colab_drive_run.ipynb")

    assert notebook["nbformat"] == 4
    source = _joined_source(notebook)

    expected_texts = [
        "Colab에서 RAG 실험을 돌릴 때",
        "from google.colab import drive",
        "drive.mount",
        "REPO_URL",
        "git clone",
        "pip install -r requirements.txt",
        "/content/drive/MyDrive/codeit_rag_project",
        "configs/experiments/rag/rag_colab_drive.yaml",
        "scripts/run_rag_ingest.py",
        "scripts/run_rag_chat.py",
        "display_metrics",
        "display_answers",
        "display_failure_tables",
    ]
    for text in expected_texts:
        assert text in source


def test_notebook_readme_points_to_templates() -> None:
    readme = (ROOT / "notebooks/README.md").read_text(encoding="utf-8")

    assert "rag/rag_config_run.ipynb" in readme
    assert "rag/rag_colab_drive_run.ipynb" in readme
    assert "templates/colab_drive_run.md" in readme
