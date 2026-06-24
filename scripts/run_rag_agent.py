"""Agent Loop 실행 CLI 스크립트.

Usage:
    python scripts/run_rag_agent.py --config configs/experiments/rag/rag_agent.yaml --question "예산은?"
    python scripts/run_rag_agent.py --config rag_agent.yaml --verbose --dump-state
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from src.rag.pipeline import run_rag_agent  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG Agent Loop 실행기")
    parser.add_argument("--config", required=True, help="실험 config 파일 경로")
    parser.add_argument("--question", default=None, help="질문 (없으면 Tool 설명으로 대체)")
    parser.add_argument("--verbose", action="store_true", help="Phase/Tool 실행 로그 출력")
    parser.add_argument("--dump-state", action="store_true", help="Phase별 State를 JSON으로 출력")
    args = parser.parse_args()

    result = run_rag_agent(
        config_path=args.config,
        project_root=_PROJECT_ROOT,
        question=args.question,
    )

    if args.dump_state:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        status = result.get("status", "unknown")
        steps = result.get("step_count", 0)
        phases = len(result.get("phase_results", []))
        print(f"Agent completed: status={status}, steps={steps}, phases={phases}")


if __name__ == "__main__":
    main()
