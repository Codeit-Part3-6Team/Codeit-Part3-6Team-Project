"""Streamlit UI ↔ RAG 파이프라인 서비스 어댑터.

UI는 RAG 내부 구조를 모르고 이 모듈의 함수만 호출합니다.
import 시점 실행 금지 — 모든 동작은 함수 호출 시점에 발생합니다.

=== 제공 함수 ===
  create_and_ingest(raw_docs_source_dir)  새 run 생성 + 문서 ingest
  ask(run_id, question)                    챗봇 질의응답
  get_documents(run_id)                    문서 목록 조회
  list_runs()                              기존 run 목록
  get_run_info(run_id)                     run 메타정보
  clear_chatbot(run_id)                    챗봇 캐시 초기화
"""

from __future__ import annotations

import csv
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.config import load_config
from src.rag.pipeline import run_rag_ingest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_STREAMLIT_EXPERIMENTS = _PROJECT_ROOT / "experiments" / "streamlit"
# 전용 streamlit 템플릿 사용 (base_config 상속으로 rag-baseline/agent_lplus 포함)
_TEMPLATE_CONFIG_PATH = (
    _PROJECT_ROOT / "configs" / "experiments" / "rag" / "streamlit.yaml"
)

# ── run_id별 챗봇 인스턴스 캐시 ──
_chatbot_cache: dict[str, Any] = {}


def _generate_run_id() -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uid = uuid.uuid4().hex[:6]
    return f"{ts}_{short_uid}"


def _run_dir(run_id: str) -> Path:
    return _STREAMLIT_EXPERIMENTS / run_id


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def _build_streamlit_config(run_id: str) -> dict[str, Any]:
    """streamlit.yaml 템플릿을 로드해 run별 경로만 덮어씁니다.

    base_config 상속으로 rag-baseline.yaml → agent_lplus.yaml 설정을
    그대로 가져오며, paths만 run_id 기반으로 바꿉니다.
    """
    base = load_config(_TEMPLATE_CONFIG_PATH)
    run_dir = _run_dir(run_id)

    base["experiment"]["name"] = f"streamlit-{run_id}"
    base["paths"]["raw_docs_dir"] = str(run_dir / "raw_docs")
    base["paths"]["output_dir"] = str(run_dir / "output")

    return base


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────


def create_and_ingest(raw_docs_source_dir: str) -> dict[str, Any]:
    """원본 문서 디렉토리로 새 run을 생성하고 RAG ingest를 실행합니다.

    Args:
        raw_docs_source_dir: 원본 문서가 이미 저장된 디렉토리 경로

    Returns:
        {
            "run_id": str,
            "status": "ready" | "failed",
            "documents": int,
            "chunks": int,
            "embeddings": int,
            "config_path": str | None,
            "output_dir": str | None,
            "error": str | None,
        }
    """
    run_id = _generate_run_id()
    run_dir = _run_dir(run_id)
    raw_docs_dir = run_dir / "raw_docs"
    output_dir = run_dir / "output"

    try:
        raw_docs_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        source = Path(raw_docs_source_dir)
        file_count = 0
        for f in source.iterdir():
            if f.is_file():
                shutil.copy2(f, raw_docs_dir / f.name)
                file_count += 1

        if file_count == 0:
            return {
                "run_id": run_id,
                "status": "failed",
                "documents": 0,
                "chunks": 0,
                "embeddings": 0,
                "config_path": None,
                "output_dir": None,
                "error": "업로드된 파일이 없습니다.",
            }

        config = _build_streamlit_config(run_id)
        config_path = run_dir / "config.yaml"
        _write_yaml(config_path, config)

        result = run_rag_ingest(str(config_path), str(_PROJECT_ROOT))

        return {
            "run_id": run_id,
            "status": "ready",
            "documents": result.get("documents", 0),
            "chunks": result.get("chunks", 0),
            "embeddings": result.get("embeddings", 0),
            "config_path": str(config_path),
            "output_dir": str(output_dir),
            "error": None,
        }

    except Exception as exc:
        return {
            "run_id": run_id,
            "status": "failed",
            "documents": 0,
            "chunks": 0,
            "embeddings": 0,
            "config_path": None,
            "output_dir": None,
            "error": str(exc),
        }


