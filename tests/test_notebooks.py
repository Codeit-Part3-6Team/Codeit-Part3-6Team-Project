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


def test_local_experiment_notebook_structure() -> None:
    notebook = _load_notebook("notebooks/local_experiment_template.ipynb")

    assert notebook["nbformat"] == 4
    assert len(notebook["cells"]) >= 10
    source = _joined_source(notebook)

    expected_refs = [
        "scripts/run_validate.py",
        "scripts/run_train.py",
        "scripts/run_predict.py",
        "scripts/run_rag_ingest.py",
        "scripts/run_rag_chat.py",
        "scripts/summarize_experiments.py",
        "configs/smoke/smoke_test_text.yaml",
        "configs/rag/rag_smoke_test.yaml",
        "data/text_processed/sample_positive.txt",
    ]
    for ref in expected_refs:
        assert ref in source
        assert (ROOT / ref).exists(), f"Notebook reference does not exist: {ref}"


def test_colab_experiment_notebook_structure() -> None:
    notebook = _load_notebook("notebooks/colab_experiment_template.ipynb")

    assert notebook["nbformat"] == 4
    assert notebook.get("metadata", {}).get("accelerator") == "GPU"
    source = _joined_source(notebook)

    expected_texts = [
        "from google.colab import drive",
        "drive.mount",
        "REPO_URL",
        "git clone",
        "pip install -r requirements.txt",
        "/content/drive/MyDrive/codeit_ml_project",
        "configs/experiments/exp002_hf_text_finetune_colab.yaml",
    ]
    for text in expected_texts:
        assert text in source


def test_notebook_readme_points_to_templates() -> None:
    readme = (ROOT / "notebooks/README.md").read_text(encoding="utf-8")

    assert "local_experiment_template.ipynb" in readme
    assert "colab_experiment_template.ipynb" in readme
