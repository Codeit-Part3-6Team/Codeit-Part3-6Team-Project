"""
프론트엔드 ↔ RAG 백엔드 어댑터 (내부 문서 corpus 버전)
=======================================================
views/ 화면 코드와 services/rag_service.py 사이의 '번역 계층'입니다.

이 서비스는 '내부에 미리 인덱싱된 RFP 문서(약 98건)'를 대상으로 합니다.
사용자는 파일을 올리지 않고, 목록에서 문서를 골라 요약·비교·질문합니다.

역할 4가지:
  1) RAG 백엔드 가용성 감지 (지연 import + 실패 원인 분류)
     - rag_service.py 는 VM의 src/ 패키지를 import 하므로, src/ 가 없는
       로컬(Windows)에서는 import 가 실패함 → Mock 모드로 자동 폴백.
     - 단, '예상된 실패(src 없음)'와 '예상 밖 오류(버그/의존성 누락)'를 구분해
       후자는 화면 배너에 분명히 드러냅니다(문제를 조용히 삼키지 않음).
  2) 내부 corpus run 해석
     - list_runs() 중 문서가 가장 많은 ready run 을 '내부 문서 인덱스'로 선택.
       (환경변수 RAG_CORPUS_RUN_ID 로 특정 run 고정 가능)
  3) 데이터 형태 변환
     - rag_service 응답을 UI 형태({"meta","summary","requirements"} 등)로 변환.
  4) 에러의 UI 친화적 처리
     - 백엔드 예외를 화면까지 던지지 않고 {"error": ...} 로 감싸 반환.

사용법 (views 에서):
    from services.frontend_adapter import (
        backend_mode, internal_corpus, analyze_selection, compare_selection, chat_ask,
    )
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# ── 백엔드 가용성 감지 (지연 import + 1회 캐시) ──────────────────────────────
_rag: Any = None               # 성공 시 rag_service 모듈
_rag_checked = False           # 감지를 딱 한 번만 수행
_rag_status = "unknown"        # "rag" | "local" | "missing_dep" | "error"
_rag_error: str | None = None  # 실패 사유


def _load_rag():
    """rag_service 를 지연 import. 실패 원인을 분류해 _rag_status 에 기록."""
    global _rag, _rag_checked, _rag_status, _rag_error
    if _rag_checked:
        return _rag
    _rag_checked = True

    # 환경변수로 명시적 모드 전환 (RAG_MODE=mock → 강제 Mock)
    forced_mode = os.environ.get("RAG_MODE", "").lower()
    if forced_mode == "mock":
        _rag = None
        _rag_status = "local"
        _rag_error = "RAG_MODE=mock 으로 강제 지정됨"
        return _rag
    if forced_mode == "rag":
        pass  # 강제 RAG 모드 — import 실패 시 fatal로 처리

    try:
        from services import rag_service  # 여기서 src.* import 가 실행됨
        _rag = rag_service
        _rag_status = "rag"
    except ModuleNotFoundError as exc:
        # F1: 폴백을 좁힘 — '왜 실패했는지'를 구분한다.
        _rag = None
        top = (exc.name or "").split(".")[0]
        if top == "src":
            # 예상된 상황: 로컬에 백엔드 패키지(src/)가 없음 → 정상적인 Mock 모드
            _rag_status = "local"
            _rag_error = "백엔드(src/) 미탑재 로컬 환경 → Mock 데이터 사용"
        else:
            # 예상 밖: VM 인데 의존 패키지가 없다는 등 — 조용히 넘기지 않고 표시
            _rag_status = "missing_dep"
            _rag_error = f"필요한 모듈을 찾을 수 없음: {exc.name}"
    except Exception as exc:
        # 예상 밖의 실제 오류(예: rag_service 버그). 앱은 죽이지 않되 배너로 드러냄.
        _rag = None
        _rag_status = "error"
        _rag_error = f"백엔드 초기화 오류: {exc}"
    return _rag


def backend_mode() -> dict[str, Any]:
    """현재 백엔드 모드를 UI 에 알려줍니다.

    Returns:
        {"mode": "rag"|"mock", "healthy": bool, "detail": str}
        - healthy=False 는 '예상 밖 이유로 Mock 으로 떨어졌다'는 신호(🔴).
    """
    rag = _load_rag()
    if rag is not None:
        return {"mode": "rag", "healthy": True, "detail": "RAG 파이프라인 연결됨"}
    forced_mode = os.environ.get("RAG_MODE", "").lower()
    if forced_mode == "rag":
        return {"mode": "rag", "healthy": False,
                "detail": f"RAG_MODE=rag 강제 지정됐으나 백엔드 연결 실패 (사유: {_rag_error})"}
    if _rag_status == "local":
        return {"mode": "mock", "healthy": True,
                "detail": "RAG 미연결(로컬) → Mock 데이터로 미리보기"}
    return {"mode": "mock", "healthy": False,
            "detail": f"백엔드 연결 실패 → Mock 폴백 (사유: {_rag_error})"}


# ── structured_output → UI 데이터 변환 헬퍼 ─────────────────────────────────
_META_KEYS = ["사업명", "발주기관", "사업예산", "사업기간", "제출마감"]
_NOT_SPECIFIED = "명시되지 않음"


def _build_meta(structured: dict | None, title: str) -> dict[str, str]:
    """extract_facts 의 structured_output → 워크스페이스 '사업 개요' 카드 dict."""
    structured = structured or {}
    meta: dict[str, str] = {}
    for key in _META_KEYS:
        value = structured.get(key)
        if isinstance(value, list):
            value = "; ".join(str(v) for v in value) if value else None
        meta[key] = str(value) if value not in (None, "") else _NOT_SPECIFIED
    meta["문서"] = title
    return meta


def _flatten_requirements(structured: dict | None, reply: str) -> list[str]:
    """extract_requirements 결과 → '핵심 요구사항' 탭용 문자열 리스트."""
    items: list[str] = []
    if isinstance(structured, dict):
        for key, value in structured.items():
            if isinstance(value, list):
                items.extend(f"[{key}] {v}" for v in value if str(v).strip())
            elif value not in (None, "", _NOT_SPECIFIED):
                items.append(f"[{key}] {value}")
    if not items and reply:
        items = [line.lstrip("-• ").strip()
                 for line in reply.splitlines()
                 if line.strip().startswith(("-", "•"))]
    if not items and reply.strip():
        items = [reply.strip()]
    return items or ["문서에서 요구사항을 추출하지 못했습니다."]


def _citations_to_sources(citations: list[dict] | None) -> list[tuple[str, str]]:
    """rag_service citation dict → UI 출처 태그 (page_label, section) 튜플."""
    sources: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for c in citations or []:
        page = c.get("page") or c.get("page_start")
        page_label = f"p.{page}" if page not in (None, "", "?") else \
            (Path(str(c.get("source_path") or "")).name or "원문")
        section = str(c.get("section") or "본문")
        key = (page_label, section)
        if key in seen:
            continue
        seen.add(key)
        sources.append(key)
    return sources[:5]


# ──────────────────────────────────────────────────────────────────────
# Public API — views 가 호출하는 함수들
# ──────────────────────────────────────────────────────────────────────

def _rag_unavailable_error() -> dict[str, Any] | None:
    """RAG_MODE=rag 이면서 백엔드가 없는 경우 에러 반환, 아니면 None."""
    if os.environ.get("RAG_MODE", "").lower() == "rag":
        return {"mode": "rag", "error": "RAG_MODE=rag 로 설정되었으나 백엔드 연결에 실패했습니다."}
    return None


# 내부 corpus run 은 세션 내내 동일하므로 1회 해석 후 캐시.
_corpus_cache: dict[str, Any] | None = None


def internal_corpus(force_refresh: bool = False) -> dict[str, Any]:
    """내부 문서 인덱스(run)와 문서 목록을 반환합니다.

    Returns:
        {
          "mode": "rag" | "mock",
          "run_id": str | None,     # mock 이면 None
          "documents": [ {document_id, title, org?, amount?, chunk_count, ...}, ... ],
          "error": str | None,
        }
    """
    global _corpus_cache
    if _corpus_cache is not None and not force_refresh:
        return _corpus_cache

    rag = _load_rag()

    # ── Mock 경로: 내부 98개 문서 메타데이터로 목록 구성 ──
    if rag is None:
        if os.environ.get("RAG_MODE", "").lower() == "rag":
            _corpus_cache = {
                "mode": "rag", "run_id": None, "documents": [], "warning": None,
                "error": "RAG_MODE=rag 로 설정되었으나 백엔드 연결에 실패했습니다.",
            }
            return _corpus_cache
        from utils.mock_data import mock_documents
        _corpus_cache = {
            "mode": "mock",
            "run_id": None,
            "documents": mock_documents(),
            "warning": None,
            "error": None,
        }
        return _corpus_cache

    # ── 실제 RAG 경로: 문서가 가장 많은 run 을 내부 corpus 로 선택 ──
    #    (status 로 거르지 않음 — chunks.csv 가 있으면 조회 가능하고,
    #     예전 업로드 테스트로 남은 1건짜리 run 대신 실제 corpus 를 확실히 잡기 위해
    #     '문서 수 최다' 를 최우선 기준으로 삼는다.)
    try:
        forced = os.environ.get("RAG_CORPUS_RUN_ID")
        if forced:
            documents = rag.get_documents(forced)
            _corpus_cache = {
                "mode": "rag", "run_id": forced, "documents": documents,
                "warning": None,
                "error": None if documents else "지정된 corpus run 에 문서가 없습니다.",
            }
            return _corpus_cache

        runs = rag.list_runs()
        candidates = [r for r in runs if int(r.get("documents") or 0) > 0]

        if not candidates:
            _corpus_cache = {
                "mode": "rag", "run_id": None, "documents": [], "warning": None,
                "error": "인덱싱된 내부 문서 corpus 가 없습니다. "
                         "먼저 내부 문서 ingest(build_internal_corpus)를 실행해주세요.",
            }
            return _corpus_cache

        best = max(candidates, key=lambda r: int(r.get("documents") or 0))
        run_id = best["run_id"]
        documents = rag.get_documents(run_id)

        # 문서 수가 비정상적으로 적으면(예: 예전 업로드 테스트 찌꺼기 run) 경고.
        warning = None
        if 0 < len(documents) < 10:
            warning = (
                f"현재 선택된 인덱스에 문서가 {len(documents)}건뿐입니다. "
                "전체 내부 corpus(약 98건)가 아직 ingest되지 않았을 수 있어요. "
                "build_internal_corpus 로 원문 폴더를 한 번 인덱싱해주세요."
            )
        _corpus_cache = {
            "mode": "rag", "run_id": run_id, "documents": documents,
            "warning": warning,
            "error": None if documents else "문서 목록을 불러오지 못했습니다.",
        }
        return _corpus_cache

    except Exception as exc:
        _corpus_cache = {
            "mode": "rag", "run_id": None, "documents": [], "warning": None,
            "error": f"내부 문서 목록 조회 실패: {exc}",
        }
        return _corpus_cache


def analyze_selection(run_id: str | None,
                      doc_ids: list[str],
                      titles: list[str] | None = None) -> dict[str, Any]:
    """선택한 내부 문서(1건 이상)를 요약/요구사항 추출해 UI 형태로 반환합니다.

    업로드/ingest 가 없습니다. 이미 인덱싱된 corpus 에서 doc_ids 로 필터링해
    summarize / extract_requirements 를 호출합니다.

    Returns:
        {"mode", "run_id", "meta", "summary", "requirements",
         "sources": {"summary":[...], "requirements":[...]}, "error"}
    """
    rag = _load_rag()
    doc_ids = list(doc_ids or [])
    titles = titles or []

    # ── Mock 경로 ──
    if rag is None or not run_id:
        blocked = _rag_unavailable_error()
        if blocked:
            return blocked
        from utils.mock_data import mock_analyze_selection
        result = mock_analyze_selection(doc_ids, titles)
        return {
            "mode": "mock", "run_id": run_id,
            "meta": result["meta"],
            "summary": result["summary"],
            "summary_ok": True,
            "requirements": result["requirements"],
            "sources": {"summary": [], "requirements": []},
            "error": None,
        }

    # ── 실제 RAG 경로 ──
    if not doc_ids:
        return _analysis_error("선택된 문서가 없습니다.")

    try:
        summary_res = rag.summarize(run_id, doc_ids)
        req_res = rag.extract_requirements(run_id, doc_ids)
        errors = [e for e in (summary_res.get("error"), req_res.get("error")) if e]

        title = titles[0] if len(titles) == 1 else f"{len(doc_ids)}개 문서"
        structured = summary_res.get("structured_output")
        raw_summary = (summary_res.get("reply") or "").strip()
        summary_ok = _has_content(raw_summary)
        return {
            "mode": "rag", "run_id": run_id,
            "meta": _build_meta(structured, title),
            "summary": raw_summary,
            "summary_ok": summary_ok,   # 실질 내용이 있는지(빈 응답 sentinel 아닌지)
            "requirements": _flatten_requirements(
                req_res.get("structured_output"), req_res.get("reply") or ""),
            "sources": {
                "summary": _citations_to_sources(summary_res.get("citations")),
                "requirements": _citations_to_sources(req_res.get("citations")),
            },
            "error": " / ".join(errors) if errors else None,
        }
    except Exception as exc:
        return _analysis_error(str(exc))


# 백엔드가 내용 없이 돌려보내는 빈 응답 표식들
_EMPTY_MARKERS = {
    "", "(응답 없음)", "문서에서 확인하지 못했습니다.",
    "선택한 문서에 해당하는 분석 데이터가 없습니다.",
}


def _has_content(reply: str) -> bool:
    """요약 reply 가 실질 내용을 담고 있으면 True (빈 응답 sentinel 이면 False)."""
    return bool(reply) and reply.strip() not in _EMPTY_MARKERS


def _analysis_error(message: str) -> dict[str, Any]:
    return {
        "mode": "rag", "run_id": None,
        "meta": {}, "summary": "", "summary_ok": False, "requirements": [],
        "sources": {"summary": [], "requirements": []},
        "error": message,
    }


def compare_selection(run_id: str | None,
                      docs: list[dict]) -> dict[str, Any]:
    """선택한 문서 2건 이상을 비교합니다.

    Returns:
        {"mode", "summary": str, "reply": str, "rows": [dict]|None, "error"}
    """
    rag = _load_rag()
    docs = docs or []
    doc_ids = [d.get("document_id") for d in docs if d.get("document_id")]

    # ── Mock 경로: 표 형태 비교 ──
    if rag is None or not run_id:
        blocked = _rag_unavailable_error()
        if blocked:
            return blocked
        from utils.mock_data import mock_compare
        result = mock_compare(docs)
        return {"mode": "mock", "summary": result["summary"],
                "reply": "", "rows": result["rows"], "error": None}

    # ── 실제 RAG 경로 ──
    try:
        res = rag.compare(run_id, doc_ids)
        return {
            "mode": "rag",
            "summary": f"선택한 {len(doc_ids)}개 문서를 비교했습니다.",
            "reply": res.get("reply") or "",
            "rows": None,  # RAG 는 서술형 비교 텍스트를 reply 로 반환
            "error": res.get("error"),
        }
    except Exception as exc:
        return {"mode": "rag", "summary": "", "reply": "",
                "rows": None, "error": str(exc)}


def chat_ask(question: str, run_id: str | None,
             selected_doc_ids: list[str] | None = None,
             titles: list[str] | None = None) -> tuple[str, list[tuple[str, str]]]:
    """워크스페이스 채팅 질의. (answer, sources) 튜플을 반환합니다.

    run_id 가 있으면 실제 RAG(ask_with_document_filter), 없으면 Mock.
    """
    rag = _load_rag()

    if rag is None or not run_id:
        if os.environ.get("RAG_MODE", "").lower() == "rag":
            return ("RAG_MODE=rag 로 설정되었으나 백엔드 연결에 실패했습니다.", [])
        from utils.mock_data import mock_chat
        return mock_chat(question, titles)

    response = rag.ask_with_document_filter(run_id, question, selected_doc_ids)

    if response.get("error"):
        return (f"답변 생성 중 오류가 발생했습니다: {response['error']}", [])

    reply = response.get("reply") or "문서에서 확인하지 못했습니다."
    return (reply, _citations_to_sources(response.get("citations")))


def ingest_progress(run_id: str | None) -> dict[str, Any]:
    """ingest 진행률을 조회합니다."""
    rag = _load_rag()
    if rag is None or not run_id:
        return {"stage": "mock", "progress": 1.0, "message": "Mock 모드"}
    return rag.get_ingest_progress(run_id)
