"""Agent 챗봇 모듈.

config의 agent.chatbot.enabled: true일 때, LLM이 Tool description을 읽고
사용자 질문에 적합한 Tool을 동적으로 선택하여 실행합니다.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.rag.tool import Tool, ToolResult

logger = logging.getLogger("rag.chatbot")


@dataclass(frozen=True)
class ChatPresentation:
    """챗봇 질문 유형과 출력 형식을 나타냅니다."""

    answer_type: str
    tool_name: str | None
    fields: tuple[str, ...]


FIELD_ALIASES = {
    "사업예산": ("사업예산", "예산", "사업금액", "사업 금액"),
    "발주기관": ("발주기관", "발주 기관", "기관"),
    "사업명": ("사업명", "사업 명", "문서명"),
    "사업기간": ("사업기간", "사업 기간", "계약기간", "용역기간"),
    "제출마감": ("제출마감", "제출 마감", "입찰마감", "마감일"),
    "제출서류": ("제출서류", "제출 서류", "필요서류", "구비서류"),
    "참가자격": ("참가자격", "참가 자격", "자격요건", "참가요건", "참여조건"),
    "평가기준": ("평가기준", "평가 기준", "평가항목", "평가 항목", "배점"),
    "리스크": ("리스크", "위험", "주의사항", "제안_주의사항"),
    "요약": ("요약", "사업개요", "사업 개요", "사업범위", "기대효과", "추진목표"),
}


def _has_batchim(word: str) -> bool:
    """한글 마지막 글자에 받침이 있는지 확인합니다."""
    if not word:
        return False
    last = word[-1]
    if not ("가" <= last <= "힣"):
        return False
    return (ord(last) - 0xAC00) % 28 != 0


class ChatbotRunner:
    """LLM 기반 Tool 선택 + 실행 챗봇입니다.

    AgentRunner의 Tool dispatch를 재활용하며, Phase DAG 없이
    사용자 입력에 따라 단일 Tool을 동적으로 선택해 실행합니다.
    """

    def __init__(
        self,
        tools: dict[str, Tool],
        tool_selection_model: str = "gpt-4o-mini",
        tool_selection_provider: str = "openai",
        system_prompt: str | None = None,
        max_history: int = 10,
        cache_ttl: int = 300,
    ):
        self.tools = tools
        self.tool_selection_model = tool_selection_model
        self.tool_selection_provider = tool_selection_provider
        self.system_prompt = system_prompt or (
            "너는 RFP 입찰 전문 컨설턴트 'IT'S MINE'이다.\n"
            "사용자의 질문을 이해하고 적합한 분석 도구를 선택하여 자연스러운 문장으로 답변하라.\n"
            "도구 선택은 JSON으로 하라: {\"tool\": \"도구명\", \"question\": \"도구에 전달할 질문\"}\n"
            "도구가 필요 없는 일반 대화면 {\"tool\": null, \"answer\": \"직접 답변\"} 으로 응답하라."
        )
        self.max_history = max_history
        self.max_retries = 2
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self.history: list[dict[str, str]] = []
        self.state: dict[str, ToolResult] = {}
        self.current_context: dict[str, str] = {}
        self.chunks: list[dict[str, str]] = []
        self.embeddings: list[dict[str, Any]] = []
        self._output_dir: Path | None = None
        self._use_chroma: bool = False
        self._run_id: str | None = None
        self._selected_doc_ids: list[str] = []

    def load_document_context(self, output_dir: str | Path | None) -> None:
        """CSV/JSONL에서 문서 context를 로딩하거나 ChromaDB에 연결합니다."""
        if output_dir is None:
            return

        from pathlib import Path
        dir_path = Path(output_dir)
        self._output_dir = dir_path

        # ChromaDB vector_store 설정 확인
        # retriever.method가 chroma이면 chunks/embeddings 로딩을 건너뜀
        for tool in self.tools.values():
            if tool.retriever_cfg.get("method") == "chroma":
                persist_path = tool.retriever_cfg.get("persist_dir", "")
                if persist_path:
                    p = Path(persist_path)
                    if not p.is_absolute():
                        persist_path = str(dir_path / persist_path)
                    tool.retriever_cfg["persist_dir"] = persist_path
                self._use_chroma = True

        if self._use_chroma:
            return

        import csv
        import json

        chunks_path = dir_path / "chunks.csv"
        if chunks_path.exists():
            with open(chunks_path, "r", encoding="utf-8-sig") as fh:
                for row in csv.DictReader(fh):
                    self.chunks.append(dict(row))
        embeddings_path = dir_path / "embeddings.jsonl"
        if embeddings_path.exists():
            with open(embeddings_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        self.embeddings.append(json.loads(line))


    def _run_agent_loop(self, user_input: str, max_iterations: int = 3):
        self._add_history('user', user_input)
        tool_history = []
        run_state: dict[str, ToolResult] = {}

        for iteration in range(max_iterations):
            tool_name, refined_question = self._select_tool(user_input)
            if tool_name is None:
                reply = (
                    refined_question
                    if refined_question and refined_question != user_input
                    else "어떤 분석을 도와드릴까요? 예산, 요구사항, 비교, 참여 가능 여부 등에 대해 질문해 주세요."
                )
                self._add_history('assistant', reply)
                return {
                    'reply': reply,
                    'tool_used': None,
                    'tool_result': None,
                    'structured_output': None,
                    'citations': [],
                }
            tool = self.tools.get(tool_name)
            if tool is None:
                available = ", ".join(self.tools.keys())
                reply = (
                    f"죄송합니다. '{tool_name}' 기능은 아직 준비되지 않았습니다.\n"
                    f"사용 가능한 기능: {available}"
                )
                self._add_history('assistant', reply)
                return {
                    'reply': reply,
                    'tool_used': None,
                    'tool_result': None,
                    'structured_output': None,
                    'citations': [],
                }

            for dep_name in tool.input_from:
                if dep_name not in run_state:
                    dep_tool = self.tools.get(dep_name)
                    if dep_tool:
                        dep_result = self._run_tool_with_retry(dep_tool, user_input, run_state)
                        run_state[dep_name] = dep_result

            result = self._run_tool_with_retry(tool, refined_question, run_state)
            run_state[tool_name] = result
            tool_history.append(tool_name)
            self.current_context["last_tool"] = tool_name
            self.current_context["last_question"] = user_input
            self.current_context["last_answer"] = result.answer[:300] if result.answer else ""

            is_complete, next_tool = self._evaluate_result(user_input, tool_name, result, iteration, max_iterations)
            if is_complete:
                # 질문 실행 결과를 self.state에 반영
                self.state.update(run_state)
                reply = self._format_chat_result(user_input, result)
                self._add_history('assistant', reply)
                return {
                    'reply': reply,
                    'tool_used': tool_history,
                    'tool_result': {'status': result.status, 'answer': result.answer[:500], 'citations_count': len(result.citations), 'duration_ms': result.duration_ms},
                    'structured_output': result.structured_output,
                    'citations': [dict(c) for c in result.citations],
                }
            if next_tool and next_tool in self.tools:
                continue
        return None

    def _evaluate_result(self, user_input, tool_name, result, iteration, max_iterations):
        if result.status == 'ok' and result.answer and '확인하지 못했습니다' not in result.answer:
            return True, None
        if iteration >= max_iterations - 1:
            return True, None
        return False, next(iter(self.tools))

    def _format_tool_result(self, result):
        if result.answer and result.answer != '(응답 없음)':
            out = result.answer
        elif result.structured_output:
            lines = []
            for k, v in result.structured_output.items():
                if isinstance(v, list):
                    lines.append(f'{k}: ' + ', '.join(str(x) for x in v))
                else:
                    lines.append(f'{k}: {v}')
            out = '\n'.join(lines)
        else:
            out = result.answer or '(응답 없음)'
        if result.citations:
            source_lines = []
            for c in result.citations[:5]:
                page = c.get('page', c.get('page_start', '?'))
                section = c.get('section', '')
                chunk_id = c.get('chunk_id', '')
                label = f'p.{page} ({section})' if section else f'p.{page}'
                source_lines.append(f'📄 {label} chunk_id: {chunk_id}')
            out += '\n\n[출처]\n' + '\n'.join(source_lines)
        return out

    def _format_chat_result(self, user_input: str, result: ToolResult) -> str:
        """챗봇 화면에 맞게 ToolResult를 자연스러운 답변으로 변환합니다."""
        if result.structured_output:
            return self._format_structured_chat_reply(user_input, result.structured_output, result.answer)
        return self._strip_source_block(self._format_tool_result(result))

    def _format_structured_chat_reply(
        self,
        user_input: str,
        structured: dict[str, Any],
        natural_reply: str = "",
    ) -> str:
        presentation = self._classify_chat_presentation(user_input)
        projected = self._project_structured_fields(structured, presentation.fields)

        # scalar 타입: natural_reply가 schema dump가 아니고 핵심 값이 포함되어 있으면 그대로 사용
        if presentation.answer_type == "scalar" and projected:
            stripped = self._strip_source_block(natural_reply).strip()
            _, value = projected[0]
            value_text = str(self._format_scalar_value(value))
            is_natural = stripped.count(":") <= 1 and len(stripped) < 200
            if is_natural and stripped and value_text in stripped:
                return stripped

        if projected:
            return self._render_projected_answer(presentation.answer_type, projected)

        # 질문 의도에 맞는 필드가 비었으면 문서에 없다고 안내
        if presentation.answer_type in ("scalar", "list", "checklist", "evaluation"):
            missing_label = presentation.fields[0] if presentation.fields else "해당 정보"
            return f"문서에서 {missing_label}을(를) 확인하지 못했습니다."

        natural_reply = self._strip_source_block(natural_reply).strip()
        if natural_reply and natural_reply != "(응답 없음)":
            return natural_reply

        fallback_fields = self._project_structured_fields(
            structured,
            ("사업예산", "발주기관", "사업명", "사업기간", "제출마감", "참가자격", "제출서류", "평가기준"),
        )
        if fallback_fields:
            return self._render_projected_answer("general", fallback_fields)
        return "문서에서 확인하지 못했습니다."

    def _classify_chat_presentation(self, user_input: str) -> ChatPresentation:
        """사용자 질문을 챗봇 출력 유형으로 분류합니다."""
        text = user_input.lower()
        if any(token in text for token in ("제출", "서류", "구비")):
            return ChatPresentation("list", "extract_requirements", ("제출서류",))
        if any(token in text for token in ("참가", "자격", "요건", "참여조건")):
            return ChatPresentation("checklist", "extract_requirements", ("참가자격",))
        if any(token in text for token in ("평가", "배점", "기준")):
            return ChatPresentation("evaluation", "extract_requirements", ("평가기준",))
        if any(token in text for token in ("비교", "차이", "대조")):
            return ChatPresentation("comparison", "compare_rfps", ("사업명", "사업예산", "사업기간", "참가자격", "평가기준"))
        if any(token in text for token in ("참여", "가능", "할만", "리스크", "위험", "특이사항")):
            return ChatPresentation("judgement", "decide_participation", ("리스크", "참가자격", "평가기준", "제출서류"))
        if any(token in text for token in ("요약", "중요", "핵심", "사업 내용", "뭐가")):
            return ChatPresentation("summary", "extract_facts", ("요약", "사업명", "발주기관", "사업예산", "사업기간"))
        if any(token in text for token in ("예산", "금액", "얼마")):
            return ChatPresentation("scalar", "extract_facts", ("사업예산",))
        if "발주" in text:
            return ChatPresentation("scalar", "extract_facts", ("발주기관",))
        if "사업명" in text or "문서명" in text:
            return ChatPresentation("scalar", "extract_facts", ("사업명",))
        if any(token in text for token in ("마감", "언제", "일정")):
            return ChatPresentation("scalar", "extract_facts", ("제출마감", "사업기간"))
        if "기간" in text:
            return ChatPresentation("scalar", "extract_facts", ("사업기간",))
        return ChatPresentation("general", None, ())

    def _project_structured_fields(
        self,
        structured: dict[str, Any],
        desired_fields: tuple[str, ...],
    ) -> list[tuple[str, Any]]:
        projected: list[tuple[str, Any]] = []
        used_keys: set[str] = set()
        for field in desired_fields:
            aliases = FIELD_ALIASES.get(field, (field,))
            for key, value in structured.items():
                if key in used_keys:
                    continue
                normalized = str(key).replace(" ", "")
                if any(normalized == alias.replace(" ", "") for alias in aliases):
                    if not self._is_missing_value(value):
                        projected.append((field, value))
                        used_keys.add(key)
                    break
        return projected

    def _render_projected_answer(self, answer_type: str, fields: list[tuple[str, Any]]) -> str:
        if answer_type == "scalar":
            label, value = fields[0]
            particle = "은" if _has_batchim(label) else "는"
            return f"{label}{particle} {self._format_scalar_value(value)}입니다."
        if answer_type in {"list", "checklist"}:
            return self._render_table_answer(answer_type, fields)
        if answer_type in {"evaluation", "comparison"}:
            return self._render_bullet_answer(answer_type, fields)
        if answer_type == "judgement":
            return self._render_judgement_answer(fields)
        if answer_type == "summary":
            return self._render_summary_answer(fields)
        return self._render_general_answer(fields)

    def _render_table_answer(self, answer_type: str, fields: list[tuple[str, Any]]) -> str:
        title_by_type = {
            "list": "문서에서 확인한 목록입니다.",
            "checklist": "문서에서 확인한 체크리스트입니다.",
            "evaluation": "문서에서 확인한 평가 관련 항목입니다.",
            "comparison": "문서에서 확인한 비교 항목입니다.",
        }
        lines = [title_by_type.get(answer_type, "문서에서 확인한 내용입니다."), "", "| 구분 | 내용 |", "|---|---|"]
        for label, value in fields:
            for item in self._value_items(value):
                lines.append(f"| {label} | {self._escape_table_cell(item)} |")
        return "\n".join(lines)

    def _render_bullet_answer(self, answer_type: str, fields: list[tuple[str, Any]]) -> str:
        title_by_type = {
            "evaluation": "문서에서 확인한 평가 기준입니다.",
            "comparison": "문서에서 확인한 비교 항목입니다.",
        }
        lines = [title_by_type.get(answer_type, "문서에서 확인한 내용입니다."), ""]
        for label, value in fields:
            lines.append(f"**{label}**")
            for item in self._value_items(value):
                lines.append(f"- {item}")
            lines.append("")
        return "\n".join(lines)

    def _render_summary_answer(self, fields: list[tuple[str, Any]]) -> str:
        lines = ["핵심 내용은 아래와 같습니다."]
        for label, value in fields:
            for item in self._value_items(value):
                lines.append(f"- {label}: {item}")
        return "\n".join(lines)

    def _render_judgement_answer(self, fields: list[tuple[str, Any]]) -> str:
        lines = ["문서 기준으로는 아래 항목을 먼저 확인해야 합니다."]
        for label, value in fields:
            for item in self._value_items(value):
                lines.append(f"- {label}: {item}")
        lines.append("- 최종 참여 가능 여부는 원문 자격요건과 제출서류를 함께 대조해 판단하세요.")
        return "\n".join(lines)

    def _render_general_answer(self, fields: list[tuple[str, Any]]) -> str:
        lines = ["문서에서 확인한 내용은 아래와 같습니다."]
        for label, value in fields:
            for item in self._value_items(value):
                lines.append(f"- {label}: {item}")
        return "\n".join(lines)

    def _value_items(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if not self._is_missing_value(item)]
        if isinstance(value, dict):
            return [f"{key}: {item}" for key, item in value.items() if not self._is_missing_value(item)]
        return [str(value)]

    def _format_scalar_value(self, value: Any) -> str:
        if isinstance(value, list):
            return ", ".join(self._value_items(value))
        if isinstance(value, dict):
            return "; ".join(self._value_items(value))
        return str(value)

    def _escape_table_cell(self, value: str) -> str:
        return str(value).replace("|", "\\|").replace("\n", "<br>")

    def _is_missing_value(self, value: Any) -> bool:
        if value in (None, "", [], {}):
            return True
        if isinstance(value, str):
            return value.strip() in {"", "명시되지 않음", "(응답 없음)"}
        return False

    def _strip_source_block(self, reply: str) -> str:
        marker = "\n\n[출처]\n"
        if marker in reply:
            return reply.split(marker, 1)[0].rstrip()
        return reply

    def chat(self, user_input: str) -> dict[str, Any]:
        """사용자 입력을 받아 Tool 선택 → 실행 → 응답을 반환합니다.

        Args:
            user_input: 사용자 메시지

        Returns:
            {"reply": str, "tool_used": str | None, "tool_result": dict | None}
        """
        if not self._is_rfp_question(user_input):
            reply = (
                "저는 RFP 문서 전문 분석 도우미입니다.\n"
                "문서 요약, 요구사항 추출, 비교 분석, 참여 판단에 대해 질문해 주세요."
            )
            self._add_history("assistant", reply)
            return {"reply": reply, "tool_used": None, "tool_result": None}

        cache_key = (user_input.strip(), tuple(sorted(self._selected_doc_ids or [])))
        if cache_key in self._cache:
            ts, cached = self._cache[cache_key]
            if time.time() - ts < self.cache_ttl:
                self._add_history("assistant", cached.get("reply", ""))
                return dict(cached)
            del self._cache[cache_key]

        result = self._run_agent_loop(user_input, max_iterations=3)
        if result:
            self._cache[cache_key] = (time.time(), dict(result))
            return result

        reply = "어떤 분석을 도와드릴까요? 예산, 요구사항, 비교, 참여 가능 여부 등에 대해 질문해 주세요."
        self._add_history("assistant", reply)
        return {"reply": reply, "tool_used": None, "tool_result": None}

    def _is_rfp_question(self, user_input: str) -> bool:
        """질문이 RFP/입찰 문서 분석 도메인에 속하는지 키워드 기반으로 1차 판단합니다."""
        rfp_keywords = [
            "rfp", "입찰", "제안", "공고", "사업", "예산", "발주", "마감",
            "자격", "서류", "평가", "계약", "낙찰", "과업", "용역",
            "요약", "비교", "분석", "추출", "참여", "요구사항",
            "체크리스트", "리스크", "검색", "찾아",
        ]
        text = user_input.lower()
        return any(kw in text for kw in rfp_keywords)

    def _select_tool(self, user_input: str) -> tuple[str | None, str]:
        """LLM에게 Tool 목록을 보여주고 선택하게 합니다."""
        routed = self._select_tool_by_presentation(user_input)
        if routed:
            self._add_history("user", user_input)
            return routed, user_input

        tool_descriptions = "\n".join(
            f"- {name}: {tool.description}" for name, tool in self.tools.items()
        )
        history_context = ""
        if self.history:
            recent = self.history[-5:]
            history_context = "\n".join(
                f"{h['role']}: {h['content'][:200]}" for h in recent
            )
            history_context = f"이전 대화:\n{history_context}\n\n"

        context_context = ""
        if self.current_context.get("last_tool"):
            ctx = self.current_context
            context_context = f"현재 맥락:\n  마지막 도구: {ctx['last_tool']}\n  마지막 질문: {ctx['last_question'][:200]}\n  마지막 답변: {ctx.get('last_answer', '')[:200]}\n\n"

        prompt = (
            f"{self.system_prompt}\n\n"
            f"사용 가능한 도구:\n{tool_descriptions}\n\n"
            f"{context_context}"
            f"{history_context}"
            f"사용자 질문: {user_input}\n\n"
            "JSON 응답:"
        )
        try:
            if self.tool_selection_provider == "ollama":
                from langchain_ollama import ChatOllama
                model = ChatOllama(model=self.tool_selection_model, temperature=0)
            else:
                from langchain_openai import ChatOpenAI
                model = ChatOpenAI(model=self.tool_selection_model, temperature=0)

            response = model.invoke(prompt)
            text = getattr(response, "content", str(response)).strip()
            parsed = _extract_json(text)
        except Exception as exc:
            logger.error("Tool selection failed (%s: %s)", type(exc).__name__, exc)
            return self._fallback_tool_selection(user_input)

        # Fallback: JSON parsing failed, try natural language
        if not isinstance(parsed, dict) or "tool" not in parsed:
            return self._fallback_tool_selection(user_input, str(parsed) + " " + text)

        tool_name = parsed.get("tool")
        question = parsed.get("question", user_input)
        if isinstance(tool_name, str) and tool_name:
            self._add_history("user", user_input)
            return tool_name, question
        direct_answer = parsed.get("answer")
        if direct_answer:
            return None, direct_answer
        return self._fallback_tool_selection(user_input)

    def _select_tool_by_presentation(self, user_input: str) -> str | None:
        """흔한 질문은 LLM tool selection 없이 바로 tool을 선택합니다."""
        presentation = self._classify_chat_presentation(user_input)
        if presentation.tool_name and presentation.tool_name in self.tools:
            return presentation.tool_name
        return None

    def _fallback_tool_selection(
        self,
        user_input: str,
        model_text: str = "",
    ) -> tuple[str | None, str]:
        """LLM Tool 선택이 실패했을 때 키워드 기반으로 안전하게 라우팅합니다."""
        combined = f"{model_text} {user_input}"
        for name in self.tools:
            if name in combined:
                self._add_history("user", user_input)
                return name, user_input

        keyword_map = {
            "compare_rfps": ["비교", "차이", "대조"],
            "extract_requirements": ["참가", "자격", "서류", "요건", "체크리스트", "필요한"],
            "decide_participation": ["참여", "판단", "추천", "가능", "적합", "리스크"],
            "search_rfp_documents": ["검색", "찾아", "조건", "필터", "골라"],
            "extract_facts": [
                "추출",
                "요약",
                "분석",
                "정보",
                "예산",
                "기간",
                "마감",
                "발주",
                "사업",
                "얼마",
                "언제",
            ],
        }
        for name, keywords in keyword_map.items():
            if name in self.tools and any(kw in user_input for kw in keywords):
                self._add_history("user", user_input)
                return name, user_input

        return None, user_input

    def _run_tool_with_retry(self, tool: Tool, question: str, state: dict[str, ToolResult] | None = None) -> ToolResult:
        """Tool 실행 실패 시 최대 max_retries회 재시도합니다."""
        effective_state = state if state is not None else self.state
        last_result: ToolResult | None = None
        for attempt in range(self.max_retries + 1):
            result = tool.run(question, self.chunks, self.embeddings, effective_state)
            result.retry_count = attempt
            if result.status not in ("failed", "partial"):
                return result
            last_result = result
        return last_result or ToolResult(
            tool_name=tool.name, status="failed", errors=["max retries exceeded"]
        )

    def _add_history(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_history:
            self.history.pop(0)
        if self._run_id:
            try:
                from app.services.sqlite_store import add_chat_message
                add_chat_message(self._run_id, role, content)
            except Exception:
                pass

    def run_cli_loop(self, exit_words: tuple[str, ...] = ("exit", "quit", "q")) -> None:
        """대화형 CLI 루프를 실행합니다."""
        print("챗봇 시작 (종료: exit, quit, q)")
        print(f"사용 가능한 도구: {', '.join(self.tools.keys())}")
        while True:
            try:
                user_input = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if user_input.lower() in exit_words:
                break
            if not user_input:
                continue
            response = self.chat(user_input)
            tool_info = f" [도구: {response['tool_used']}]" if response["tool_used"] else ""
            print(f"\n{tool_info}\n{response['reply']}")


def build_chatbot_from_config(config: dict[str, Any]) -> ChatbotRunner:
    """config에서 챗봇 설정을 읽어 ChatbotRunner를 생성합니다."""
    agent_cfg = config.get("agent", {})
    chatbot_cfg = agent_cfg.get("chatbot", {})
    rag_cfg = config.get("rag", {})

    from src.rag.tool import build_tool_from_config

    default_retriever = dict(rag_cfg.get("retriever", {}))
    default_answerer = dict(rag_cfg.get("answerer", {}))

    # ChromaDB vector_store가 설정되어 있으면 retriever에 persist_dir 주입
    vector_store_cfg = rag_cfg.get("vector_store", {})
    if vector_store_cfg.get("type") == "chroma":
        default_retriever["method"] = "chroma"
        default_retriever["persist_dir"] = vector_store_cfg.get("path", "vector_store")

    raw_tools = agent_cfg.get("tools", {})
    tools: dict[str, Tool] = {}
    for name, tool_cfg in raw_tools.items():
        tools[name] = build_tool_from_config(
            name, tool_cfg, default_retriever, default_answerer,
            agent_cfg, rag_cfg,
        )

    return ChatbotRunner(
        tools=tools,
        tool_selection_model=chatbot_cfg.get("tool_selection_model", "gpt-4o-mini"),
        tool_selection_provider=chatbot_cfg.get("tool_selection_provider", "openai"),
        system_prompt=chatbot_cfg.get("system_prompt"),
        max_history=int(chatbot_cfg.get("max_history", 10)),
        cache_ttl=int(chatbot_cfg.get("cache_ttl", 300)),
    )


def _extract_json(text: str) -> dict[str, Any]:
    """LLM 응답에서 JSON을 추출합니다. markdown 코드블록, nested JSON 대응."""
    import re

    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    match = _find_json_object(text)
    if match:
        return json.loads(match)
    try:
        return json.loads(text)
    except Exception:
        logger.warning("JSON parse failed for: %s", text[:100])
        raise


def _find_json_object(text: str) -> str | None:
    """중첩된 JSON 객체를 brace 카운트로 추출합니다."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None
