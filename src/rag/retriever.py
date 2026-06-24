from __future__ import annotations

import re

from src.rag.scoring import score as _score, tokenize as _tokenize


def retrieve_chunks(
    question: str,
    chunks: list[dict[str, str]],
    top_k: int = 3,
    score_threshold: float = 0.0,
) -> list[dict[str, str | float | int]]:
    """질문과 chunk의 단어 겹침을 기준으로 top-k 검색 결과를 반환합니다."""
    query_tokens = _tokenize(question)
    scored: list[tuple[float, dict[str, str]]] = []
    for chunk in chunks:
        chunk_score = _score(query_tokens, question, chunk["text"])
        if chunk_score > score_threshold:
            scored.append((chunk_score, chunk))

    scored.sort(key=lambda item: (-item[0], item[1]["chunk_id"]))
    results: list[dict[str, str | float | int]] = []
    for rank, (chunk_score, chunk) in enumerate(scored[:top_k], start=1):
        results.append(
            {
                "rank": rank,
                "score": round(chunk_score, 4),
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["document_id"],
                "source_path": chunk["source_path"],
                "page": chunk["page_start"],
                "section": chunk["section"],
                "text": chunk["text"],
            }
        )
    return results
