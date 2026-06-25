"""Agent Loop 동작 테스트."""
from __future__ import annotations

from src.rag.agent import AgentRunner


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


def test_run_rag_agent_disabled_returns_disabled():
    from src.rag.pipeline import run_rag_agent

    config = {
        "agent": {"enabled": False},
    }
    result = run_rag_agent(config)
    assert result["status"] == "disabled"
    assert result["step_count"] == 0
    assert result["step_count"] == 0
