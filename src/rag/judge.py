"""LLM-as-Judge 공통 모듈.

평가(evaluation)와 에이전트(agent)에서 공통으로 사용하는 판단 로직.
"""

from __future__ import annotations

import os
from typing import Any

DEFAULT_BINARY_TEMPLATE = (
    '다음 expected_answer와 actual_answer가 의미상 같은 내용이면 "true", '
    '다른 내용이면 "false"라고만 답하세요.\n\n'
    "expected_answer: {expected}\n"
    "actual_answer: {actual}\n\n"
    "같은 의미인가요? (true/false)"
)


def judge_binary(
    expected: str,
    actual: str,
    model_name: str = "gpt-4o-mini",
    provider: str = "openai",
    api_key_env: str = "OPENAI_API_KEY",
    template: str | None = None,
) -> bool:
    """expected와 actual이 의미상 같은 답인지 LLM으로 판단.

    Args:
        expected: 정답 텍스트.
        actual: 모델이 생성한 답변.
        model_name: 판단에 사용할 LLM 모델.
        provider: LLM provider (openai, ollama).
        api_key_env: API 키가 등록된 환경변수 이름.
        template: 판단 프롬프트 템플릿. None이면 기본 binary template 사용.

    Returns:
        의미상 같으면 True. 호출 실패 시 False.
    """
    from langchain_core.messages import HumanMessage

    api_key = os.environ.get(api_key_env, "")
    prompt_template = template or DEFAULT_BINARY_TEMPLATE
    prompt = prompt_template.format(expected=expected, actual=actual)

    try:
        if provider == "ollama":
            from langchain_ollama import ChatOllama

            judge = ChatOllama(model=model_name, temperature=0)
        else:
            from langchain_openai import ChatOpenAI

            judge = ChatOpenAI(model=model_name, temperature=0, openai_api_key=api_key or None)

        result = judge.invoke([HumanMessage(content=prompt)])
        result_text = getattr(result, "content", str(result)).strip().lower()
        return bool(re.search(r"\btrue\b", result_text))
    except Exception:
        return False


def judge_binary_from_config(
    config: dict[str, Any],
    expected: str,
    actual: str,
) -> bool:
    """config의 evaluation.llm_judge 설정을 읽어 판단.

    평가 전용 wrapper. config 구조:
        evaluation:
          llm_judge:
            enabled: true
            model_name: gpt-5-mini
            prompt: |      # optional, template override
              ...
    """
    judge_cfg = config.get("evaluation", {}).get("llm_judge", {})
    return judge_binary(
        expected=expected,
        actual=actual,
        model_name=judge_cfg.get("model_name", "gpt-4o-mini"),
        provider=judge_cfg.get("provider", "openai"),
        api_key_env=judge_cfg.get("api_key_env", "OPENAI_API_KEY"),
        template=judge_cfg.get("prompt"),
    )
