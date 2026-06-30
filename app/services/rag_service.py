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
import time
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.config import load_config
from src.rag.pipeline import run_rag_ingest

_STREAMLIT_EXPERIMENTS = _PROJECT_ROOT / "experiments" / "streamlit"
# 전용 streamlit 템플릿 사용 (base_config 상속으로 rag-baseline/agent_lplus 포함)
_TEMPLATE_CONFIG_PATH = (
    _PROJECT_ROOT / "configs" / "experiments" / "rag" / "streamlit.yaml"
)

# ── run_id별 챗봇 인스턴스 캐시 ──
_chatbot_cache: dict[str, Any] = {}
_SUPPORTED_FILE_TYPES = ["pdf", "docx", "hwp", "hwpx", "txt", "csv"]


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


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    csv.field_size_limit(int(1e9))
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _output_dir(run_id: str) -> Path:
    return _run_dir(run_id) / "output"


def _build_streamlit_config(
    run_id: str,
    *,
    embedding_provider: str | None = None,
    embedding_model_name: str | None = None,
) -> dict[str, Any]:
    """streamlit.yaml 템플릿을 로드해 run별 경로만 덮어씁니다.

    base_config 상속으로 rag-baseline.yaml → agent_lplus.yaml 설정을
    그대로 가져오며, paths만 run_id 기반으로 바꿉니다.
    """
    base = load_config(_TEMPLATE_CONFIG_PATH)
    run_dir = _run_dir(run_id)

    base["experiment"]["name"] = f"streamlit-{run_id}"
    base["paths"]["raw_docs_dir"] = str(run_dir / "raw_docs")
    base["paths"]["output_dir"] = str(run_dir / "output")
    base.setdefault("rag", {}).setdefault("loader", {})["file_types"] = list(
        _SUPPORTED_FILE_TYPES
    )
    if embedding_provider:
        embedding_cfg = base.setdefault("rag", {}).setdefault("embedding", {})
        embedding_cfg["provider"] = embedding_provider
        if embedding_model_name is not None:
            embedding_cfg["model_name"] = embedding_model_name
    base.setdefault("agent", {}).setdefault("chatbot", {})["enabled"] = True
    base["artifact_policy"] = {"on_existing": "overwrite"}

    return base


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────


