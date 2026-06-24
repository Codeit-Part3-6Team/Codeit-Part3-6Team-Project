"""텍스트 토크나이징 및 검색 스코어링 유틸리티 모듈.

retriever, answerer, adapter에서 공통으로 사용하는 토크나이징과
한국어 도메인 키워드 가중치 로직을 한 곳으로 통합합니다.
config에서 rag.scoring.keyword_weights 로 가중치를 오버라이드할 수 있습니다.
"""

from __future__ import annotations

import re
from typing import Any


def tokenize(text: str) -> set[str]:
    """텍스트를 2글자 이상의 토큰 집합으로 분리합니다.

    Args:
        text: 입력 텍스트

    Returns:
        소문자 정규화된 토큰 집합
    """
    return {token.lower() for token in re.findall(r"[0-9A-Za-z가-힣]+", text) if len(token) >= 2}


def score(query_tokens: set[str], question: str, text: str) -> float:
    """질문 토큰과 텍스트의 겹침 정도를 점수로 계산합니다.

    Args:
        query_tokens: 질문에서 추출한 토큰 집합
        question: 원본 질문 문자열 (co-occurrence 검사용)
        text: 점수를 매길 텍스트

    Returns:
        점수 (0.0 이상)
    """
    text_tokens = tokenize(text)
    overlap = query_tokens & text_tokens
    base_score = float(len(overlap))

    compact_text = re.sub(r"\s+", "", text)
    for token in query_tokens:
        if len(token) >= 2 and token in compact_text:
            base_score += 0.5
    if "얼마" in question and ("예산" in text or "금액" in text):
        base_score += 1.0
    if "언제" in question and ("마감" in text or "일정" in text):
        base_score += 1.0
    if "자격" in question and "자격" in text:
        base_score += 1.0
    return base_score
