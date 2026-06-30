"""Agent Loop 동작 테스트."""
from __future__ import annotations

from src.rag.agent import AgentRunner
from src.rag.tool import ToolResult


def test_agent_runner_resolves_dag_simple():
    config = {
        "rag": {
            "embedding": {"provider": "local"},
            "retriever": {"method": "keyword", "top_k": 3},
            "answerer": {"provider": "local"},
        },
        "agent": {
            "enabled": True,
            "phases": [
                {"name": "extract", "tools": ["extract_facts"]},
                {"name": "decide", "tools": ["decide_participation"], "depends_on": ["extract"]},
            ],
            "tools": {
                "extract_facts": {"description": "extract facts"},
                "decide_participation": {"description": "decide whether to participate"},
            },
        },
    }
    runner = AgentRunner(config)
    assert runner._phase_order == ["extract", "decide"]


def test_agent_runner_resolves_dag_multiple_deps():
    config = {
        "rag": {
            "embedding": {"provider": "local"},
            "retriever": {"method": "keyword", "top_k": 3},
            "answerer": {"provider": "local"},
        },
        "agent": {
            "enabled": True,
            "phases": [
                {"name": "extract", "tools": ["extract_facts"]},
                {"name": "scan", "tools": ["scan_clauses"], "depends_on": ["extract"]},
                {"name": "diagnose", "tools": ["check_budget"], "depends_on": ["extract"]},
                {"name": "decide", "tools": ["decide_participation"], "depends_on": ["scan", "diagnose"]},
            ],
            "tools": {
                "extract_facts": {"description": "extract"},
                "scan_clauses": {"description": "scan"},
                "check_budget": {"description": "check"},
                "decide_participation": {"description": "decide"},
            },
        },
    }
    runner = AgentRunner(config)
    order = runner._phase_order
    # extract 먼저, scan/diagnose가 그 다음, decide가 마지막
    assert order[0] == "extract"
    assert order[-1] == "decide"
    assert order.index("scan") < order.index("decide")
    assert order.index("diagnose") < order.index("decide")


def test_agent_runner_runs_with_local_tools():
    config = {
        "rag": {
            "embedding": {"provider": "local"},
            "retriever": {"method": "keyword", "top_k": 3},
            "answerer": {"provider": "local"},
        },
        "agent": {
            "enabled": True,
            "max_steps": 5,
            "phases": [
                {"name": "extract", "tools": ["extract_facts"]},
            ],
            "tools": {
                "extract_facts": {
                    "description": "extract facts from documents",
                    "retriever": {"top_k": 3},
                    "answerer": {"provider": "local"},
                },
            },
        },
    }
    runner = AgentRunner(config)
    result = runner.run("Should we participate?")
    assert result["status"] == "ok"
    assert result["step_count"] >= 1
    assert "extract_facts" in result["state"]


def test_agent_runner_respects_max_steps():
    config = {
        "rag": {
            "embedding": {"provider": "local"},
            "retriever": {"method": "keyword", "top_k": 3},
            "answerer": {"provider": "local"},
        },
        "agent": {
            "enabled": True,
            "max_steps": 1,
            "phases": [
                {"name": "extract", "tools": ["extract_facts", "parse_conditions"]},
                {"name": "decide", "tools": ["decide_participation"]},
            ],
            "tools": {
                "extract_facts": {"description": "extract"},
                "parse_conditions": {"description": "parse"},
                "decide_participation": {"description": "decide"},
            },
        },
    }
    runner = AgentRunner(config)
    result = runner.run("Should we?")
    # max_steps=1 → 첫 Tool 1개만 실행
    assert result["step_count"] == 1


def test_agent_runner_tool_not_found_graceful():
    config = {
        "rag": {
            "embedding": {"provider": "local"},
            "retriever": {"method": "keyword", "top_k": 3},
            "answerer": {"provider": "local"},
        },
        "agent": {
            "enabled": True,
            "phases": [
                {"name": "extract", "tools": ["nonexistent_tool"]},
            ],
            "tools": {},
        },
    }
    runner = AgentRunner(config)
    result = runner.run()
    # 존재하지 않는 Tool → 실패로 기록되지만 Agent는 중단되지 않음
    assert result["status"] == "ok"
    state = result["state"]
    assert "nonexistent_tool" in state
    assert state["nonexistent_tool"]["status"] == "failed"


def test_agent_runner_parallel_execution():
    config = {
        "rag": {
            "embedding": {"provider": "local"},
            "retriever": {"method": "keyword", "top_k": 3},
            "answerer": {"provider": "local"},
        },
        "agent": {
            "enabled": True,
            "phases": [
                {"name": "extract", "tools": ["t1", "t2"], "parallel": True},
            ],
            "tools": {
                "t1": {"description": "tool 1", "answerer": {"provider": "local"}},
                "t2": {"description": "tool 2", "answerer": {"provider": "local"}},
            },
        },
    }
    runner = AgentRunner(config)
    result = runner.run("test?")
    assert result["status"] == "ok"
    assert result["step_count"] == 2
    assert "t1" in result["state"]
    assert "t2" in result["state"]


