"""프롬프트 템플릿 생성 모듈.

langchain engine과 adapter가 동일한 기본 프롬프트를 사용하도록 통합합니다.
config의 rag.answerer.prompt로 오버라이드 가능하며,
{context}와 {question} 플레이스홀더를 치환합니다.
"""

from __future__ import annotations

from typing import Any

# langchain.py _build_prompt와 동일한 기본 템플릿 (fix/answer-quality 버전)
DEFAULT_PROMPT_TEMPLATE = """너는 RFP 문서 분석 도우미다. 아래 근거에 있는 내용만 사용해서 한국어로 답하라.
근거에 없는 내용은 추측하지 말고 '문서에서 확인하지 못했습니다.'라고 답하라.
답변 말미에는 반드시 사용한 근거 번호를 [사용근거: 1,3] 형식으로 표기하라.

{context}

질문: {question}"""


def build_prompt(
    question: str,
    retrieved_chunks: list[dict[str, Any]],
    template: str | None = None,
) -> str:
    """검색된 chunk를 context로 묶어 프롬프트를 생성합니다.

    Args:
        question: 사용자 질문
        retrieved_chunks: 검색된 chunk 목록
        template: 프롬프트 템플릿. {context}와 {question} 플레이스홀더 사용.
                  None이면 DEFAULT_PROMPT_TEMPLATE 사용.

    Returns:
        완성된 프롬프트 문자열
    """
    context = "\n\n".join(
        f"[근거 {index}]\nchunk_id: {chunk.get('chunk_id', '')}\n{chunk.get('text', '')}"
        for index, chunk in enumerate(retrieved_chunks, start=1)
    )
    fmt = template if template is not None else DEFAULT_PROMPT_TEMPLATE
    return fmt.format(context=context, question=question)
