"""텍스트 토크나이징 및 검색 스코어링 유틸리티 모듈.

retriever, answerer, adapter에서 공통으로 사용하는 토크나이징과
한국어 도메인 키워드 가중치 로직을 한 곳으로 통합합니다.
config에서 rag.scoring.keyword_weights 와 rag.scoring.co_occurrence_bonus 로
가중치를 오버라이드할 수 있습니다.
"""

from __future__ import annotations

import re
from typing import Any

# 기본 키워드 가중치 (retriever.py/answerer.py 원본과 동일)
DEFAULT_SUBSTRING_BONUS = 0.5
DEFAULT_CO_OCCURRENCE_BONUS = 1.0
DEFAULT_CO_OCCURRENCE_RULES: list[tuple[str, list[str]]] = [
    ("얼마", ["예산", "금액"]),
    ("언제", ["마감", "일정"]),
    ("자격", ["자격"]),
]


def tokenize(text: str) -> set[str]:
    """텍스트를 2글자 이상의 토큰 집합으로 분리합니다.

    Args:
        text: 입력 텍스트

    Returns:
        소문자 정규화된 토큰 집합
    """
    return {token.lower() for token in re.findall(r"[0-9A-Za-z가-힣]+", text) if len(token) >= 2}


def score(
    query_tokens: set[str],
    question: str,
    text: str,
    *,
    keyword_weights: dict[str, float] | None = None,
    co_occurrence_bonus: float | None = None,
    substring_bonus: float | None = None,
) -> float:
    """질문 토큰과 텍스트의 겹침 정도를 점수로 계산합니다.

    Args:
        query_tokens: 질문에서 추출한 토큰 집합
        question: 원본 질문 문자열 (co-occurrence 검사용)
        text: 점수를 매길 텍스트
        keyword_weights: 키워드별 가중치 오버라이드 ({'예산': 2.0, ...})
        co_occurrence_bonus: co-occurrence 보너스 값 (기본 1.0)
        substring_bonus: substring 매칭 보너스 값 (기본 0.5)

    Returns:
        점수 (0.0 이상)
    """
    text_tokens = tokenize(text)
    overlap = query_tokens & text_tokens
    base_score = float(len(overlap))

    sub_bonus = substring_bonus if substring_bonus is not None else DEFAULT_SUBSTRING_BONUS
    compact_text = re.sub(r"\s+", "", text)
    for token in query_tokens:
        if len(token) >= 2 and token in compact_text:
            base_score += sub_bonus

    co_bonus = co_occurrence_bonus if co_occurrence_bonus is not None else DEFAULT_CO_OCCURRENCE_BONUS
    weights = keyword_weights or {}

    for q_keyword, text_keywords in DEFAULT_CO_OCCURRENCE_RULES:
        bonus_value = weights.get(q_keyword, co_bonus)
        if q_keyword in question:
            for tk in text_keywords:
                if tk in text:
                    base_score += bonus_value
                    break
    return base_score


def build_keyword_weights(config: dict[str, Any] | None) -> dict[str, float]:
    """config의 rag.scoring.keyword_weights를 읽어 가중치 dict를 반환합니다.

    Args:
        config: rag 설정 dict 또는 None

    Returns:
        {'예산': 2.0, '일정': 1.5, ...} 형태의 가중치 dict.
        config가 없거나 keyword_weights가 없으면 빈 dict.
    """
    if not config:
        return {}
    scoring = config.get("rag", {}).get("scoring", {})
    raw = scoring.get("keyword_weights", {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): float(v) for k, v in raw.items()}


def build_scoring_kwargs(config: dict[str, Any] | None) -> dict[str, Any]:
    """config에서 scoring 관련 kwargs를 추출합니다.

    Args:
        config: rag 설정 dict 또는 None

    Returns:
        keyword_weights, co_occurrence_bonus, substring_bonus가 포함된 dict.
    """
    if not config:
        return {}
    scoring = config.get("rag", {}).get("scoring", {})
    kwargs: dict[str, Any] = {}
    if "keyword_weights" in scoring:
        kwargs["keyword_weights"] = build_keyword_weights(config)
    if "co_occurrence_bonus" in scoring:
        kwargs["co_occurrence_bonus"] = float(scoring["co_occurrence_bonus"])
    if "substring_bonus" in scoring:
        kwargs["substring_bonus"] = float(scoring["substring_bonus"])
    return kwargs
