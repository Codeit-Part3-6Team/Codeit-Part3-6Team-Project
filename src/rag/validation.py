from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from src.artifacts import resolve_experiment_dir
from src.config import load_config
from src.rag.document_loader import SUPPORTED_FILE_TYPES


SUPPORTED_EMBEDDING_PROVIDERS = {"local", "huggingface"}
SUPPORTED_VECTOR_STORES = {"memory", "faiss", "chroma", "elasticsearch"}
SUPPORTED_RETRIEVERS = {"keyword", "semantic", "hybrid"}
SUPPORTED_RUNTIME_RETRIEVERS = {"keyword", "semantic", "hybrid"}
SUPPORTED_LANGCHAIN_RETRIEVERS = {"similarity", "mmr"}
SUPPORTED_RERANKER_PROVIDERS = {"local", "huggingface"}
SUPPORTED_ANSWERERS = {"extractive", "llm"}
SUPPORTED_ANSWERER_PROVIDERS = {"local", "openai", "huggingface", "ollama"}
SUPPORTED_RAG_ENGINES = {"local", "langchain"}
SUPPORTED_LANGCHAIN_EMBEDDING_PROVIDERS = {"local", "huggingface", "ollama", "openai"}
SUPPORTED_LANGCHAIN_VECTOR_STORES = {"memory", "chroma"}
SUPPORTED_LANGCHAIN_ANSWERERS = {"local", "ollama", "openai"}


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
    engine = str(rag.get("engine", "local") or "local")
    loader = rag.get("loader", {})
    chunk = rag.get("splitter", rag.get("chunk", {}))
    checkpoint = rag.get("checkpoint", {})
    embedding = rag.get("embedding", {})
    vector_store = rag.get("vector_store", {})
    retriever = rag.get("retriever", {})
    reranker = rag.get("reranker", {})
    answerer = rag.get("answerer", {})
    evaluation = config.get("evaluation", {})
    artifact_policy = config.get("artifact_policy", {})

    raw_docs_dir = _resolve_path(root, paths.get("raw_docs_dir", ""))
    output_dir = resolve_experiment_dir(root, config) if config.get("experiment") else root / "experiments" / "unknown"
    questions_path = _resolve_path(root, evaluation.get("questions_path", ""))

    file_types = _normalize_file_types(loader.get("file_types", ["txt"]), errors)
    document_counts = _count_documents(raw_docs_dir, file_types, errors, warnings)
    _validate_engine_config(engine, errors)
    _validate_chunk_config(rag.get("splitter", chunk), errors)
    _validate_checkpoint_config(checkpoint, errors)
    _validate_embedding_config(embedding, engine, errors)
    _validate_vector_store_config(vector_store, engine, errors, warnings)
    _validate_retriever_config(retriever, engine, errors)
    _validate_reranker_config(reranker, errors, warnings)
    _validate_answerer_config(answerer, engine, errors, warnings)
    _validate_artifact_policy(artifact_policy, errors)
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
        "engine": engine,
        "chunk_size": chunk.get("size", chunk.get("chunk_size")),
        "chunk_overlap": chunk.get("overlap", chunk.get("chunk_overlap")),
        "checkpoint_enabled": checkpoint.get("enabled", True) if isinstance(checkpoint, dict) else True,
        "checkpoint_resume": checkpoint.get("resume", True) if isinstance(checkpoint, dict) else True,
        "embedding_provider": embedding.get("provider", ""),
        "embedding_model": embedding.get("model_name", ""),
        "vector_store_type": vector_store.get("type", "memory"),
        "vector_store_path": vector_store.get("path", ""),
        "artifact_run_id": artifact_policy.get("run_id", "") if isinstance(artifact_policy, dict) else "",
        "artifact_on_existing": artifact_policy.get("on_existing", "overwrite")
        if isinstance(artifact_policy, dict)
        else "overwrite",
        "reranker_enabled": bool(reranker.get("enabled", False)) if isinstance(reranker, dict) else False,
        "answerer_mode": answerer.get("mode", "extractive"),
        "answerer_provider": answerer.get("provider", "local"),
        "answerer_model": answerer.get("model_name", ""),
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


def _validate_engine_config(engine: str, errors: list[str]) -> None:
    if engine not in SUPPORTED_RAG_ENGINES:
        errors.append(f"unsupported rag.engine: {engine}")


