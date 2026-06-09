from __future__ import annotations

from typing import Any

from src.rag.embedder import embed_text
from src.rag.retriever import _score, _tokenize


def retrieve_chunks_by_vector(
    question: str,
    chunks: list[dict[str, str]],
    embeddings: list[dict[str, Any]],
    top_k: int = 3,
    score_threshold: float = 0.0,
    dimension: int = 64,
) -> list[dict[str, str | float | int]]:
    """질문 embedding과 chunk embedding의 cosine similarity로 top-k chunk를 찾습니다."""
    chunk_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    query_vector = embed_text(question, dimension=dimension)

    scored: list[tuple[float, dict[str, str]]] = []
    query_tokens = _tokenize(question)
    for row in embeddings:
        chunk = chunk_by_id.get(str(row["chunk_id"]))
        if not chunk:
            continue
        # hashing vector만으로는 짧은 한국어 질문에서 동점/역전이 생길 수 있어 keyword 힌트를 보정값으로 섞습니다.
        score = _dot(query_vector, row["vector"]) + (_score(query_tokens, question, chunk["text"]) * 0.5)
        if score > score_threshold:
            scored.append((score, chunk))

    scored.sort(key=lambda item: (-item[0], item[1]["chunk_id"]))
    return [_to_retrieval_row(rank, score, chunk) for rank, (score, chunk) in enumerate(scored[:top_k], start=1)]


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _to_retrieval_row(rank: int, score: float, chunk: dict[str, str]) -> dict[str, str | float | int]:
    return {
        "rank": rank,
        "score": round(score, 4),
        "chunk_id": chunk["chunk_id"],
        "document_id": chunk["document_id"],
        "source_path": chunk["source_path"],
        "page": chunk["page_start"],
        "section": chunk["section"],
        "text": chunk["text"],
    }
