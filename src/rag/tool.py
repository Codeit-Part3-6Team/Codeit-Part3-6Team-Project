"""Tool wrapper 모듈.

agent.tools.* config에 정의된 개별 Tool을 retriever + answerer + output_schema
실행 단위로 감쌉니다. Agent Loop는 이 Tool을 dispatch하여 Phase를 실행합니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OnFailure(str, Enum):
    """Tool 실패 시 처리 정책입니다."""
    SKIP = "skip"
    ABORT_PHASE = "abort_phase"
    ABORT_AGENT = "abort_agent"


@dataclass
class ToolResult:
    """개별 Tool 실행 결과입니다.

    Agent State dict에 누적되어 Phase 간 context 전달에 사용됩니다.
    """

    tool_name: str
    phase_name: str = ""
    status: str = "ok"
    answer: str = ""
    structured_output: dict[str, Any] | None = None
    citations: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0
    retry_count: int = 0


@dataclass
class Tool:
    """Agent config의 tools.* 항목을 실행 가능한 단위로 변환한 구조체입니다.

    rag.retriever / rag.answerer 기본값을 상속받고, Tool별 오버라이드를 적용합니다.
    """

    name: str
    description: str
    retriever_cfg: dict[str, Any] = field(default_factory=dict)
    answerer_cfg: dict[str, Any] = field(default_factory=dict)
    prompt_template: str | None = None
    output_schema: Any = None
    rules: list[dict[str, Any]] = field(default_factory=list)
    on_failure: OnFailure = OnFailure.SKIP
    input_from: list[str] = field(default_factory=list)
    full_rag_config: dict[str, Any] | None = None

    def run(
        self,
        question: str,
        chunks: list[dict[str, str]],
        embeddings: list[dict[str, Any]] | None = None,
        state: dict[str, ToolResult] | None = None,
    ) -> ToolResult:
        """retriever + answerer를 순차 실행하여 답변을 생성합니다.

        Args:
            question: Tool에 전달할 질문
            chunks: 검색 대상 chunk 목록
            embeddings: embedding 목록 (vector search 시 필요)
            state: 이전 Phase Tool들의 결과 (input_from, context 전달용)

        Returns:
            ToolResult
        """
        import time
        from src.rag.adapters import build_answerer_adapter, build_retriever_adapter

        started_ms = int(time.time() * 1000)
        errors: list[str] = []

        # 1. retriever 실행
        retrieved: list[dict[str, Any]] = []
        try:
            if self.retriever_cfg:
                retriever = build_retriever_adapter(self.retriever_cfg, {}, self.full_rag_config)
                retrieved = retriever.retrieve(question, chunks, embeddings or [])
        except Exception as exc:
            errors.append(f"retrieve: {exc}")
            if self.on_failure in (OnFailure.ABORT_PHASE, OnFailure.ABORT_AGENT):
                return ToolResult(
                    tool_name=self.name,
                    status="failed",
                    errors=errors,
                    started_at=str(started_ms),
                    finished_at=str(int(time.time() * 1000)),
                    duration_ms=int(time.time() * 1000) - started_ms,
                )

        # 2. answerer 실행
        answer_payload: dict[str, Any] = {}
        try:
            answerer = build_answerer_adapter(self.answerer_cfg)
            if self.output_schema is not None and hasattr(answerer, "output_schema"):
                answerer.output_schema = self.output_schema
            if self.prompt_template and hasattr(answerer, "prompt_template"):
                answerer.prompt_template = self.prompt_template
            answer_payload = answerer.answer(question, retrieved)
        except Exception as exc:
            errors.append(f"answer: {exc}")
            answer_payload = {
                "question": question,
                "answer": self.answerer_cfg.get("fallback_message", "문서에서 확인하지 못했습니다."),
                "citations": [],
                "status": "not_found",
            }

        finished_ms = int(time.time() * 1000)
        return ToolResult(
            tool_name=self.name,
            status="ok" if not errors else "partial",
            answer=str(answer_payload.get("answer", "")),
            structured_output=None,
            citations=answer_payload.get("citations", []),
            errors=errors,
            started_at=str(started_ms),
            finished_at=str(finished_ms),
            duration_ms=finished_ms - started_ms,
        )


def build_tool_from_config(
    name: str,
    tool_cfg: dict[str, Any],
    default_retriever: dict[str, Any] | None = None,
    default_answerer: dict[str, Any] | None = None,
    agent_cfg: dict[str, Any] | None = None,
    full_rag_config: dict[str, Any] | None = None,
) -> Tool:
    """agent.tools.* config 항목으로 Tool 인스턴스를 생성합니다.

    Args:
        name: Tool 이름
        tool_cfg: tools.* 하위 설정
        default_retriever: rag.retriever 기본값
        default_answerer: rag.answerer 기본값
        agent_cfg: agent 최상위 설정 (schemas 검색용)
        full_rag_config: rag 전체 설정 (scoring 추출용)

    Returns:
        Tool 인스턴스
    """
    retriever_cfg = dict(default_retriever or {})
    retriever_cfg.update(tool_cfg.get("retriever", {}))

    answerer_cfg = dict(default_answerer or {})
    answerer_cfg.update(tool_cfg.get("answerer", {}))

    output_schema = None
    schema_key = answerer_cfg.pop("output_schema", None)
    if schema_key:
        from src.rag.schema_parser import resolve_output_schema

        schema_config = {"agent": agent_cfg} if agent_cfg else {}
        output_schema = resolve_output_schema(schema_config, schema_key)

    on_failure_str = tool_cfg.get("on_failure", "skip")
    try:
        on_failure = OnFailure(on_failure_str)
    except ValueError:
        on_failure = OnFailure.SKIP

    return Tool(
        name=name,
        description=str(tool_cfg.get("description", "")),
        retriever_cfg=retriever_cfg,
        answerer_cfg=answerer_cfg,
        prompt_template=answerer_cfg.get("prompt_template") or None,
        output_schema=output_schema,
        rules=tool_cfg.get("rules", {}).get("patterns", []),
        on_failure=on_failure,
        input_from=tool_cfg.get("input_from", []),
        full_rag_config=full_rag_config,
    )
