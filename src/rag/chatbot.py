"""Agent 챗봇 모듈.

config의 agent.chatbot.enabled: true일 때, LLM이 Tool description을 읽고
사용자 질문에 적합한 Tool을 동적으로 선택하여 실행합니다.
"""

from __future__ import annotations

import json
from typing import Any

from src.rag.tool import Tool, ToolResult


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
    ):
        self.tools = tools
        self.tool_selection_model = tool_selection_model
        self.tool_selection_provider = tool_selection_provider
        self.system_prompt = system_prompt or (
            "너는 RFP 문서 분석 도우미 챗봇이다.\n"
            "사용자의 질문에 가장 적합한 도구를 선택하고, 도구 실행 결과를 바탕으로 답변하라.\n"
            "아래 도구 중 하나를 선택하여 JSON으로 응답하라: {\"tool\": \"도구명\", \"question\": \"도구에 전달할 질문\"}\n"
            "도구가 필요 없으면 {\"tool\": null, \"answer\": \"직접 답변\"} 형식으로 응답하라."
        )
        self.max_history = max_history
        self.history: list[dict[str, str]] = []
        self.state: dict[str, ToolResult] = {}
        self.chunks: list[dict[str, str]] = []
        self.embeddings: list[dict[str, Any]] = []

    def chat(self, user_input: str) -> dict[str, Any]:
        """사용자 입력을 받아 Tool 선택 → 실행 → 응답을 반환합니다.

        Args:
            user_input: 사용자 메시지

        Returns:
            {"reply": str, "tool_used": str | None, "tool_result": dict | None}
        """
        tool_name, refined_question = self._select_tool(user_input)

        if tool_name is None:
            reply = refined_question or "죄송합니다. 해당 질문에 적합한 도구를 찾지 못했습니다."
            self._add_history("assistant", reply)
            return {"reply": reply, "tool_used": None, "tool_result": None}

        tool = self.tools.get(tool_name)
        if tool is None:
            reply = f"도구 '{tool_name}'을 찾을 수 없습니다. 사용 가능한 도구: {', '.join(self.tools)}"
            self._add_history("assistant", reply)
            return {"reply": reply, "tool_used": None, "tool_result": None}

        result = tool.run(refined_question, self.chunks, self.embeddings, self.state)
        self.state[tool_name] = result

        if result.status == "failed":
            reply = f"[{tool_name}] 실행 실패: {'; '.join(result.errors)}"
        elif result.structured_output:
            reply = json.dumps(result.structured_output, ensure_ascii=False, indent=2)
        else:
            reply = result.answer or "(응답 없음)"

        self._add_history("assistant", reply)
        return {
            "reply": reply,
            "tool_used": tool_name,
            "tool_result": {
                "status": result.status,
                "answer": result.answer[:500],
                "citations_count": len(result.citations),
                "duration_ms": result.duration_ms,
            },
        }

    def _select_tool(self, user_input: str) -> tuple[str | None, str]:
        """LLM에게 Tool 목록을 보여주고 선택하게 합니다."""
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

        prompt = (
            f"{self.system_prompt}\n\n"
            f"사용 가능한 도구:\n{tool_descriptions}\n\n"
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
        except Exception:
            return None, user_input

        tool_name = parsed.get("tool")
        question = parsed.get("question", user_input)
        if isinstance(tool_name, str) and tool_name:
            self._add_history("user", user_input)
            return tool_name, question
        direct_answer = parsed.get("answer")
        if direct_answer:
            return None, direct_answer
        return None, user_input

    def _add_history(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def run_cli_loop(self, exit_words: tuple[str, ...] = ("exit", "quit", "q")) -> None:
        """대화형 CLI 루프를 실행합니다."""
        print("챗봇 시작 (종료: exit, quit, q)")
        print(f"사용 가능한 도구: {', '.join(self.tools)}")
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
    )


def _extract_json(text: str) -> dict[str, Any]:
    """LLM 응답에서 JSON을 추출합니다. markdown 코드블록과 trailing text 대응."""
    import re

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    match = re.search(r"\{.*?\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return json.loads(text)
