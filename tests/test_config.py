from __future__ import annotations

from src.config import _parse_simple_yaml, load_config


def test_load_config_reads_local_fallback_rag_file_types(repo_root):
    config = load_config(repo_root / "configs" / "experiments" / "rag" / "rag_semantic.yaml")

    assert config["rag"]["loader"]["file_types"] == ["txt", "pdf", "docx", "hwpx", "hwp"]
    assert config["rag"].get("engine", "local") == "local"
    assert config["rag"]["embedding"]["provider"] == "local"
    assert config["rag"]["vector_store"]["type"] == "memory"
    assert config["rag"]["reranker"]["enabled"] is False
    assert config["rag"]["answerer"]["provider"] == "local"


def test_load_config_reads_langchain_rag_default(repo_root):
    config = load_config(repo_root / "configs" / "experiments" / "rag" / "rag_langchain.yaml")

    assert config["experiment"]["name"] == "rag_langchain"
    assert config["rag"]["engine"] == "langchain"
    assert config["rag"]["splitter"]["type"] == "recursive_character"
    assert config["rag"]["embedding"]["provider"] == "local"
    assert config["rag"]["retriever"]["method"] == "similarity"
    assert config["rag"]["answerer"]["provider"] == "local"


def test_load_config_reads_rag_hybrid_config(repo_root):
    config = load_config(repo_root / "configs" / "experiments" / "rag" / "rag_hybrid.yaml")

    assert config["experiment"]["name"] == "rag_hybrid"
    assert config["rag"]["retriever"]["method"] == "hybrid"
    assert config["rag"]["retriever"]["keyword_weight"] == 0.4
    assert config["rag"]["retriever"]["semantic_weight"] == 0.6


def test_load_config_accepts_utf8_bom_yaml(tmp_path):
    config_path = tmp_path / "bom_config.yaml"
    config_path.write_text(
        "experiment:\n  name: bom_unit\nrag:\n  retriever:\n    method: semantic\n",
        encoding="utf-8-sig",
    )

    config = load_config(config_path)

    assert "experiment" in config
    assert "\ufeffexperiment" not in config
    assert config["experiment"]["name"] == "bom_unit"


def test_fallback_yaml_parser_handles_nested_dicts_lists_and_scalars():
    parsed = _parse_simple_yaml(
        """
experiment:
  name: unit
  seed: 42
backup:
  enabled: false
report:
  - accuracy
  - f1
paths:
  backup_dir:
"""
    )

    assert parsed["experiment"]["name"] == "unit"
    assert parsed["experiment"]["seed"] == 42
    assert parsed["backup"]["enabled"] is False
    assert parsed["report"] == ["accuracy", "f1"]
    assert parsed["paths"]["backup_dir"] is None
