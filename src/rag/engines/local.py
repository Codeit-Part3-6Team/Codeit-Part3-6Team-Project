from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.rag.adapters import build_answerer_adapter, build_embedding_adapter, build_retriever_adapter
from src.rag.chunker import chunk_documents


@dataclass
class LocalRagEngine:
    """기존 lightweight 구현을 감싼 local RAG 엔진입니다."""

    config: dict[str, Any]
    output_dir: Path

    @property
    def rag_config(self) -> dict[str, Any]:
        return self.config.get("rag", {})

    def chunk_documents(self, documents: list[dict[str, str]]) -> list[dict[str, str]]:
        chunk_cfg = self.rag_config.get("chunk", {})
        return chunk_documents(
            documents,
            chunk_size=int(chunk_cfg.get("size", chunk_cfg.get("chunk_size", 500))),
            overlap=int(chunk_cfg.get("overlap", chunk_cfg.get("chunk_overlap", 80))),
        )

    def embed_chunks(self, chunks: list[dict[str, str]]) -> list[dict[str, Any]]:
        return build_embedding_adapter(self.rag_config.get("embedding", {})).embed_chunks(chunks)

    def retrieve(
        self,
        question: str,
        chunks: list[dict[str, str]],
        embeddings: list[dict[str, Any]],
    ) -> list[dict[str, str | float | int]]:
        return build_retriever_adapter(
            self.rag_config.get("retriever", {}),
            self.rag_config.get("embedding", {}),
        ).retrieve(question, chunks, embeddings)

    def answer(self, question: str, retrieved_chunks: list[dict[str, Any]]) -> dict[str, Any]:
        return build_answerer_adapter(self.rag_config.get("answerer", {})).answer(question, retrieved_chunks)
