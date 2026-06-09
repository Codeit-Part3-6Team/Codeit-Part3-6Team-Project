from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from src.artifacts import resolve_experiment_dir
from src.config import load_config
from src.rag.document_loader import SUPPORTED_FILE_TYPES


SUPPORTED_RETRIEVERS = {"keyword", "semantic"}
SUPPORTED_ANSWERERS = {"extractive"}


def check_rag_pipeline(config_path: str | Path, project_root: str | Path = ".") -> dict[str, Any]:
    """RAG pipeline을 실행하기 전에 config와 입력 경로를 점검합니다."""
    root = Path(project_root)
    resolved_config_path = _resolve_path(root, config_path)
    errors: list[str] = []
    warnings: list[str] = []

    if not resolved_config_path.exists():
        return {
            "ok": False,
            "errors": [f"config file not found: {_display_path(root, resolved_config_path)}"],
            "warnings": warnings,
            "summary": {},
        }

    config = load_config(resolved_config_path)
    _validate_required_sections(config, errors)
    summary = _build_summary(root, resolved_config_path, config, errors, warnings)
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": summary,
    }


def _validate_required_sections(config: dict[str, Any], errors: list[str]) -> None:
    for section in ["experiment", "paths", "rag", "evaluation"]:
        if section not in config or not isinstance(config[section], dict):
            errors.append(f"missing required section: {section}")


def _build_summary(
    root: Path,
    config_path: Path,
    config: dict[str, Any],
    errors: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    paths = config.get("paths", {})
    rag = config.get("rag", {})
    loader = rag.get("loader", {})
    chunk = rag.get("chunk", {})
    embedding = rag.get("embedding", {})
    retriever = rag.get("retriever", {})
    answerer = rag.get("answerer", {})
    evaluation = config.get("evaluation", {})

    raw_docs_dir = _resolve_path(root, paths.get("raw_docs_dir", ""))
    output_dir = resolve_experiment_dir(root, config) if config.get("experiment") else root / "experiments" / "unknown"
    questions_path = _resolve_path(root, evaluation.get("questions_path", ""))

    file_types = _normalize_file_types(loader.get("file_types", ["txt"]), errors)
    document_counts = _count_documents(raw_docs_dir, file_types, errors, warnings)
    _validate_chunk_config(chunk, errors)
    _validate_embedding_config(embedding, errors)
    _validate_retriever_config(retriever, errors)
    _validate_answerer_config(answerer, errors)
    _validate_questions_path(root, questions_path, errors)

    if output_dir.exists():
        warnings.append(f"output_dir already exists and may be overwritten: {_display_path(root, output_dir)}")

    return {
        "config_path": _display_path(root, config_path),
        "experiment": config.get("experiment", {}).get("name", ""),
        "raw_docs_dir": _display_path(root, raw_docs_dir),
        "output_dir": _display_path(root, output_dir),
        "questions_path": _display_path(root, questions_path),
        "file_types": sorted(file_types),
        "document_counts": dict(sorted(document_counts.items())),
        "retriever_method": retriever.get("method", "keyword"),
        "chunk_size": chunk.get("size"),
        "chunk_overlap": chunk.get("overlap"),
        "embedding_provider": embedding.get("provider", ""),
        "embedding_model": embedding.get("model_name", ""),
    }


def _normalize_file_types(value: Any, errors: list[str]) -> set[str]:
    if not isinstance(value, list) or not value:
        errors.append("rag.loader.file_types must be a non-empty list")
        return set()
    file_types = {str(item).lower().lstrip(".") for item in value}
    unknown = file_types - SUPPORTED_FILE_TYPES
    if unknown:
        errors.append(f"unsupported file types: {sorted(unknown)}")
    return file_types & SUPPORTED_FILE_TYPES


def _count_documents(
    raw_docs_dir: Path,
    file_types: set[str],
    errors: list[str],
    warnings: list[str],
) -> Counter[str]:
    counts: Counter[str] = Counter()
    if not raw_docs_dir.exists():
        errors.append(f"raw_docs_dir not found: {raw_docs_dir}")
        return counts
    for path in raw_docs_dir.iterdir():
        if not path.is_file():
            continue
        suffix = path.suffix.lower().lstrip(".")
        if suffix in file_types:
            counts[suffix] += 1
    if not counts:
        errors.append(f"no input documents found in {raw_docs_dir} for file types {sorted(file_types)}")
    ignored = [
        path.name
        for path in raw_docs_dir.iterdir()
        if path.is_file() and path.suffix.lower().lstrip(".") not in file_types
    ]
    if ignored:
        warnings.append(f"ignored files due to file type filter: {ignored}")
    return counts


def _validate_chunk_config(chunk: dict[str, Any], errors: list[str]) -> None:
    size = _as_int(chunk.get("size"), "rag.chunk.size", errors)
    overlap = _as_int(chunk.get("overlap"), "rag.chunk.overlap", errors)
    if size is not None and size <= 0:
        errors.append("rag.chunk.size must be positive")
    if overlap is not None and overlap < 0:
        errors.append("rag.chunk.overlap must be zero or positive")
    if size is not None and overlap is not None and overlap >= size:
        errors.append("rag.chunk.overlap must be smaller than rag.chunk.size")


def _validate_embedding_config(embedding: dict[str, Any], errors: list[str]) -> None:
    dimension = _as_int(embedding.get("dimension", 64), "rag.embedding.dimension", errors)
    if dimension is not None and dimension <= 0:
        errors.append("rag.embedding.dimension must be positive")


def _validate_retriever_config(retriever: dict[str, Any], errors: list[str]) -> None:
    method = retriever.get("method", "keyword")
    if method not in SUPPORTED_RETRIEVERS:
        errors.append(f"unsupported retriever method: {method}")
    top_k = _as_int(retriever.get("top_k", 3), "rag.retriever.top_k", errors)
    if top_k is not None and top_k <= 0:
        errors.append("rag.retriever.top_k must be positive")


def _validate_answerer_config(answerer: dict[str, Any], errors: list[str]) -> None:
    mode = answerer.get("mode", "extractive")
    if mode not in SUPPORTED_ANSWERERS:
        errors.append(f"unsupported answerer mode: {mode}")


def _validate_questions_path(root: Path, questions_path: Path, errors: list[str]) -> None:
    if not questions_path.exists():
        errors.append(f"evaluation questions not found: {_display_path(root, questions_path)}")


def _as_int(value: Any, name: str, errors: list[str]) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        errors.append(f"{name} must be an integer")
        return None


def _resolve_path(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _display_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
