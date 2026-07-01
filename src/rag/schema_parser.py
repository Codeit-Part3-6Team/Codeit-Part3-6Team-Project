"""config 기반 Pydantic output schema 동적 생성 모듈.

agent.tools.*.output_schema에 참조된 스키마 이름을 Pydantic BaseModel로 변환합니다.
BUILTIN_SCHEMAS에 미리 정의된 스키마를 사용하거나, config의 agent.schemas 섹션에서
inline 정의를 읽어 동적 생성합니다.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, create_model

# 기본 제공 스키마. config에서 output_schema: facts_schema 로 참조
BUILTIN_SCHEMAS: dict[str, dict[str, Any]] = {
    "facts_schema": {
        "예산": (str, ...),
        "일정": (str, ...),
        "자격요건": (list[str], ...),
        "제출서류": (list[str], ...),
        "발주기관": (str, None),
        "사업명": (str, ...),
    },
    "decision_schema": {
        "참여여부": (bool, ...),
        "근거": (str, ...),
        "리스크": (list[str], ...),
        "제안가_범위": (str | None, None),
    },
    "clause_severity_schema": {
        "조항명": (str, ...),
        "심각도": (int, ...),
        "설명": (str, ...),
    },
}


def build_output_schema(schema_name: str) -> type[BaseModel]:
    """미리 정의된 스키마 이름으로 Pydantic 모델을 생성합니다.

    Args:
        schema_name: BUILTIN_SCHEMAS에 등록된 스키마 이름

    Returns:
        생성된 Pydantic BaseModel 클래스
    """
    if schema_name not in BUILTIN_SCHEMAS:
        available = list(BUILTIN_SCHEMAS)
        raise KeyError(
            f"output_schema '{schema_name}'은 등록되지 않은 스키마입니다. "
            f"사용 가능: {available}"
        )
    return create_model(schema_name, **BUILTIN_SCHEMAS[schema_name])


def build_inline_schema(schema_name: str, fields: dict[str, Any]) -> type[BaseModel]:
    """config의 agent.schemas 섹션에서 정의된 필드로 Pydantic 모델을 생성합니다.

    Args:
        schema_name: 스키마 이름
        fields: {"필드명": 타입, ...} 형태의 필드 정의

    Returns:
        생성된 Pydantic BaseModel 클래스
    """
    return create_model(schema_name, **fields)


def resolve_output_schema(config: dict[str, Any], schema_key: str | None) -> type[BaseModel] | None:
    """config에서 output_schema 참조를 해석하여 Pydantic 모델을 반환합니다.

    우선순위:
    1. config.agent.schemas.{schema_key}.fields → inline 스키마
    2. BUILTIN_SCHEMAS → 미리 정의된 스키마

    Args:
        config: agent 최상위 config dict (agent.schemas 검색)
        schema_key: output_schema 값 (문자열 스키마 이름)

    Returns:
        Pydantic 모델, 또는 schema_key가 None이면 None
    """
    if not schema_key:
        return None

    agent_cfg = config.get("agent", {})
    schemas = agent_cfg.get("schemas", {})
    if schema_key in schemas:
        fields_def = schemas[schema_key].get("fields", {})
        if fields_def:
            return build_inline_schema(schema_key, fields_def)

    return build_output_schema(schema_key)
