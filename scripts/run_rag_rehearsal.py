from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    # scripts를 직접 실행해도 src 패키지를 찾을 수 있게 project root를 추가합니다.
    sys.path.insert(0, str(PROJECT_ROOT))

from src.artifacts import resolve_experiment_dir
from src.config import load_config
from src.rag.pipeline import run_rag_evaluation, run_rag_ingest
from src.rag.validation import check_rag_pipeline


DEFAULT_CONFIGS = [
    "configs/experiments/rag/rag_langchain.yaml",
    "configs/experiments/rag/rag_realistic_docs.yaml",
]
REQUIRED_ARTIFACTS = [
    "config.yaml",
    "parsed_documents.csv",
    "chunks.csv",
    "embeddings.jsonl",
    "retrieval_results.jsonl",
    "answers.jsonl",
    "evaluation_results.csv",
    "bad_retrievals.csv",
    "unsupported_answers.csv",
    "failed_questions.csv",
    "metrics.json",
    "run_status.json",
    "rag_ingest_checkpoint.json",
]


def main() -> None:
    """팀 공유 전 RAG 파이프라인 기준 config를 한 번에 리허설합니다."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument(
        "--config",
        action="append",
        dest="configs",
        help="리허설할 config 경로입니다. 여러 번 지정할 수 있습니다.",
    )
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    configs = args.configs or DEFAULT_CONFIGS
    summaries = [_run_one(root, config_path) for config_path in configs]

    print(json.dumps({"ok": all(row["ok"] for row in summaries), "runs": summaries}, indent=2, ensure_ascii=False))
    if not all(row["ok"] for row in summaries):
        raise SystemExit(1)


def _run_one(root: Path, config_path: str) -> dict[str, Any]:
    check = check_rag_pipeline(config_path, root)
    if not check["ok"]:
        return {
            "config": config_path,
            "ok": False,
            "stage": "check",
            "errors": check["errors"],
            "warnings": check["warnings"],
        }

    ingest = run_rag_ingest(config_path, root)
    metrics = run_rag_evaluation(config_path, root)
    output_dir = resolve_experiment_dir(root, load_config(root / config_path))
    missing_artifacts = [filename for filename in REQUIRED_ARTIFACTS if not (output_dir / filename).exists()]
    failure_log_exists = (output_dir / "failure.log").exists()
    ok = not missing_artifacts and not failure_log_exists and metrics.get("not_found_rate", 1.0) == 0.0

    return {
        "config": config_path,
        "experiment": check["summary"]["experiment"],
        "ok": ok,
        "output_dir": str(output_dir.relative_to(root)),
        "ingest": ingest,
        "metrics": metrics,
        "missing_artifacts": missing_artifacts,
        "failure_log_exists": failure_log_exists,
        "warnings": check["warnings"],
    }


if __name__ == "__main__":
    main()
