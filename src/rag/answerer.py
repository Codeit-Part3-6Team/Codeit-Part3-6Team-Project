from __future__ import annotations

import re
from typing import Any

from src.rag.retriever import _tokenize


def build_answer(
    question: str,
    retrieved_chunks: list[dict[str, Any]],
    fallback_message: str = "문서에서 확인하지 못했습니다.",
) -> dict[str, Any]:
    """검색된 chunk를 근거로 추출형 답변과 citation을 만듭니다."""
    if not retrieved_chunks:
        return {
            "question": question,
            "answer": fallback_message,
            "citations": [],
            "status": "not_found",
        }

    best_chunk = retrieved_chunks[0]
    answer_text = _select_sentence(question, str(best_chunk["text"])) or str(best_chunk["text"])
    citations = [
        {
            "chunk_id": best_chunk["chunk_id"],
            "document_id": best_chunk["document_id"],
            "source_path": best_chunk["source_path"],
            "page": best_chunk["page"],
            "section": best_chunk["section"],
        }
    ]
    return {
        "question": question,
        "answer": answer_text,
        "citations": citations,
        "status": "answered",
    }


def _select_sentence(question: str, text: str) -> str:
    """chunk 안에서 질문 token과 가장 많이 겹치는 문장을 고릅니다."""
    sentences = _split_sentences(text)
    if not sentences:
        return text.strip()

    query_tokens = _tokenize(question)
    best_sentence = sentences[0]
    best_score = -1
    for sentence in sentences:
        score = len(query_tokens & _tokenize(sentence))
        if "얼마" in question and "예산" in sentence:
            score += 2
        if "언제" in question and "마감" in sentence:
            score += 2
        if "자격" in question and "자격" in sentence:
            score += 2
        if score > best_score:
            best_sentence = sentence
            best_score = score
    return best_sentence


def _split_sentences(text: str) -> list[str]:
    """정규식 lookbehind 제약을 피하려고 구분자를 보존하는 방식으로 문장을 나눕니다."""
    parts = re.split(r"([.!?。])", text)
    sentences: list[str] = []
    for index in range(0, len(parts), 2):
        sentence = parts[index].strip()
        if not sentence:
            continue
        if index + 1 < len(parts):
            sentence = f"{sentence}{parts[index + 1]}"
        sentences.append(sentence)
    return sentences or [text.strip()]