def _validate_chunk_config(chunk: dict[str, Any], errors: list[str]) -> None:
    size = _as_int(chunk.get("size", chunk.get("chunk_size")), "rag.chunk.size", errors)
    overlap = _as_int(chunk.get("overlap", chunk.get("chunk_overlap")), "rag.chunk.overlap", errors)
    if size is not None and size <= 0:
        errors.append("rag.chunk.size must be positive")
    if overlap is not None and overlap < 0:
        errors.append("rag.chunk.overlap must be zero or positive")
    if size is not None and overlap is not None and overlap >= size:
        errors.append("rag.chunk.overlap must be smaller than rag.chunk.size")


def _validate_checkpoint_config(checkpoint: dict[str, Any], errors: list[str]) -> None:
    for key in ["enabled", "resume"]:
        if key in checkpoint and not isinstance(checkpoint[key], bool):
            errors.append(f"rag.checkpoint.{key} must be a boolean")


def _validate_embedding_config(embedding: dict[str, Any], engine: str, errors: list[str]) -> None:
    provider = embedding.get("provider", "local")
    supported = SUPPORTED_LANGCHAIN_EMBEDDING_PROVIDERS if engine == "langchain" else SUPPORTED_EMBEDDING_PROVIDERS
    if provider not in supported:
        errors.append(f"unsupported embedding provider: {provider}")
    model_name = str(embedding.get("model_name", "") or "").strip()
    if provider in {"huggingface", "ollama", "openai"} and not model_name:
        errors.append(f"rag.embedding.model_name is required when provider is {provider}")
    dimension = _as_int(embedding.get("dimension", 64), "rag.embedding.dimension", errors)
    if dimension is not None and dimension <= 0:
        errors.append("rag.embedding.dimension must be positive")
    device = embedding.get("device", "auto")
    if device not in {"auto", "cpu", "cuda"}:
        errors.append(f"unsupported embedding device: {device}")


