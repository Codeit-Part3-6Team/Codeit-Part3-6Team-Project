from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class RagEngine(Protocol):
    """RAG 내부 엔진이 pipeline에 제공해야 하는 표준 계약입니다."""

    def chunk_documents(self, documents: list[dict[str, str]]) -> list[dict[str, str]]:
        ...

    def embed_chunks(self, chunks: list[dict[str, str]]) -> list[dict[str, Any]]:
        ...

    def retrieve(
        self,
        question: str,
        chunks: list[dict[str, str]],
        embeddings: list[dict[str, Any]],
    ) -> list[dict[str, str | float | int]]:
        ...

    def answer(self, question: str, retrieved_chunks: list[dict[str, Any]]) -> dict[str, Any]:
        ...


def build_rag_engine(config: dict[str, Any], output_dir: str | Path) -> RagEngine:
    """config의 `rag.engine` 값에 맞는 RAG 엔진을 생성합니다."""
    rag_cfg = config.get("rag", {})
    engine_name = str(rag_cfg.get("engine", "local") or "local")
    if engine_name == "local":
        from src.rag.engines.local import LocalRagEngine

        return LocalRagEngine(config=config, output_dir=Path(output_dir))
    if engine_name == "langchain":
        from src.rag.engines.langchain import LangChainRagEngine

        return LangChainRagEngine(config=config, output_dir=Path(output_dir))
    raise NotImplementedError(f"unsupported RAG engine: {engine_name}")
