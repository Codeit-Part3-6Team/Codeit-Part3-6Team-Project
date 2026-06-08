from __future__ import annotations

import re


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
        score = _score(query_tokens, question, chunk["text"])
        if score > score_threshold:
            scored.append((score, chunk))

    scored.sort(key=lambda item: (-item[0], item[1]["chunk_id"]))
    results: list[dict[str, str | float | int]] = []
    for rank, (score, chunk) in enumerate(scored[:top_k], start=1):
        results.append(
            {
                "rank": rank,
                "score": round(score, 4),
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["document_id"],
                "source_path": chunk["source_path"],
                "page": chunk["page_start"],
                "section": chunk["section"],
                "text": chunk["text"],
            }
        )
    return results


def _score(query_tokens: set[str], question: str, text: str) -> float:
    """작은 smoke test용 점수입니다. 실제 프로젝트에서는 embedding 검색으로 교체합니다."""
    text_tokens = _tokenize(text)
    overlap = query_tokens & text_tokens
    score = float(len(overlap))

    # 한국어 질문은 조사/어미 때문에 정확히 같은 token이 적을 수 있어 substring 힌트를 조금 더합니다.
    compact_text = re.sub(r"\s+", "", text)
    for token in query_tokens:
        if len(token) >= 2 and token in compact_text:
            score += 0.5
    if "얼마" in question and ("예산" in text or "금액" in text):
        score += 1.0
    if "언제" in question and ("마감" in text or "일정" in text):
        score += 1.0
    if "자격" in question and "자격" in text:
        score += 1.0
    return score


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[0-9A-Za-z가-힣]+", text) if len(token) >= 2}
