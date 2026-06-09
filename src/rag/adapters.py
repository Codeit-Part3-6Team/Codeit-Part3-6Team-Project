from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from src.rag.answerer import build_answer
from src.rag.embedder import DEFAULT_EMBEDDING_MODEL, embed_chunks
from src.rag.retriever import retrieve_chunks
from src.rag.vector_store import retrieve_chunks_by_vector


class RagEmbeddingAdapter(Protocol):
    """chunk 목록을 embedding artifact row로 변환하는 adapter 계약입니다."""

    def embed_chunks(self, chunks: list[dict[str, str]]) -> list[dict[str, Any]]:
        ...


class RagRetrieverAdapter(Protocol):
    """질문과 저장된 산출물로 top-k chunk를 반환하는 adapter 계약입니다."""

    def retrieve(
        self,
        question: str,
        chunks: list[dict[str, str]],
        embeddings: list[dict[str, Any]],
    ) -> list[dict[str, str | float | int]]:
        ...


class RagAnswererAdapter(Protocol):
    """검색 결과를 답변/citation payload로 바꾸는 adapter 계약입니다."""

    def answer(self, question: str, retrieved_chunks: list[dict[str, Any]]) -> dict[str, Any]:
        ...


@dataclass
class LocalHashingEmbeddingAdapter:
    """현재 smoke pipeline에서 실제 동작하는 local hashing embedding 구현체입니다."""

    dimension: int = 64
    model_name: str = DEFAULT_EMBEDDING_MODEL

    def embed_chunks(self, chunks: list[dict[str, str]]) -> list[dict[str, Any]]:
        return embed_chunks(chunks, dimension=self.dimension, model_name=self.model_name)


@dataclass
class KeywordRetrieverAdapter:
    """token overlap 기반 keyword retriever 구현체입니다."""

    top_k: int = 3
    score_threshold: float = 0.0

    def retrieve(
        self,
        question: str,
        chunks: list[dict[str, str]],
        embeddings: list[dict[str, Any]],
    ) -> list[dict[str, str | float | int]]:
        return retrieve_chunks(question, chunks, top_k=self.top_k, score_threshold=self.score_threshold)


@dataclass
class MemorySemanticRetrieverAdapter:
    """JSONL embedding을 메모리에 올려 cosine 기반으로 검색하는 구현체입니다."""

    top_k: int = 3
    score_threshold: float = 0.0
    dimension: int = 64

    def retrieve(
        self,
        question: str,
        chunks: list[dict[str, str]],
        embeddings: list[dict[str, Any]],
    ) -> list[dict[str, str | float | int]]:
        return retrieve_chunks_by_vector(
            question,
            chunks,
            embeddings,
            top_k=self.top_k,
            score_threshold=self.score_threshold,
            dimension=self.dimension,
        )


@dataclass
class ExtractiveAnswererAdapter:
    """검색된 chunk에서 답변 문장을 뽑아 citation과 함께 반환하는 구현체입니다."""

    fallback_message: str

    def answer(self, question: str, retrieved_chunks: list[dict[str, Any]]) -> dict[str, Any]:
        return build_answer(question, retrieved_chunks, fallback_message=self.fallback_message)


def build_embedding_adapter(config: dict[str, Any]) -> RagEmbeddingAdapter:
    """rag.embedding config에 맞는 embedding adapter를 반환합니다."""
    provider = config.get("provider", "local")
    if provider == "local":
        return LocalHashingEmbeddingAdapter(
            dimension=int(config.get("dimension", 64)),
            model_name=config.get("model_name", DEFAULT_EMBEDDING_MODEL),
        )
    raise NotImplementedError(f"RAG embedding provider is not implemented yet: {provider}")


def build_retriever_adapter(config: dict[str, Any], embedding_config: dict[str, Any]) -> RagRetrieverAdapter:
    """rag.retriever config에 맞는 retriever adapter를 반환합니다."""
    method = config.get("method", "keyword")
    top_k = int(config.get("top_k", 3))
    score_threshold = float(config.get("score_threshold", 0.0))
    if method == "keyword":
        return KeywordRetrieverAdapter(top_k=top_k, score_threshold=score_threshold)
    if method == "semantic":
        return MemorySemanticRetrieverAdapter(
            top_k=top_k,
            score_threshold=score_threshold,
            dimension=int(embedding_config.get("dimension", 64)),
        )
    raise NotImplementedError(f"RAG retriever method is not implemented yet: {method}")


def build_answerer_adapter(config: dict[str, Any]) -> RagAnswererAdapter:
    """rag.answerer config에 맞는 answerer adapter를 반환합니다."""
    mode = config.get("mode", "extractive")
    provider = config.get("provider", "local")
    if mode == "extractive" and provider == "local":
        return ExtractiveAnswererAdapter(
            fallback_message=config.get("fallback_message", "문서에서 확인하지 못했습니다."),
        )
    raise NotImplementedError(f"RAG answerer is not implemented yet: mode={mode}, provider={provider}")


def describe_rag_implementations() -> dict[str, list[dict[str, str]]]:
    """현재 registry 기준으로 실제 구현/계약만 존재하는 RAG 옵션을 분류합니다."""
    return {
        "implemented": [
            {"type": "embedding", "key": "local", "description": "hashing-char-ngram smoke embedding"},
            {"type": "vector_store", "key": "memory", "description": "embeddings.jsonl in-memory retrieval"},
            {"type": "retriever", "key": "keyword", "description": "token overlap keyword search"},
            {"type": "retriever", "key": "semantic", "description": "local hashing vector semantic search"},
            {"type": "answerer", "key": "extractive/local", "description": "chunk sentence extraction"},
        ],
        "contract_only": [
            {"type": "embedding", "key": "huggingface", "description": "validated config contract only"},
            {"type": "vector_store", "key": "faiss", "description": "validated config contract only"},
            {"type": "vector_store", "key": "chroma", "description": "validated config contract only"},
            {"type": "vector_store", "key": "elasticsearch", "description": "validated config contract only"},
            {"type": "retriever", "key": "hybrid", "description": "validated config contract only"},
            {"type": "reranker", "key": "enabled", "description": "validated config contract only"},
            {"type": "answerer", "key": "llm/openai", "description": "validated config contract only"},
            {"type": "answerer", "key": "llm/huggingface", "description": "validated config contract only"},
        ],
    }


def resolve_vector_store_artifact_path(output_dir: str | Path, vector_store_config: dict[str, Any]) -> Path:
    """현재 memory vector store가 사용하는 embedding artifact 경로를 반환합니다."""
    store_type = vector_store_config.get("type", "memory")
    if store_type != "memory":
        raise NotImplementedError(f"RAG vector_store type is not implemented yet: {store_type}")
    return Path(output_dir) / "embeddings.jsonl"