def _get_or_build_chatbot(run_id: str) -> Any:
    """run_id에 해당하는 ChatbotRunner를 로딩하거나 생성합니다."""
    if run_id in _chatbot_cache:
        return _chatbot_cache[run_id]

    from src.rag.chatbot import build_chatbot_from_config
    from src.artifacts import resolve_experiment_dir

    config_path = _run_dir(run_id) / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Run config not found: {config_path}")

    config = load_config(config_path)
    output_dir = resolve_experiment_dir(_PROJECT_ROOT, config)

    bot = build_chatbot_from_config(config)
    bot.load_document_context(output_dir)

    _chatbot_cache[run_id] = bot
    return bot


def ask(run_id: str, question: str) -> dict[str, Any]:
    """챗봇에게 질문하고 답변 + citation을 반환합니다.

    Args:
        run_id: 실행 ID
        question: 사용자 질문

    Returns:
        {
            "reply": str,
            "tool_used": str | list[str] | None,
            "citations": list[dict],
            "status": str,
            "error": str | None,
        }
    """
    try:
        bot = _get_or_build_chatbot(run_id)
        response = bot.chat(question)

        citations: list[dict[str, Any]] = []
        tool_used = response.get("tool_used")
        if tool_used:
            tool_name = tool_used[-1] if isinstance(tool_used, list) else tool_used
            if tool_name in bot.state:
                tool_result = bot.state[tool_name]
                citations = list(tool_result.citations)

        return {
            "reply": response.get("reply", ""),
            "tool_used": tool_used,
            "citations": citations,
            "status": response.get("tool_result", {}).get("status", "unknown"),
            "error": None,
        }

    except Exception as exc:
        return {
            "reply": "",
            "tool_used": None,
            "citations": [],
            "status": "error",
            "error": str(exc),
        }


def ask_with_document_filter(
    run_id: str,
    question: str,
    selected_doc_ids: list[str] | None = None,
) -> dict[str, Any]:
    """선택된 문서 ID로 필터링한 뒤 챗봇에 질문합니다.

    선택 문서가 있으면 chunks를 필터링한 임시 챗봇을 생성합니다.
    선택 문서가 없으면 기본 ask()와 동일하게 동작합니다.
    """
    if not selected_doc_ids:
        return ask(run_id, question)

    from src.rag.chatbot import build_chatbot_from_config
    from src.artifacts import resolve_experiment_dir

    config_path = _run_dir(run_id) / "config.yaml"
    if not config_path.exists():
        return {
            "reply": "",
            "tool_used": None,
            "citations": [],
            "status": "error",
            "error": f"Run config not found: {config_path}",
        }

    config = load_config(config_path)
    output_dir = resolve_experiment_dir(_PROJECT_ROOT, config)

    bot = build_chatbot_from_config(config)
    bot.load_document_context(output_dir)

    # 선택된 document_id로 chunks 필터링
    doc_ids = set(selected_doc_ids)
    bot.chunks = [c for c in bot.chunks if c.get("document_id") in doc_ids]

    if not bot.chunks:
        return {
            "reply": "선택한 문서에 해당하는 분석 데이터가 없습니다.",
            "tool_used": None,
            "citations": [],
            "status": "not_found",
            "error": None,
        }

    response = bot.chat(question)

    citations: list[dict[str, Any]] = []
    tool_used = response.get("tool_used")
    if tool_used:
        tool_name = tool_used[-1] if isinstance(tool_used, list) else tool_used
        if tool_name in bot.state:
            citations = list(bot.state[tool_name].citations)

    return {
        "reply": response.get("reply", ""),
        "tool_used": tool_used,
        "citations": citations,
        "status": response.get("tool_result", {}).get("status", "unknown"),
        "error": None,
    }


