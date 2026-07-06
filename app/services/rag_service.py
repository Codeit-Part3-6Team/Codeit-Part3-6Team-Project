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
import logging
import threading
import time
import shutil
import sys
import uuid
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any

logger = logging.getLogger("rag_service")

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.config import load_config
from src.rag.pipeline import run_rag_ingest
from . import sqlite_store
from .paths import streamlit_experiments_dir

_STREAMLIT_EXPERIMENTS = streamlit_experiments_dir()
# 전용 streamlit 템플릿 사용 (base_config 상속으로 config_final/agent_lplus 포함)
_TEMPLATE_CONFIG_PATH = (
    _PROJECT_ROOT / "configs" / "experiments" / "rag" / "streamlit.yaml"
)

# ── run_id별 챗봇 인스턴스 캐시 ──
_chatbot_cache: dict[str, Any] = {}
_chatbot_lock = threading.Lock()


def _service_error(error_code: str, message: str, exc: Exception | None = None) -> dict[str, Any]:
    if exc:
        logger.error("[%s] %s: %s", error_code, message, exc)
    else:
        logger.warning("[%s] %s", error_code, message)
    return {
        "reply": "",
        "tool_used": None,
        "structured_output": None,
        "citations": [],
        "status": "error",
        "duration_ms": 0,
        "error": message,
        "error_code": error_code,
    }


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


def _build_streamlit_config(run_id: str) -> dict[str, Any]:
    """streamlit.yaml 템플릿을 로드해 run별 경로만 덮어씁니다.

    base_config 상속으로 config_final.yaml → agent_lplus.yaml 설정을
    그대로 가져오며, paths와 서비스용 Chroma 경로만 run_id 기반으로 바꿉니다.
    """
    base = load_config(_TEMPLATE_CONFIG_PATH)
    run_dir = _run_dir(run_id)

    base["experiment"]["name"] = f"streamlit-{run_id}"
    base["paths"]["raw_docs_dir"] = str(run_dir / "raw_docs")
    base["paths"]["output_dir"] = str(run_dir / "output")
    base.setdefault("agent", {}).setdefault("chatbot", {})["enabled"] = True
    base["artifact_policy"] = {"on_existing": "overwrite"}

    return base


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────