def _validate_vector_store_config(
    vector_store: dict[str, Any],
    engine: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    store_type = vector_store.get("type", "memory")
    supported = SUPPORTED_LANGCHAIN_VECTOR_STORES if engine == "langchain" else SUPPORTED_VECTOR_STORES
    if store_type not in supported:
        errors.append(f"unsupported vector_store type: {store_type}")
        return
    path = str(vector_store.get("path", "") or "").strip()
    if store_type in {"faiss", "chroma"} and not path:
        errors.append(f"rag.vector_store.path is required when type is {store_type}")
    if store_type == "elasticsearch":
        url = str(vector_store.get("url", "") or "").strip()
        index_name = str(vector_store.get("index_name", "") or vector_store.get("collection_name", "") or "").strip()
        if not url:
            errors.append("rag.vector_store.url is required when type is elasticsearch")
        if not index_name:
            errors.append("rag.vector_store.index_name is required when type is elasticsearch")
    if store_type != "memory" and engine != "langchain":
        warnings.append(f"vector_store type '{store_type}' is config-ready but not implemented in smoke runtime")


def _validate_retriever_config(retriever: dict[str, Any], engine: str, errors: list[str]) -> None:
    method = retriever.get("method", "keyword")
    supported = SUPPORTED_LANGCHAIN_RETRIEVERS if engine == "langchain" else SUPPORTED_RETRIEVERS
    if method not in supported:
        errors.append(f"unsupported retriever method: {method}")
    elif engine != "langchain" and method not in SUPPORTED_RUNTIME_RETRIEVERS:
        errors.append(f"retriever method is not implemented in smoke runtime yet: {method}")
    top_k = _as_int(retriever.get("top_k", 3), "rag.retriever.top_k", errors)
    if top_k is not None and top_k <= 0:
        errors.append("rag.retriever.top_k must be positive")
    score_threshold = _as_float(retriever.get("score_threshold", 0.0), "rag.retriever.score_threshold", errors)
    if score_threshold is not None and score_threshold < 0:
        errors.append("rag.retriever.score_threshold must be zero or positive")
    if method == "hybrid":
        keyword_weight = _as_float(retriever.get("keyword_weight", 0.4), "rag.retriever.keyword_weight", errors)
        semantic_weight = _as_float(retriever.get("semantic_weight", 0.6), "rag.retriever.semantic_weight", errors)
        if keyword_weight is not None and keyword_weight < 0:
            errors.append("rag.retriever.keyword_weight must be zero or positive")
        if semantic_weight is not None and semantic_weight < 0:
            errors.append("rag.retriever.semantic_weight must be zero or positive")


def _validate_reranker_config(
    reranker: dict[str, Any],
    errors: list[str],
    warnings: list[str],
) -> None:
    enabled = bool(reranker.get("enabled", False))
    provider = reranker.get("provider", "huggingface")
    if provider not in SUPPORTED_RERANKER_PROVIDERS:
        errors.append(f"unsupported reranker provider: {provider}")
    top_k = _as_int(reranker.get("top_k", 3), "rag.reranker.top_k", errors)
    if top_k is not None and top_k <= 0:
        errors.append("rag.reranker.top_k must be positive")
    model_name = str(reranker.get("model_name", "") or "").strip()
    if enabled and provider == "huggingface" and not model_name:
        errors.append("rag.reranker.model_name is required when reranker is enabled with huggingface")
    if enabled:
        warnings.append("reranker is config-ready but not implemented in smoke runtime")


def _validate_answerer_config(
    answerer: dict[str, Any],
    engine: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    mode = answerer.get("mode", "extractive")
    if mode not in SUPPORTED_ANSWERERS:
        errors.append(f"unsupported answerer mode: {mode}")
    provider = answerer.get("provider", "local")
    supported_providers = SUPPORTED_LANGCHAIN_ANSWERERS if engine == "langchain" else SUPPORTED_ANSWERER_PROVIDERS
    if provider not in supported_providers:
        errors.append(f"unsupported answerer provider: {provider}")
    model_name = str(answerer.get("model_name", "") or "").strip()
    if mode == "extractive":
        if provider != "local":
            errors.append("rag.answerer.provider must be local when mode is extractive")
        return
    if mode != "llm":
        return

    if provider == "local":
        errors.append("rag.answerer.provider must be openai, huggingface, or ollama when mode is llm")
        return
    if not model_name:
        errors.append("rag.answerer.model_name is required when answerer mode is llm")

    temperature = _as_float(answerer.get("temperature", 0.2), "rag.answerer.temperature", errors)
    if temperature is not None and temperature < 0:
        errors.append("rag.answerer.temperature must be zero or positive")
    max_tokens = _as_int(answerer.get("max_tokens", answerer.get("max_new_tokens", 512)), "rag.answerer.max_tokens", errors)
    if max_tokens is not None and max_tokens <= 0:
        errors.append("rag.answerer.max_tokens must be positive")
    if "require_citations" in answerer and not isinstance(answerer["require_citations"], bool):
        errors.append("rag.answerer.require_citations must be a boolean")

    if provider == "openai":
        api_key_env = str(answerer.get("api_key_env", "OPENAI_API_KEY") or "").strip()
        if not api_key_env:
            errors.append("rag.answerer.api_key_env must not be empty when provider is openai")
    if provider == "ollama":
        base_url = str(answerer.get("base_url", "http://localhost:11434") or "").strip()
        if not base_url:
            errors.append("rag.answerer.base_url must not be empty when provider is ollama")
    if provider == "huggingface":
        device = answerer.get("device", "auto")
        if device not in {"auto", "cpu", "cuda"}:
            errors.append(f"unsupported answerer device: {device}")
    elif engine != "langchain":
        warnings.append(f"answerer provider '{provider}' is config-ready but not implemented in smoke runtime")


def _validate_artifact_policy(policy: Any, errors: list[str]) -> None:
    if policy in ({}, None):
        return
    if not isinstance(policy, dict):
        errors.append("artifact_policy must be a mapping")
        return
    on_existing = policy.get("on_existing", "overwrite")
    if on_existing not in {"overwrite", "fail"}:
        errors.append(f"unsupported artifact_policy.on_existing: {on_existing}")
    run_id = policy.get("run_id")
    if run_id is not None and str(run_id).strip() in {"", ".", ".."}:
        errors.append("artifact_policy.run_id must not be empty")


def _validate_questions_path(root: Path, questions_path: Path, errors: list[str]) -> None:
    if not questions_path.exists():
        errors.append(f"evaluation questions not found: {_display_path(root, questions_path)}")


def _as_int(value: Any, name: str, errors: list[str]) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        errors.append(f"{name} must be an integer")
        return None


def _as_float(value: Any, name: str, errors: list[str]) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        errors.append(f"{name} must be a number")
        return None


def _resolve_path(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _display_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