def test_chatbot_runner_builds_from_config():
    from src.rag.chatbot import build_chatbot_from_config

    config = {
        "rag": {
            "embedding": {"provider": "local"},
            "retriever": {"method": "keyword", "top_k": 3},
            "answerer": {"provider": "local"},
        },
        "agent": {
            "enabled": True,
            "chatbot": {"enabled": True, "tool_selection_model": "gpt-4o-mini"},
            "tools": {
                "extract_facts": {"description": "extract facts", "answerer": {"provider": "local"}},
            },
        },
    }
    bot = build_chatbot_from_config(config)
    assert "extract_facts" in bot.tools
    assert bot.tool_selection_model == "gpt-4o-mini"


def test_chatbot_runner_handles_no_tool_selection(monkeypatch):
    from src.rag.chatbot import ChatbotRunner

    bot = ChatbotRunner({})
    monkeypatch.setattr(bot, "_select_tool", lambda user_input: (None, user_input))

    response = bot.chat("문서 밖 질문")

    assert response["tool_used"] is None
    assert response["tool_result"] is None
    assert "적합한 도구" in response["reply"]


def test_chatbot_runner_handles_unknown_tool_selection(monkeypatch):
    from src.rag.chatbot import ChatbotRunner

    bot = ChatbotRunner({})
    monkeypatch.setattr(bot, "_select_tool", lambda user_input: ("missing_tool", user_input))

    response = bot.chat("요약해줘")

    assert response["tool_used"] is None
    assert response["tool_result"] is None
    assert "missing_tool" in response["reply"]


def test_chatbot_runner_fallback_routes_common_korean_questions():
    from src.rag.chatbot import build_chatbot_from_config

    config = {
        "rag": {
            "embedding": {"provider": "local"},
            "retriever": {"method": "keyword", "top_k": 3},
            "answerer": {"provider": "local"},
        },
        "agent": {
            "enabled": True,
            "chatbot": {"enabled": True, "tool_selection_provider": "missing_provider"},
            "tools": {
                "extract_facts": {"description": "extract facts", "answerer": {"provider": "local"}},
                "extract_requirements": {"description": "extract requirements", "answerer": {"provider": "local"}},
                "compare_rfps": {"description": "compare rfp documents", "answerer": {"provider": "local"}},
            },
        },
    }
    bot = build_chatbot_from_config(config)

    assert bot._fallback_tool_selection("요약해줘")[0] == "extract_facts"
    assert bot._fallback_tool_selection("사업 예산과 기간은?")[0] == "extract_facts"
    assert bot._fallback_tool_selection("참가 자격 요건은?")[0] == "extract_requirements"
    assert bot._fallback_tool_selection("두 문서를 비교해줘")[0] == "compare_rfps"


def test_agent_loop_configs_load_with_service_tools(repo_root):
    from src.config import load_config

    loop_cfg = load_config(repo_root / "configs" / "experiments" / "rag" / "agent" / "agent_loop.yaml")
    lplus_cfg = load_config(repo_root / "configs" / "experiments" / "rag" / "agent" / "agent_lplus.yaml")

    assert "rag" in loop_cfg
    assert loop_cfg["agent"]["loop"]["enabled"] is True
    assert set(lplus_cfg["agent"]["tools"]) >= {
        "extract_facts",
        "decide_participation",
        "search_rfp_documents",
        "compare_rfps",
        "extract_requirements",
    }
    assert lplus_cfg["agent"]["phases"] == [
        {"name": "extract", "tools": ["extract_facts"]},
        {"name": "decide", "tools": ["decide_participation"], "depends_on": ["extract"]},
    ]


def test_run_rag_agent_disabled_returns_disabled():
    from src.rag.pipeline import run_rag_agent

    config = {
        "agent": {"enabled": False},
    }
    result = run_rag_agent(config)
    assert result["status"] == "disabled"
    assert result["step_count"] == 0
    assert result["step_count"] == 0


def test_agent_runner_abort_phase_failure_path_does_not_crash():
    config = {
        "rag": {
            "embedding": {"provider": "local"},
            "retriever": {"method": "keyword", "top_k": 3},
            "answerer": {"provider": "local"},
        },
        "agent": {
            "enabled": True,
            "phases": [
                {"name": "extract", "tools": ["fail_tool"]},
            ],
            "tools": {
                "fail_tool": {"description": "fail", "on_failure": "abort_phase"},
            },
        },
    }
    runner = AgentRunner(config)

    class FailingTool:
        name = "fail_tool"
        on_failure = runner.tools["fail_tool"].on_failure

        def run(self, **kwargs):
            return ToolResult(
                tool_name="fail_tool",
                phase_name="extract",
                status="failed",
                errors=["boom"],
            )

    runner.tools["fail_tool"] = FailingTool()

    result = runner.run("질문")

    assert result["status"] == "failed"
    assert result["state"]["fail_tool"]["status"] == "failed"