def create_and_ingest(raw_docs_source_dir: str, async_mode: bool = True) -> dict[str, Any]:
    """원본 문서 디렉토리로 새 run을 생성하고 RAG ingest를 실행합니다.

    Args:
        raw_docs_source_dir: 원본 문서가 이미 저장된 디렉토리 경로
        async_mode: True이면 백그라운드로 ingest 실행 후 즉시 반환

    Returns:
        {
            "run_id": str,
            "status": "ready" | "processing" | "failed",
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
            "documents": 0, "chunks": 0, "embeddings": 0,
            "config_path": None, "output_dir": None,
            "error": "업로드된 파일이 없습니다.",
        }

    config = _build_streamlit_config(run_id)
    config_path = run_dir / "config.yaml"
    _write_yaml(config_path, config)

    sqlite_store.insert_run(run_id, status="running", config_path=str(config_path), output_dir=str(output_dir))

    if async_mode:
        def _ingest_worker():
            try:
                result = run_rag_ingest(str(config_path), str(_PROJECT_ROOT))
                sqlite_store.update_run_status(run_id, "ready", result.get("documents", 0), result.get("chunks", 0))
                docs = get_documents(run_id)
                if docs:
                    sqlite_store.upsert_documents(run_id, docs)
            except Exception as exc:
                logger.error("Async ingest failed for %s: %s", run_id, exc)
                sqlite_store.update_run_status(run_id, "failed")

        threading.Thread(target=_ingest_worker, daemon=True).start()
        return {
            "run_id": run_id,
            "status": "processing",
            "documents": 0, "chunks": 0, "embeddings": 0,
            "config_path": str(config_path), "output_dir": str(output_dir),
            "error": None,
        }

    result = run_rag_ingest(str(config_path), str(_PROJECT_ROOT))
    sqlite_store.update_run_status(run_id, "ready", document_count=result.get("documents", 0), chunk_count=result.get("chunks", 0))
    docs = get_documents(run_id)
    if docs:
        sqlite_store.upsert_documents(run_id, docs)

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


def _get_or_build_chatbot(run_id: str) -> Any:
    """run_id에 해당하는 ChatbotRunner를 로딩하거나 생성합니다 (Thread-safe)."""
    with _chatbot_lock:
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
    bot._run_id = run_id

    with _chatbot_lock:
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
    bot._run_id = run_id
    return bot


def _get_chatbot_for_filter(run_id: str, selected_doc_ids: list[str] | None) -> Any:
    """선택 문서 필터에 맞는 챗봇을 반환합니다.

    Chroma는 retriever filter만 바꾸면 되므로 run_id별 캐시를 재사용합니다.
    CSV/JSONL 메모리 경로는 chunks를 직접 잘라내야 하므로 임시 챗봇을 씁니다.
    """
    bot = _get_or_build_chatbot(run_id)
    if not selected_doc_ids or getattr(bot, "_use_chroma", False):
        return bot
    return _build_chatbot(run_id)


def _filter_bot_documents(bot: Any, selected_doc_ids: list[str] | None) -> bool:
    bot._selected_doc_ids = list(selected_doc_ids or [])

    if getattr(bot, "_use_chroma", False):
        for tool in bot.tools.values():
            if tool.retriever_cfg.get("method") == "chroma":
                if selected_doc_ids:
                    tool.retriever_cfg["document_ids"] = list(selected_doc_ids)
                else:
                    tool.retriever_cfg.pop("document_ids", None)
        return True

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

    total = len(structured)
    missing: list[str] = []
    lines: list[str] = []
    for key, value in structured.items():
        if isinstance(value, list):
            lines.append(f"{key}")
            if value:
                for item in value:
                    lines.append(f"- {item}")
            else:
                lines.append("- 명시되지 않음")
                missing.append(key)
        elif value in (None, ""):
            lines.append(f"{key}: 명시되지 않음")
            missing.append(key)
        else:
            lines.append(f"{key}: {value}")
        lines.append("")

    result = "\n".join(lines).strip()

    if missing and len(missing) / total > 0.3:
        missing_fields = ", ".join(f"'{m}'" for m in missing)
        result += f"\n\n※ {missing_fields} 항목은 문서에 명시되지 않았습니다."

    return result


def _strip_source_block(reply: str) -> str:
    marker = "\n\n[출처]\n"
    if marker in reply:
        return reply.split(marker, 1)[0].rstrip()
    return reply


def _display_reply(raw_reply: str, structured: dict[str, Any] | None = None) -> str:
    reply = _strip_source_block(raw_reply)
    structured_reply = _format_structured_output(structured)
    if reply:
        return reply
    if structured_reply:
        return structured_reply
    return reply


def _format_doc_fact_for_compare(title: str, structured: dict[str, Any] | None, fallback: str) -> str:
    if not structured:
        return f"문서명: {title}\n{_strip_source_block(fallback).strip() or '요약 정보를 추출하지 못했습니다.'}"

    fields = [
        ("문서명", title),
        ("사업명", structured.get("사업명", "명시되지 않음")),
        ("발주기관", structured.get("발주기관", "명시되지 않음")),
        ("사업예산", structured.get("사업예산", "명시되지 않음")),
        ("사업기간", structured.get("사업기간", "명시되지 않음")),
        ("제출마감", structured.get("제출마감", "명시되지 않음")),
    ]
    lines = [f"{key}: {value}" for key, value in fields]
    requirements = structured.get("자격요건")
    if isinstance(requirements, list) and requirements:
        lines.append("자격요건: " + "; ".join(str(item) for item in requirements))
    elif requirements:
        lines.append(f"자격요건: {requirements}")
    return "\n".join(lines)


def _compare_selected_documents_by_facts(
    run_id: str,
    selected_doc_ids: list[str],
) -> dict[str, Any]:
    started = time.perf_counter()
    docs_by_id = {doc["document_id"]: doc for doc in get_documents(run_id)}
    doc_summaries: list[str] = []
    citations: list[dict[str, Any]] = []
    errors: list[str] = []

    for doc_id in selected_doc_ids:
        title = docs_by_id.get(doc_id, {}).get("title") or doc_id
        response = summarize(run_id, [doc_id])
        if response.get("error"):
            errors.append(f"{title}: {response['error']}")
        doc_summaries.append(
            _format_doc_fact_for_compare(
                title,
                response.get("structured_output"),
                response.get("reply", ""),
            )
        )
        citations.extend(response.get("citations") or [])

    comparison_text = (
        f"선택한 {len(selected_doc_ids)}개 문서를 모두 포함해 문서별 핵심 정보를 같은 기준으로 정리했습니다.\n\n"
        + "\n\n---\n\n".join(doc_summaries)
    )
    structured = {
        "문서목록": [docs_by_id.get(doc_id, {}).get("title") or doc_id for doc_id in selected_doc_ids],
        "비교결과": comparison_text,
    }
    return {
        "reply": _format_structured_output(structured),
        "tool_used": "compare_rfps",
        "structured_output": structured,
        "citations": _dedupe_citations(citations),
        "status": "partial" if errors else "ok",
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "error": "\n".join(errors) if errors else None,
    }


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
    """챗봇에게 질문하고 답변 + citation을 반환합니다."""
    try:
        bot = _get_or_build_chatbot(run_id)
        _filter_bot_documents(bot, None)
        response = bot.chat(question)

        citations = _dedupe_citations(list(response.get("citations") or []))
        structured_output = response.get("structured_output")

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
        return _service_error("ASK_FAILED", "답변 생성 중 오류가 발생했습니다.", exc)


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
        bot = _get_chatbot_for_filter(run_id, selected_doc_ids)
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
        structured_output = response.get("structured_output")
        citations = _dedupe_citations(list(response.get("citations") or []))

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
        return _service_error("ASK_FILTER_FAILED", "답변 생성 중 오류가 발생했습니다.", exc)


def run_tool(
    run_id: str,
    tool_name: str,
    question: str,
    selected_doc_ids: list[str] | None = None,
) -> dict[str, Any]:
    """지정한 Tool을 명시적으로 실행합니다."""
    started = time.perf_counter()
    try:
        bot = _get_chatbot_for_filter(run_id, selected_doc_ids)
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
    if selected_doc_ids and len(selected_doc_ids) >= 2:
        return _compare_selected_documents_by_facts(run_id, selected_doc_ids)

    return run_tool(
        run_id,
        "compare_rfps",
        "선택된 RFP 문서들을 예산, 기간, 자격요건 기준으로 비교해줘.",
        selected_doc_ids,
    )


def get_documents(run_id: str) -> list[dict[str, Any]]:
    """SQLite 또는 CSV에서 문서 목록을 조회합니다."""
    db_docs = sqlite_store.get_documents(run_id)

    output_dir = _output_dir(run_id)
    chunks_path = output_dir / "chunks.csv"
    if not chunks_path.exists():
        return db_docs

    rows = _read_csv_rows(chunks_path)
    document_rows = _read_csv_rows(output_dir / "parsed_documents.csv")
    meta_by_doc_id = {
        row.get("document_id", ""): row
        for row in document_rows
        if row.get("document_id")
    }

    docs: dict[str, dict[str, Any]] = {
        str(doc.get("document_id")): dict(doc)
        for doc in db_docs
        if doc.get("document_id")
    }
    for doc in docs.values():
        doc["chunk_count"] = 0
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
        docs[doc_id]["title"] = docs[doc_id].get("title") or title
        docs[doc_id]["source_path"] = docs[doc_id].get("source_path") or source_path
        _enrich_document_card_metadata(docs[doc_id], meta, row)
        docs[doc_id]["chunk_count"] += 1

    return list(docs.values())


def _enrich_document_card_metadata(
    document: dict[str, Any],
    parsed_row: dict[str, str],
    chunk_row: dict[str, str],
) -> None:
    """문서 카드에 표시할 발주기관/금액/요약 메타데이터를 채웁니다."""
    org = parsed_row.get("meta_발주 기관", "")
    amount = parsed_row.get("meta_사업 금액", "")
    summary = parsed_row.get("meta_사업 요약", "")
    period = _first_present(
        parsed_row,
        [
            "meta_사업 기간",
            "meta_사업기간",
            "meta_계약 기간",
            "meta_계약기간",
            "meta_용역 기간",
            "meta_용역기간",
            "meta_수행 기간",
            "meta_수행기간",
        ],
    )
    deadline = _first_present(
        parsed_row,
        [
            "meta_제출 마감",
            "meta_제출마감",
            "meta_제출 마감일",
            "meta_제출마감일",
            "meta_입찰 마감",
            "meta_입찰마감",
            "meta_입찰 마감일",
            "meta_입찰마감일",
            "meta_입찰 참여 마감일",
            "meta_입찰참여마감일",
            "meta_마감일",
            "meta_마감일시",
        ],
    )
    ftype = parsed_row.get("meta_파일형식", "")

    if not (org and amount and period and deadline):
        preamble = _extract_chunk_preamble(chunk_row.get("text", ""))
        org = org or preamble.get("발주기관", "")
        amount = amount or preamble.get("사업금액", "")
        period = period or preamble.get("사업기간", "") or preamble.get("계약기간", "")
        deadline = deadline or preamble.get("제출마감", "") or preamble.get("입찰마감", "") or preamble.get("입찰참여마감", "")

    period = period or _extract_labeled_value(summary, ["사업기간", "계약기간", "용역기간", "수행기간"])
    deadline = deadline or _extract_labeled_value(summary, ["제출마감", "제출마감일", "입찰마감", "입찰마감일", "입찰참여마감", "입찰참여마감일", "마감일", "마감일시"])

    if org:
        document.setdefault("org", org)
    if amount:
        document.setdefault("amount", _format_amount_label(amount))
    if summary:
        document.setdefault("summary", summary)
    if period:
        document.setdefault("period", period)
    if deadline:
        document.setdefault("deadline", deadline)
    if ftype:
        document.setdefault("ftype", ftype)


def _first_present(row: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def _extract_labeled_value(text: str, labels: list[str]) -> str:
    """요약문 안의 '사업기간: ...' 같은 짧은 라벨 값을 가져옵니다."""
    import re

    if not text:
        return ""
    for label in labels:
        pattern = rf"{re.escape(label)}\s*[:：]\s*([^\n\-]+)"
        match = re.search(pattern, text)
        if match:
            value = match.group(1).strip(" .·,;")
            if value:
                return value
    return ""


def _extract_chunk_preamble(text: str) -> dict[str, str]:
    if not text.startswith("[") or "]" not in text:
        return {}
    raw = text[1:text.find("]")]
    items: dict[str, str] = {}
    for part in raw.split("|"):
        key, sep, value = part.partition(":")
        if sep:
            items[key.strip()] = value.strip()
    return items


def _format_amount_label(value: str) -> str:
    stripped = str(value or "").strip()
    if not stripped:
        return ""
    if stripped.endswith("원"):
        return stripped
    try:
        return f"{int(float(stripped)):,}원"
    except ValueError:
        return stripped


def get_citation(run_id: str, chunk_id: str) -> dict[str, Any] | None:
    """chunk_id에 해당하는 citation 원문을 반환합니다."""
    for row in _read_csv_rows(_output_dir(run_id) / "chunks.csv"):
        if row.get("chunk_id") == chunk_id:
            return dict(row)
    return None


def find_field_candidates(
    run_id: str,
    document_ids: list[str] | None,
    field: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """사업기간/제출마감 후보 문장을 chunks.csv에서 빠르게 검색합니다."""
    keywords = _field_candidate_keywords(field)
    if not keywords:
        return []

    doc_filter = {str(doc_id) for doc_id in (document_ids or []) if doc_id}
    candidates: list[dict[str, Any]] = []
    seen_texts: set[str] = set()
    for row in _read_csv_rows(_output_dir(run_id) / "chunks.csv"):
        doc_id = str(row.get("document_id") or "")
        if doc_filter and doc_id not in doc_filter:
            continue
        text = _strip_chunk_preamble(str(row.get("text") or ""))
        for keyword in keywords:
            if keyword not in text:
                continue
            sentence = _extract_candidate_sentence(text, keyword)
            if not sentence or sentence in seen_texts:
                continue
            seen_texts.add(sentence)
            candidates.append({
                "chunk_id": row.get("chunk_id", ""),
                "document_id": doc_id,
                "source_path": row.get("source_path", ""),
                "page": row.get("page_start") or row.get("page") or "",
                "section": row.get("section") or "본문",
                "text": sentence,
            })
            break
        if len(candidates) >= limit:
            break
    return candidates


def _field_candidate_keywords(field: str) -> list[str]:
    if field == "사업기간":
        return [
            "사업기간", "계약기간", "용역기간", "수행기간", "과업기간",
            "착수일", "계약일", "완료일", "계약체결일로부터", "착수일로부터",
        ]
    if field == "제출마감":
        return [
            "제출마감", "입찰마감", "접수마감", "마감일시", "제출기한",
            "제안서 제출", "가격입찰", "전자입찰", "개찰",
        ]
    return []


def _strip_chunk_preamble(text: str) -> str:
    stripped = str(text or "").strip()
    if stripped.startswith("[") and "]" in stripped[:500]:
        return stripped[stripped.find("]") + 1:].strip()
    return stripped


def _extract_candidate_sentence(text: str, keyword: str) -> str:
    import re

    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    index = normalized.find(keyword)
    if index < 0:
        return ""

    delimiters = ".。\n\r;"
    start = max(normalized.rfind(delim, 0, index) for delim in delimiters)
    start = 0 if start < 0 else start + 1
    end_positions = [normalized.find(delim, index + len(keyword)) for delim in delimiters]
    end_positions = [pos for pos in end_positions if pos >= 0]
    end = min(end_positions) + 1 if end_positions else len(normalized)
    sentence = normalized[start:end].strip(" -•*.;")
    if len(sentence) > 220:
        sentence = sentence[:217].rstrip() + "..."
    return sentence


def list_runs() -> list[dict[str, Any]]:
    """SQLite + 파일시스템 run 목록을 병합하여 반환합니다."""
    db_runs = {r["run_id"]: r for r in sqlite_store.list_runs()}

    # 파일시스템 run도 병합
    fs_runs: dict[str, dict[str, Any]] = {}
    if _STREAMLIT_EXPERIMENTS.exists():
        for run_dir in sorted(_STREAMLIT_EXPERIMENTS.iterdir(), reverse=True):
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
            else:
                status = "running"

            fs_runs[run_id] = {
                "run_id": run_id,
                "created_at": datetime.fromtimestamp(run_dir.stat().st_mtime).isoformat(),
                "status": status,
                "documents": len(get_documents(run_id)),
            }

    # DB 우선 병합
    merged = dict(fs_runs)
    merged.update(db_runs)
    return sorted(merged.values(), key=lambda r: r.get("created_at", ""), reverse=True)


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
    """챗봇 캐시와 대화 기록을 초기화합니다."""
    if run_id:
        _chatbot_cache.pop(run_id, None)
        sqlite_store.clear_chat_history(run_id)
    else:
        _chatbot_cache.clear()
        sqlite_store.clear_chat_history()


def get_ingest_progress(run_id: str) -> dict[str, Any]:
    """ingest 진행률을 반환합니다.

    Returns:
        {"stage": "documents"|"chunks"|"embeddings"|"ready"|"unknown",
         "progress": float (0.0 ~ 1.0),
         "message": str}
    """
    output_dir = _output_dir(run_id)
    checkpoint_path = output_dir / "rag_ingest_checkpoint.json"
    status_path = output_dir / "run_status.json"

    # SQLite 실패 상태 우선 확인
    db_run = sqlite_store.get_run(run_id)
    if db_run and db_run.get("status") == "failed":
        return {"stage": "failed", "progress": 1.0, "message": "분석 실패", "error": "ingest 처리 중 오류가 발생했습니다."}

    if status_path.exists():
        try:
            data = json.loads(status_path.read_text(encoding="utf-8"))
            if data.get("status") == "success":
                return {"stage": "ready", "progress": 1.0, "message": "분석 완료"}
            if data.get("status") in ("failed", "error"):
                return {"stage": "failed", "progress": 1.0, "message": "분석 실패", "error": str(data.get("result", ""))}
        except Exception:
            pass

    if checkpoint_path.exists():
        try:
            data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            stage = data.get("stage", "unknown")
            stage_map = {"documents": 0.33, "chunks": 0.66, "embeddings": 0.9}
            return {
                "stage": stage,
                "progress": stage_map.get(stage, 0.0),
                "message": {"documents": "문서 파싱 중...", "chunks": "청크 분할 중...", "embeddings": "임베딩 생성 중..."}.get(stage, "처리 중..."),
            }
        except Exception:
            pass

    return {"stage": "unknown", "progress": 0.0, "message": "대기 중..."}
