"""Agent Loop 실행기 모듈.

config의 agent.phases 정의를 읽어 Phase DAG를 해석하고,
Tool을 순차/병렬 dispatch하며 Phase 간 State를 전파합니다.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any

from src.config import write_json
from src.rag.tool import OnFailure, Tool, ToolResult, build_tool_from_config


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
                name, tool_cfg, default_retriever, default_answerer, agent_cfg, rag_cfg
            )

        self.state: dict[str, ToolResult] = {}
        self.phase_results: list[dict[str, Any]] = []
        self.step_count: int = 0

        self._output_dir: Path | None = None

    def run(self, question: str | None = None, output_dir: str | Path | None = None) -> dict[str, Any]:
        """전체 Phase DAG를 실행하고 최종 State를 반환합니다.

        Args:
            question: 최초 질문. None이면 Phase 정의의 첫 Tool 설명으로 대체.
            output_dir: 산출물 저장 디렉터리. 지정되면 chunks/embeddings 로딩 및
                        agent_state.jsonl, agent_metrics.json 저장.

        Returns:
            최종 state dict (tool_name → ToolResult)
        """
        if output_dir:
            self._output_dir = Path(output_dir)
        chunks, embeddings = self._load_document_context()

        for phase_name in self._phase_order:
            if self.step_count >= self.max_steps:
                break
            phase = None
            for p in self.phases:
                if p["name"] == phase_name:
                    phase = p
                    break
            if phase is None:
                continue
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
        """단일 Phase의 모든 Tool을 실행합니다.

        phase.parallel이 True이면 ThreadPoolExecutor로 Tool을 병렬 실행합니다.
        """
        phase_name = phase["name"]
        tool_names: list[str] = phase.get("tools", [])
        parallel = bool(phase.get("parallel", False))

        if self.verbose:
            mode = "parallel" if parallel else "serial"
            print(f"[Agent] Phase: {phase_name} | Tools: {tool_names} | Mode: {mode}")

        if parallel:
            return self._run_phase_parallel(phase_name, tool_names, question, chunks, embeddings)

        return self._run_phase_serial(phase_name, tool_names, question, chunks, embeddings)

    def _run_phase_serial(
        self,
        phase_name: str,
        tool_names: list[str],
        question: str | None,
        chunks: list[dict[str, str]],
        embeddings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        results: dict[str, ToolResult] = {}
        phase_failed = False

        for tool_name in tool_names:
            if self.step_count >= self.max_steps:
                break
            result, abort = self._run_single_tool(phase_name, tool_name, question, chunks, embeddings)
            results[tool_name] = result
            if abort and not phase_failed:
                phase_failed = True
                break

        return {
            "phase_name": phase_name,
            "tools": {name: r.__dict__ if isinstance(r, ToolResult) else r for name, r in results.items()},
            "status": "failed" if phase_failed else "ok",
        }

    def _run_phase_parallel(
        self,
        phase_name: str,
        tool_names: list[str],
        question: str | None,
        chunks: list[dict[str, str]],
        embeddings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from threading import Lock

        results: dict[str, ToolResult] = {}
        phase_failed = False
        lock = Lock()

        # ThreadPoolExecutor 한계: abort 시 이미 실행 중인 future는 취소 불가. 결과는 버려짐.
        with ThreadPoolExecutor(max_workers=min(len(tool_names), 4)) as executor:
            future_map = {
                executor.submit(
                    self._run_single_tool, phase_name, tool_name, question, chunks, embeddings
                ): tool_name
                for tool_name in tool_names
            }
            for future in as_completed(future_map):
                with lock:
                    if phase_failed:
                        future.cancel()
                        continue
                tool_name = future_map[future]
                result, abort = future.result()
                with lock:
                    results[tool_name] = result
                    if abort:
                        phase_failed = True

        return {
            "phase_name": phase_name,
            "tools": {name: r.__dict__ if isinstance(r, ToolResult) else r for name, r in results.items()},
            "status": "failed" if phase_failed else "ok",
        }

    def _run_single_tool(
        self,
        phase_name: str,
        tool_name: str,
        question: str | None,
        chunks: list[dict[str, str]],
        embeddings: list[dict[str, Any]],
    ) -> tuple[ToolResult, bool]:
        """단일 Tool을 실행하고 (ToolResult, abort_flag)를 반환합니다."""
        if self.step_count >= self.max_steps:
            return ToolResult(tool_name=tool_name, phase_name=phase_name, status="skipped"), False

        tool = self.tools.get(tool_name)
        if tool is None:
            tr = ToolResult(
                tool_name=tool_name,
                phase_name=phase_name,
                status="failed",
                errors=[f"Tool not found: {tool_name}"],
            )
            self.state[tool_name] = tr
            return tr, False

        self.step_count += 1
        tool_result = tool.run(
            question=question or tool.description,
            chunks=chunks,
            embeddings=embeddings,
            state=self.state,
        )
        tool_result.phase_name = phase_name
        self.state[tool_name] = tool_result

        if self.verbose:
            status_map = {"ok": "OK", "partial": "PARTIAL", "not_found": "NF", "failed": "FAIL", "skipped": "SKIP"}
            status_icon = status_map.get(tool_result.status, tool_result.status.upper())
            print(f"  Tool {tool_name}: {status_icon} ({tool_result.duration_ms}ms)")

        abort = False
        if tool_result.status == "failed":
            if tool.on_failure == OnFailure.ABORT_PHASE:
                abort = True
            elif tool.on_failure == OnFailure.ABORT_AGENT:
                return tool_result, True  # [Agent] 중단

        return tool_result, abort

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
            import warnings

            warnings.warn(
                "Phase DAG에 순환 의존성이 감지되었습니다. "
                "정렬되지 않은 Phase는 YAML 정의 순서로 실행됩니다: {}".format(sorted(remaining)),
                RuntimeWarning,
            )
            for phase in self.phases:
                if phase["name"] in remaining:
                    order.append(phase["name"])

        return order

    def _load_document_context(self) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
        """문서 chunk와 embedding을 로딩합니다.

        checkpoint가 활성화되어 있고 output_dir이 있으면 산출물에서 읽고,
        없으면 빈 리스트를 반환합니다 (Tool의 retriever가 자체 처리).
        """
        if self._output_dir is None:
            return [], []

        import csv
        import json

        chunks: list[dict[str, str]] = []
        embeddings: list[dict[str, Any]] = []

        chunks_path = self._output_dir / "chunks.csv"
        if chunks_path.exists():
            with open(chunks_path, "r", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    chunks.append(dict(row))

        embeddings_path = self._output_dir / "embeddings.jsonl"
        if embeddings_path.exists():
            with open(embeddings_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        embeddings.append(json.loads(line))
        return chunks, embeddings

    def _build_summary(self) -> dict[str, Any]:
        """실행 결과 요약을 생성합니다."""
        state_serialized: dict[str, Any] = {}
        for name, result in self.state.items():
            if isinstance(result, ToolResult):
                state_serialized[name] = {
                    "tool_name": result.tool_name,
                    "phase_name": result.phase_name,
                    "status": result.status,
                    "answer": result.answer[:500] if result.answer else "",
                    "structured_output": result.structured_output,
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

        Config-driven 모드: 정의된 Tool 대비 실행/성공 비율 측정.
        챗봇 모드 확장 시 tool_selection_accuracy는 LLM의 Tool 선택 정확도,
        hallucination_rate는 judge 기반 환각 비율로 대체됩니다.
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

        # Config-driven 모드: 정의된 Tool 중 실제 실행된 비율
        defined_tools = len(self.tools)
        executed_tools = total_tools
        tool_selection_accuracy = round(executed_tools / defined_tools, 4) if defined_tools else 1.0

        # not_found 감지된 Tool 비율 (환각 회피율의 근사치)
        not_found_count = sum(
            1 for r in self.state.values() if getattr(r, "status", "") == "not_found"
        )
        hallucination_avoidance = round(not_found_count / total_tools, 4) if total_tools else 0.0

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
            "tool_selection_accuracy": tool_selection_accuracy,
            "hallucination_avoidance_rate": hallucination_avoidance,
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

        write_json(output_dir / "agent_metrics.json", self._calculate_metrics())



class AgentLoopRunner:
    """Agent Loop: Planner -> Executor -> Evaluator 반복.

    config의 agent.loop.max_iterations에 따라 Tool을 선택하고 실행한 뒤,
    결과를 평가하여 부족하면 다른 Tool로 재시도합니다.
    모든 Tool은 agent.tools에 정의된 것을 그대로 사용합니다.
    """

    def __init__(self, tools, loop_cfg, chunks, embeddings, agent_cfg=None):
        self.tools = tools
        self.max_iterations = int(loop_cfg.get("max_iterations", 5))
        self.chunks = chunks
        self.embeddings = embeddings
        self.agent_cfg = agent_cfg or {}
        self.state = {}
        self.trace = []

    def run(self, user_input):
        self.trace = []
        for iteration in range(self.max_iterations):
            step = {"iteration": iteration + 1}
            tool_name, question = self._plan(user_input, iteration)
            if tool_name is None:
                step["status"] = "no_tool_selected"
                self.trace.append(step)
                break
            step["tool"] = tool_name

            result = self._execute(tool_name, question)
            self.state[tool_name] = result
            step["status"] = result.status
            step["answer"] = result.answer[:200] if result.answer else ""
            step["duration_ms"] = result.duration_ms
            self.trace.append(step)

            if self._is_complete(result, iteration):
                return self._build_response(result, tool_name)

        last = self.trace[-1] if self.trace else {}
        last_tool = last.get("tool")
        if last_tool and last_tool in self.state:
            return self._build_response(self.state[last_tool], last_tool)
        return {"reply": "분석을 완료하지 못했습니다.", "tool_used": [], "completed": False, "trace": self.trace}

    def _plan(self, user_input, iteration):
        keyword_map = {
            "extract_facts": ["추출", "요약", "분석", "예산", "기간", "자격", "마감", "정보"],
            "decide_participation": ["참여", "판단", "추천", "가능", "적합"],
        }
        for name, keywords in keyword_map.items():
            if name in self.tools and any(kw in user_input for kw in keywords):
                return name, user_input
        if self.tools:
            first = next(iter(self.tools))
            return first, user_input
        return None, user_input

    def _execute(self, tool_name, question):
        from src.rag.tool import ToolResult
        tool = self.tools.get(tool_name)
        if tool is None:
            return ToolResult(tool_name=tool_name, status="failed", errors=[f"Tool not found: {tool_name}"])
        return tool.run(question, self.chunks, self.embeddings, self.state)

    def _is_complete(self, result, iteration):
        if result.status == "ok" and result.answer and "확인하지 못했습니다" not in result.answer:
            return True
        return iteration >= self.max_iterations - 1

    def _build_response(self, result, tool_name):
        reply = self._format(result)
        return {
            "reply": reply,
            "tool_used": [t["tool"] for t in self.trace if "tool" in t],
            "completed": True,
            "status": result.status,
            "citations_count": len(result.citations),
            "trace": self.trace,
        }

    def _format(self, result):
        if getattr(result, "structured_output", None):
            lines = []
            for k, v in result.structured_output.items():
                if isinstance(v, list):
                    lines.append(f"  {k}: " + ", ".join(str(x) for x in v))
                else:
                    lines.append(f"  {k}: {v}")
            out = "\n".join(lines)
        else:
            out = getattr(result, "answer", "") or "(응답 없음)"
        citations = getattr(result, "citations", [])
        if citations:
            source_lines = []
            for c in citations[:5]:
                page = c.get("page", c.get("page_start", "?"))
                section = c.get("section", "")
                chunk_id = c.get("chunk_id", "")
                label = f"p.{page} ({section})" if section else f"p.{page}"
                source_lines.append(f"📄 {label} chunk_id: {chunk_id}")
            out += "\n\n[출처]\n" + "\n".join(source_lines)
        return out


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
