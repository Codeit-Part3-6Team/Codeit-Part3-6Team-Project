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
                name, tool_cfg, default_retriever, default_answerer, agent_cfg
            )

        self.state: dict[str, ToolResult] = {}
        self.phase_results: list[dict[str, Any]] = []
        self.step_count: int = 0

        self._loader_config = dict(rag_cfg.get("loader", {}))
        self._checkpoint_enabled = bool(rag_cfg.get("checkpoint", {}).get("enabled", False))
        self._output_dir: Path | None = None

    def run(self, question: str | None = None, output_dir: str | Path | None = None) -> dict[str, Any]:
        """전체 Phase DAG를 실행하고 최종 State를 반환합니다.

        Args:
            question: 최초 질문. None이면 Phase 정의의 첫 Tool 설명으로 대체.
            output_dir: 산출물 저장 디렉터리. 지정되면 agent_state.jsonl, agent_metrics.json 저장.

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

        summary = self._build_summary()
        if output_dir:
            self._save_artifacts(Path(output_dir))

        return summary

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
            remaining = {p["name"] for p in self.phases} - set(order)
            # cycle detected — 남은 Phase는 의존 없이 뒤에 추가
            order.extend(p["name"] for p in self.phases if p["name"] in remaining)

        return order

    def _build_summary(self) -> dict[str, Any]:
        """실행 결과 요약을 생성합니다."""
        state_serialized: dict[str, Any] = {}
        for name, result in self.state.items():
            if isinstance(result, ToolResult):
                state_serialized[name] = {
                    "tool_name": result.tool_name,
                    "phase_name": result.phase_name,
                    "status": result.status,
                    "answer": result.answer[:200] if result.answer else "",
                    "citations_count": len(result.citations),
                    "errors": result.errors,
                    "duration_ms": result.duration_ms,
                }
            else:
                state_serialized[name] = result

        return {
            "state": state_serialized,
            "phase_results": self.phase_results,
            "step_count": self.step_count,
            "status": self.phase_results[-1].get("status", "ok") if self.phase_results else "ok",
            "metrics": self._calculate_metrics(),
        }

    def _calculate_metrics(self) -> dict[str, Any]:
        """Agent 실행 지표를 계산합니다.

        챗봇 확장 시 tool_selection_accuracy, hallucination_rate 등 추가.
        """
        total_tools = len(self.state)
        if total_tools == 0:
            return {
                "phase_count": len(self.phase_results),
                "tool_count": 0,
                "tool_success_rate": 0.0,
                "tool_failure_rate": 0.0,
                "phase_completion_rate": 0.0,
                "agent_duration_ms": 0,
            }

        success_count = sum(1 for r in self.state.values() if getattr(r, "status", "failed") == "ok")
        failed_count = total_tools - success_count
        total_phases = len(self.phases)
        completed_phases = sum(
            1 for pr in self.phase_results if pr.get("status") in ("ok", "partial")
        )
        total_duration = sum(
            getattr(r, "duration_ms", 0) for r in self.state.values()
        )

        return {
            "phase_count": total_phases,
            "completed_phase_count": completed_phases,
            "tool_count": total_tools,
            "tool_success_count": success_count,
            "tool_failure_count": failed_count,
            "tool_success_rate": round(success_count / total_tools, 4),
            "tool_failure_rate": round(failed_count / total_tools, 4),
            "phase_completion_rate": round(completed_phases / total_phases, 4) if total_phases else 0.0,
            "agent_duration_ms": total_duration,
            # 챗봇 확장 시 추가될 지표 (placeholder)
            "tool_selection_accuracy": None,
            "hallucination_rate": None,
        }

    def _save_artifacts(self, output_dir: Path) -> None:
        """Phase별 ToolResult와 Agent 지표를 파일로 저장합니다."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # agent_state.jsonl: Phase별 Tool 실행 결과
        import json

        state_path = output_dir / "agent_state.jsonl"
        with open(state_path, "w", encoding="utf-8") as fh:
            for phase_result in self.phase_results:
                record = {
                    "phase_name": phase_result.get("phase_name", ""),
                    "phase_status": phase_result.get("status", ""),
                    "tools": {},
                }
                for tname, tresult in phase_result.get("tools", {}).items():
                    if isinstance(tresult, ToolResult):
                        record["tools"][tname] = {
                            "status": tresult.status,
                            "answer": tresult.answer[:500] if tresult.answer else "",
                            "citations_count": len(tresult.citations),
                            "errors": tresult.errors,
                            "duration_ms": tresult.duration_ms,
                        }
                    else:
                        record["tools"][tname] = tresult
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")

        # agent_metrics.json: 종합 지표
        from src.config import write_json

        write_json(output_dir / "agent_metrics.json", self._calculate_metrics())


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
