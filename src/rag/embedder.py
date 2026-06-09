from __future__ import annotations

import hashlib
import math
import re
from typing import Any


DEFAULT_EMBEDDING_MODEL = "hashing-char-ngram-v1"


def embed_chunks(
    chunks: list[dict[str, str]],
    dimension: int = 64,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> list[dict[str, Any]]:
    """chunk text를 zero-dependency hashing embedding으로 변환합니다."""
    return [
        {
            "chunk_id": chunk["chunk_id"],
            "embedding_model": model_name,
            "vector": embed_text(chunk["text"], dimension=dimension),
        }
        for chunk in chunks
    ]


def embed_text(text: str, dimension: int = 64) -> list[float]:
    """문자 n-gram을 hashing trick으로 고정 길이 vector에 투영합니다.

    실제 프로젝트에서는 sentence-transformers 같은 의미 기반 embedding으로 바꾸면 됩니다.
    지금 구현은 외부 의존성 없이 vector retrieval 산출물 계약을 검증하기 위한 smoke 구현입니다.
    """
    if dimension <= 0:
        raise ValueError("embedding dimension must be positive")

    vector = [0.0 for _ in range(dimension)]
    for feature in _char_ngrams(text):
        index = _stable_hash(feature) % dimension
        vector[index] += 1.0
    return _l2_normalize(vector)


def _char_ngrams(text: str) -> list[str]:
    compact = "".join(re.findall(r"[0-9A-Za-z가-힣]+", text.lower()))
    features: list[str] = []
    for size in (2, 3):
        if len(compact) < size:
            continue
        features.extend(compact[index : index + size] for index in range(len(compact) - size + 1))
    return features or [compact] if compact else []


def _stable_hash(value: str) -> int:
    digest = hashlib.md5(value.encode("utf-8")).hexdigest()
    return int(digest, 16)


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]