def create_and_ingest(
    raw_docs_source_dir: str,
    *,
    embedding_provider: str | None = None,
    embedding_model_name: str | None = None,
) -> dict[str, Any]:
    """원본 문서 디렉토리로 새 run을 생성하고 RAG ingest를 실행합니다.

    Args:
        raw_docs_source_dir: 원본 문서가 이미 저장된 디렉토리 경로
        embedding_provider: run config에 덮어쓸 embedding provider. None이면 streamlit.yaml 상속값을 사용
        embedding_model_name: run config에 덮어쓸 embedding model_name

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

        config = _build_streamlit_config(
            run_id,
            embedding_provider=embedding_provider,
            embedding_model_name=embedding_model_name,
        )
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


def _build_chatbot(run_id: str) -> Any:
    from src.artifacts import resolve_experiment_dir
    from src.rag.chatbot import build_chatbot_from_config

    config_path = _run_dir(run_id) / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Run config not found: {config_path}")

    config = load_config(config_path)
    output_dir = resolve_experiment_dir(_PROJECT_ROOT, config)
    bot = build_chatbot_from_config(config)
    bot.load_document_context(output_dir)
    return bot


def _filter_bot_documents(bot: Any, selected_doc_ids: list[str] | None) -> bool:
    if not selected_doc_ids:
        return True

    doc_ids = set(selected_doc_ids)
    bot.chunks = [c for c in bot.chunks if c.get("document_id") in doc_ids]
    chunk_ids = {c.get("chunk_id") for c in bot.chunks}
    bot.embeddings = [
        e for e in bot.embeddings if e.get("chunk_id") in chunk_ids
    ]
    return bool(bot.chunks)


def _collect_citations(bot: Any, tool_used: str | list[str] | None) -> list[dict[str, Any]]:
    result = _get_state_result(bot, tool_used)
    if result is None:
        return []
    return _dedupe_citations(list(result.citations))


def _get_state_result(bot: Any, tool_used: str | list[str] | None) -> Any | None:
    if not tool_used:
        return None
    tool_name = tool_used[-1] if isinstance(tool_used, list) else tool_used
    if tool_name in bot.state:
        return bot.state[tool_name]
    return None


def _dedupe_citations(citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for citation in citations:
        key = _citation_display_key(citation)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(citation)
    return deduped


def _citation_display_key(citation: dict[str, Any]) -> str:
    page = citation.get("page", citation.get("page_start", ""))
    section = citation.get("section", "")
    source = citation.get("source_path", "")
    return f"{source}|{page}|{section}"


def _format_structured_output(structured: dict[str, Any] | None) -> str:
    if not structured:
        return ""

    lines: list[str] = []
    for key, value in structured.items():
        if isinstance(value, list):
            lines.append(f"{key}")
            if value:
                for item in value:
                    lines.append(f"- {item}")
            else:
                lines.append("- 명시되지 않음")
        elif value in (None, ""):
            lines.append(f"{key}: 명시되지 않음")
        else:
            lines.append(f"{key}: {value}")
        lines.append("")
    return "\n".join(lines).strip()


def _strip_source_block(reply: str) -> str:
    marker = "\n\n[출처]\n"
    if marker in reply:
        return reply.split(marker, 1)[0].rstrip()
    return reply


def _display_reply(raw_reply: str, structured: dict[str, Any] | None = None) -> str:
    structured_reply = _format_structured_output(structured)
    if structured_reply:
        return structured_reply
    return _strip_source_block(raw_reply)


def _execute_tool(bot: Any, tool_name: str, question: str) -> Any:
    tool = bot.tools.get(tool_name)
    if tool is None:
        available = ", ".join(bot.tools.keys())
        raise ValueError(f"Unknown tool: {tool_name}. Available tools: {available}")

    for dep_name in tool.input_from:
        if dep_name in bot.state:
            continue
        dep_tool = bot.tools.get(dep_name)
        if dep_tool is not None:
            bot.state[dep_name] = bot._run_tool_with_retry(dep_tool, question)

    result = bot._run_tool_with_retry(tool, question)
    bot.state[tool_name] = result
    return result


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
        structured_output = None
        if tool_used:
            tool_name = tool_used[-1] if isinstance(tool_used, list) else tool_used
            if tool_name in bot.state:
                tool_result = bot.state[tool_name]
                citations = _dedupe_citations(list(tool_result.citations))
                structured_output = tool_result.structured_output

        return {
            "reply": _display_reply(response.get("reply", ""), structured_output),
            "tool_used": tool_used,
            "structured_output": structured_output,
            "citations": citations,
            "status": (response.get("tool_result") or {}).get("status", "unknown"),
            "duration_ms": (response.get("tool_result") or {}).get("duration_ms", 0),
            "error": None,
        }

    except Exception as exc:
        return {
            "reply": "",
            "tool_used": None,
            "structured_output": None,
            "citations": [],
            "status": "error",
            "duration_ms": 0,
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
    try:
        bot = _get_or_build_chatbot(run_id) if not selected_doc_ids else _build_chatbot(run_id)
        if not _filter_bot_documents(bot, selected_doc_ids):
            return {
                "reply": "선택한 문서에 해당하는 분석 데이터가 없습니다.",
                "tool_used": None,
                "structured_output": None,
                "citations": [],
                "status": "not_found",
                "duration_ms": 0,
                "error": None,
            }

        response = bot.chat(question)
        tool_result = _get_state_result(bot, response.get("tool_used"))
        structured_output = getattr(tool_result, "structured_output", None)
        citations = _dedupe_citations(list(getattr(tool_result, "citations", []))) if tool_result else []

        return {
            "reply": _display_reply(response.get("reply", ""), structured_output),
            "tool_used": response.get("tool_used"),
            "structured_output": structured_output,
            "citations": citations,
            "status": (response.get("tool_result") or {}).get("status", "unknown"),
            "duration_ms": (response.get("tool_result") or {}).get("duration_ms", 0),
            "error": None,
        }
    except Exception as exc:
        return {
            "reply": "",
            "tool_used": None,
            "structured_output": None,
            "citations": [],
            "status": "error",
            "duration_ms": 0,
            "error": str(exc),
        }


def run_tool(
    run_id: str,
    tool_name: str,
    question: str,
    selected_doc_ids: list[str] | None = None,
) -> dict[str, Any]:
    """지정한 Tool을 명시적으로 실행합니다."""
    started = time.perf_counter()
    try:
        bot = _build_chatbot(run_id)
        if not _filter_bot_documents(bot, selected_doc_ids):
            return {
                "reply": "선택한 문서에 해당하는 분석 데이터가 없습니다.",
                "tool_used": tool_name,
                "structured_output": None,
                "citations": [],
                "status": "not_found",
                "duration_ms": 0,
                "error": None,
            }

        result = _execute_tool(bot, tool_name, question)
        reply = _display_reply(bot._format_tool_result(result), result.structured_output)
        return {
            "reply": reply,
            "tool_used": tool_name,
            "structured_output": result.structured_output,
            "citations": _dedupe_citations(list(result.citations)),
            "status": result.status,
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "error": None,
        }
    except Exception as exc:
        return {
            "reply": "",
            "tool_used": tool_name,
            "structured_output": None,
            "citations": [],
            "status": "error",
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "error": str(exc),
        }


def summarize(run_id: str, selected_doc_ids: list[str] | None = None) -> dict[str, Any]:
    """선택 문서의 핵심 내용을 요약합니다."""
    return run_tool(
        run_id,
        "extract_facts",
        "이 RFP 문서의 핵심 내용을 요약해줘.",
        selected_doc_ids,
    )


def extract_requirements(
    run_id: str,
    selected_doc_ids: list[str] | None = None,
) -> dict[str, Any]:
    """선택 문서의 참가자격과 제출서류를 추출합니다."""
    return run_tool(
        run_id,
        "extract_requirements",
        "참가자격과 제출서류를 추출해서 보여줘.",
        selected_doc_ids,
    )


def compare(run_id: str, selected_doc_ids: list[str] | None = None) -> dict[str, Any]:
    """선택 문서를 예산, 기간, 자격요건 기준으로 비교합니다."""
    return run_tool(
        run_id,
        "compare_rfps",
        "선택된 RFP 문서들을 예산, 기간, 자격요건 기준으로 비교해줘.",
        selected_doc_ids,
    )


def get_documents(run_id: str) -> list[dict[str, Any]]:
    """chunks.csv에서 문서 목록을 추출합니다.

    Returns:
        [{"document_id": str, "title": str, "source_path": str, "chunk_count": int}, ...]
    """
    output_dir = _output_dir(run_id)
    chunks_path = output_dir / "chunks.csv"
    if not chunks_path.exists():
        return []

    rows = _read_csv_rows(chunks_path)
    document_rows = _read_csv_rows(output_dir / "parsed_documents.csv")
    meta_by_doc_id = {
        row.get("document_id", ""): row
        for row in document_rows
        if row.get("document_id")
    }

    docs: dict[str, dict[str, Any]] = {}
    for row in rows:
        doc_id = row.get("document_id", "unknown")
        meta = meta_by_doc_id.get(doc_id, {})
        source_path = meta.get("source_path") or row.get("source_path", "")
        title = meta.get("title") or Path(source_path).stem or doc_id
        if doc_id not in docs:
            docs[doc_id] = {
                "document_id": doc_id,
                "title": title,
                "source_path": source_path,
                "chunk_count": 0,
            }
        docs[doc_id]["chunk_count"] += 1

    return list(docs.values())


def get_citation(run_id: str, chunk_id: str) -> dict[str, Any] | None:
    """chunk_id에 해당하는 citation 원문을 반환합니다."""
    for row in _read_csv_rows(_output_dir(run_id) / "chunks.csv"):
        if row.get("chunk_id") == chunk_id:
            return dict(row)
    return None


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

        docs_count = len(get_documents(run_id))

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
