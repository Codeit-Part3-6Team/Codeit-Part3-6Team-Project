"""Agent Loop 실행기 모듈.

config의 agent.phases 정의를 읽어 Phase DAG를 해석하고,
Tool을 순차/병렬 dispatch하며 Phase 간 State를 전파합니다.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any

from src.rag.tool import Tool, ToolResult, build_tool_from_config


class AgentRunner:
    """Phase DAG 해석 + Tool dispatch + State 전파를 수행하는 Agent 실행기입니다.

    config에서 agent.phases와 agent.tools를 읽어 실행 순서를 결정하고,
    Phase 단위로 Tool을 실행하며 결과를 State dict에 누적합니다.
    """

    def __init__(self, config: dict[str, Any], project_root: str | Path = "."):
        agent_cfg = config.get("agent", {})
        rag_cfg = config.get("rag", {})
        self.max_steps = int(agent_cfg.get("max_steps", 15))
        self.verbose = bool(agent_cfg.get("verbose", False))

        self.phases: list[dict[str, Any]] = agent_cfg.get("phases", [])
        self._phase_order: list[str] = self._resolve_dag()

        default_retriever = dict(rag_cfg.get("retriever", {}))
        default_answerer = dict(rag_cfg.get("answerer", {}))
        raw_tools = agent_cfg.get("tools", {})
        self.tools: dict[str, Tool] = {}
        for name, tool_cfg in raw_tools.items():
            self.tools[name] = build_tool_from_config(
                name, tool_cfg, default_retriever, default_answerer
            )

        self.state: dict[str, ToolResult] = {}
        self.phase_results: list[dict[str, Any]] = []
        self.step_count: int = 0

        self._loader_config = dict(rag_cfg.get("loader", {}))
        self._checkpoint_enabled = bool(rag_cfg.get("checkpoint", {}).get("enabled", False))
        self._output_dir: Path | None = None

    def run(self, question: str | None = None) -> dict[str, Any]:
        """전체 Phase DAG를 실행하고 최종 State를 반환합니다.

        Args:
            question: 최초 질문. None이면 Phase 정의의 첫 Tool 설명으로 대체.

        Returns:
            최종 state dict (tool_name → ToolResult)
        """
        chunks: list[dict[str, str]] = []
        embeddings: list[dict[str, Any]] = []

        for phase_name in self._phase_order:
            if self.step_count >= self.max_steps:
                break

            phase = next(p for p in self.phases if p["name"] == phase_name)
            result = self._run_phase(phase, question, chunks, embeddings)
            self.phase_results.append(result)

            if result.get("status") == "failed":
                break

        return {
            "state": {name: r.__dict__ if isinstance(r, ToolResult) else r for name, r in self.state.items()},
            "phase_results": self.phase_results,
            "step_count": self.step_count,
            "status": self.phase_results[-1].get("status", "ok") if self.phase_results else "ok",
        }

    def _run_phase(
        self,
        phase: dict[str, Any],
        question: str | None,
        chunks: list[dict[str, str]],
        embeddings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """단일 Phase의 모든 Tool을 실행합니다."""
        phase_name = phase["name"]
        tool_names: list[str] = phase.get("tools", [])

        if self.verbose:
            print(f"[Agent] Phase: {phase_name} | Tools: {tool_names}")

        results: dict[str, ToolResult] = {}
        phase_failed = False

        for tool_name in tool_names:
            if self.step_count >= self.max_steps:
                break

            tool = self.tools.get(tool_name)
            if tool is None:
                tr = ToolResult(
                    tool_name=tool_name,
                    phase_name=phase_name,
                    status="failed",
                    errors=[f"Tool not found: {tool_name}"],
                )
                results[tool_name] = tr
                self.state[tool_name] = tr
                continue

            self.step_count += 1
            tool_result = tool.run(
                question=question or tool.description,
                chunks=chunks,
                embeddings=embeddings,
                state=self.state,
            )
            tool_result.phase_name = phase_name
            self.state[tool_name] = tool_result
            results[tool_name] = tool_result

            if self.verbose:
                status_icon = "OK" if tool_result.status in ("ok", "partial") else "FAIL"
                print(f"  Tool {tool_name}: {status_icon} ({tool_result.duration_ms}ms)")

            if tool_result.status == "failed" and tool.on_failure.value == "abort_phase":
                phase_failed = True
                break
            if tool_result.status == "failed" and tool.on_failure.value == "abort_agent":
                return {"phase_name": phase_name, "tools": results, "status": "failed"}

        return {
            "phase_name": phase_name,
            "tools": {name: r.__dict__ if isinstance(r, ToolResult) else r for name, r in results.items()},
            "status": "failed" if phase_failed else "ok",
        }

    def _resolve_dag(self) -> list[str]:
        """depends_on 기준으로 Phase 위상 정렬을 수행합니다."""
        phase_map = {p["name"]: p for p in self.phases}
        in_degree: dict[str, int] = {p["name"]: 0 for p in self.phases}
        adj: dict[str, list[str]] = {p["name"]: [] for p in self.phases}

        for phase in self.phases:
            for dep in phase.get("depends_on", []):
                if dep in phase_map:
                    adj[dep].append(phase["name"])
                    in_degree[phase["name"]] += 1

        queue = deque([name for name, deg in in_degree.items() if deg == 0])
        order: list[str] = []

        while queue:
            current = queue.popleft()
            order.append(current)
            for neighbor in adj[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self.phases):
            remaining = set(self.phases) - set(order)  # type: ignore[arg-type]
            # cycle detected — 남은 Phase는 의존 없이 뒤에 추가
            order.extend(p["name"] for p in self.phases if p["name"] in remaining)

        return order


def run_rag_agent(
    config: dict[str, Any],
    project_root: str | Path = ".",
    question: str | None = None,
) -> dict[str, Any]:
    """config 기반 Agent 실행 진입점입니다.

    agent.enabled가 False이면 빈 결과를 반환합니다.
    pipeline.py에서 agent.enabled 분기에 따라 호출됩니다.

    Args:
        config: 전체 실험 config
        project_root: 프로젝트 루트 경로
        question: 초기 질문

    Returns:
        AgentRunner.run() 결과 dict
    """
    agent_cfg = config.get("agent", {})
    if not agent_cfg.get("enabled", False):
        return {"state": {}, "phase_results": [], "step_count": 0, "status": "disabled"}

    runner = AgentRunner(config, project_root)
    return runner.run(question)
