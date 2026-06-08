from __future__ import annotations

from src.config import _parse_simple_yaml, load_config


def test_load_config_reads_text_smoke_config(repo_root):
    config = load_config(repo_root / "configs" / "smoke_test_text.yaml")

    assert config["experiment"]["name"] == "smoke_test_text"
    assert config["data"]["task"] == "text_classification"
    assert config["model"]["name"] == "keyword_text_classifier"
    assert config["backup"]["enabled"] is False


def test_load_config_reads_huggingface_text_config(repo_root):
    config = load_config(repo_root / "configs" / "exp002_hf_text_finetune.yaml")

    assert config["experiment"]["name"] == "exp002_hf_text_finetune"
    assert config["data"]["task"] == "text_classification"
    assert config["model"]["name"] == "huggingface_sequence_classifier"
    assert config["model"]["model_name"] == "distilbert-base-multilingual-cased"
    assert config["train"]["batch_size"] == 4


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