def get_documents(run_id: str) -> list[dict[str, Any]]:
    """chunks.csv에서 문서 목록을 추출합니다.

    Returns:
        [{"document_id": str, "title": str, "source_path": str, "chunk_count": int}, ...]
    """
    chunks_path = _run_dir(run_id) / "output" / "chunks.csv"
    if not chunks_path.exists():
        return []

    csv.field_size_limit(int(1e9))
    with open(chunks_path, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    docs: dict[str, dict[str, Any]] = {}
    for row in rows:
        doc_id = row.get("document_id", "unknown")
        if doc_id not in docs:
            docs[doc_id] = {
                "document_id": doc_id,
                "title": row.get("title", ""),
                "source_path": row.get("source_path", ""),
                "chunk_count": 0,
            }
        docs[doc_id]["chunk_count"] += 1

    return list(docs.values())


def list_runs() -> list[dict[str, Any]]:
    """기존 run 목록을 반환합니다.

    Returns:
        [{"run_id": str, "created_at": str, "status": str, "documents": int}, ...]
    """
    if not _STREAMLIT_EXPERIMENTS.exists():
        return []

    runs: list[dict[str, Any]] = []
    for run_dir in sorted(
        _STREAMLIT_EXPERIMENTS.iterdir(), reverse=True
    ):
        if not run_dir.is_dir():
            continue
        run_id = run_dir.name
        status_path = run_dir / "output" / "run_status.json"
        chunks_path = run_dir / "output" / "chunks.csv"

        status = "unknown"
        if status_path.exists():
            import json
            try:
                data = json.loads(status_path.read_text(encoding="utf-8"))
                status = data.get("status", "unknown")
            except Exception:
                pass
        elif chunks_path.exists():
            status = "ready"

        import json
        docs_count = 0
        info_path = run_dir / "output" / "run_info.json"
        if info_path.exists():
            try:
                info = json.loads(info_path.read_text(encoding="utf-8"))
                docs_count = info.get("experiment", {}).get("documents", 0)
            except Exception:
                pass

        config_path = run_dir / "config.yaml"
        created_at = ""
        if config_path.exists():
            try:
                created_at = datetime.fromtimestamp(
                    config_path.stat().st_mtime
                ).isoformat()
            except Exception:
                pass

        runs.append({
            "run_id": run_id,
            "created_at": created_at,
            "status": status,
            "documents": docs_count,
        })

    return runs


def get_run_info(run_id: str) -> dict[str, Any]:
    """특정 run의 메타 정보를 반환합니다."""
    run_dir = _run_dir(run_id)
    config_path = run_dir / "config.yaml"
    chunks_path = run_dir / "output" / "chunks.csv"
    status_path = run_dir / "output" / "run_status.json"

    if not config_path.exists():
        return {"run_id": run_id, "exists": False, "status": "not_found"}

    import json

    status = "unknown"
    if status_path.exists():
        try:
            data = json.loads(status_path.read_text(encoding="utf-8"))
            status = data.get("status", "unknown")
        except Exception:
            pass
    elif chunks_path.exists():
        status = "ready"

    docs = get_documents(run_id)
    config = load_config(config_path)

    return {
        "run_id": run_id,
        "exists": True,
        "status": status,
        "config_path": str(config_path),
        "output_dir": str(run_dir / "output"),
        "raw_docs_dir": config.get("paths", {}).get("raw_docs_dir", ""),
        "documents": docs,
        "document_count": len(docs),
    }


def clear_chatbot(run_id: str | None = None) -> None:
    """챗봇 캐시를 초기화합니다. run_id가 None이면 전체 초기화."""
    if run_id:
        _chatbot_cache.pop(run_id, None)
    else:
        _chatbot_cache.clear()
