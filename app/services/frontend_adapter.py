"""
프론트엔드 ↔ RAG 백엔드 어댑터
================================
views/ 화면 코드와 services/rag_service.py 사이의 '번역 계층'입니다.

역할 3가지:
  1) RAG 백엔드 사용 가능 여부 자동 감지
     - rag_service.py 는 VM의 src/ 패키지(src.config, src.rag.pipeline)를
       import 하므로, src/ 가 없는 로컬(Windows) 환경에서는 import 자체가 실패함.
     - import 를 "함수 호출 시점"으로 늦추고 실패하면 Mock 모드로 폴백.
       → 프론트 개발자는 로컬에서 UI 작업, VM에서는 실제 RAG 로 동작. 코드는 동일.
  2) 데이터 형태 변환
     - rag_service 응답({"reply", "structured_output", "citations", ...})을
       기존 UI 가 쓰는 형태({"meta", "summary", "requirements"}, (answer, sources))로 변환.
     - 덕분에 views/ 쪽 수정을 최소화하고, mock_data 와 실제 백엔드를 같은 모양으로 사용.
  3) 에러의 UI 친화적 처리
     - 백엔드 예외를 화면까지 던지지 않고 {"error": ...} 로 감싸서 반환.

사용법 (views 에서):
    from services.frontend_adapter import backend_mode, analyze_document, chat_ask
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

# ── 백엔드 가용성 감지 (지연 import + 1회 캐시) ──────────────────────────────
_rag: Any = None          # 성공 시 rag_service 모듈이 들어감
_rag_checked = False      # 감지를 딱 한 번만 수행
_rag_error: str | None = None  # 실패 사유 (디버깅 표시용)


def _load_rag():
    """rag_service 를 지연 import. src/ 가 없는 환경이면 None 유지."""
    global _rag, _rag_checked, _rag_error
    if _rag_checked:
        return _rag
    _rag_checked = True
    try:
        from services import rag_service  # src.* import 가 여기서 일어남
        _rag = rag_service
    except Exception as exc:  # ModuleNotFoundError 포함 모든 실패 → Mock 폴백
        _rag = None
        _rag_error = str(exc)
    return _rag


def backend_mode() -> dict[str, Any]:
    """현재 백엔드 모드를 UI 에 알려줍니다.

    Returns:
        {"mode": "rag" | "mock", "detail": str}
    """
    rag = _load_rag()
    if rag is not None:
        return {"mode": "rag", "detail": "RAG 파이프라인 연결됨"}
    return {"mode": "mock", "detail": f"RAG 미연결 → Mock 모드 (사유: {_rag_error})"}


# ── structured_output → UI 데이터 변환 헬퍼 ─────────────────────────────────
# extract_facts 도구가 돌려주는 구조화 키 (rag_service._format_doc_fact_for_compare 참조)
_META_KEYS = ["사업명", "발주기관", "사업예산", "사업기간", "제출마감"]
_NOT_SPECIFIED = "명시되지 않음"


def _build_meta(structured: dict | None, doc_name: str) -> dict[str, str]:
    """extract_facts 의 structured_output → 워크스페이스 '사업 개요' 카드 dict."""
    structured = structured or {}
    meta = {}
    for key in _META_KEYS:
        value = structured.get(key)
        if isinstance(value, list):
            value = "; ".join(str(v) for v in value) if value else None
        meta[key] = str(value) if value not in (None, "") else _NOT_SPECIFIED
    meta["문서"] = doc_name
    return meta


def _flatten_requirements(structured: dict | None, reply: str) -> list[str]:
    """extract_requirements 결과 → '핵심 요구사항' 탭용 문자열 리스트.

    structured_output 형태가 확정 전이라 방어적으로 처리:
      - dict 이면: 리스트 값은 "카테고리 · 항목"으로 평탄화, 문자열 값은 그대로
      - 그 외: reply 에서 '-' 로 시작하는 줄을 항목으로 사용
    """
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
    """rag_service citation dict → UI 출처 태그 (page_label, section) 튜플.

    workspace 채팅의 src-tag 렌더링 형식(📑 p.12 · 2.3 제출 안내)에 맞춥니다.
    """
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
    return sources[:5]  # 태그가 너무 길어지지 않게 상한


# ──────────────────────────────────────────────────────────────────────
# Public API — views 가 호출하는 함수들
# ──────────────────────────────────────────────────────────────────────

def analyze_document(file_name: str, file_bytes: bytes | None) -> dict[str, Any]:
    """문서 1건을 분석해 UI 가 쓰는 형태로 반환합니다.

    흐름 (README 의 'RAG 연결 계약' 1~5단계 그대로):
      1) 업로드 bytes 를 임시 디렉토리에 저장
      2) create_and_ingest(temp_dir) → run 생성 + 인덱싱
      3) run_id 반환 (호출측이 세션에 저장)
      4) summarize / extract_requirements 호출
      5) reply·structured_output·citations 를 UI dict 로 변환

    Args:
        file_name: 업로드 파일명 (샘플 체험이면 표시용 이름)
        file_bytes: 파일 내용. None 이면 실제 파일이 없다는 뜻 → Mock 처리.

    Returns:
        {
          "mode": "rag" | "mock",
          "run_id": str | None,
          "meta": dict, "summary": str, "requirements": [str],
          "sources": {"summary": [...], "requirements": [...]},
          "error": str | None,
        }
    """
    rag = _load_rag()

    # ── Mock 경로: 백엔드 미연결이거나 실제 파일이 없는 샘플 체험 ──
    if rag is None or file_bytes is None:
        from utils.mock_data import mock_analyze
        result = mock_analyze(file_name)
        return {
            "mode": "mock",
            "run_id": None,
            "meta": result["meta"],
            "summary": result["summary"],
            "requirements": result["requirements"],
            "sources": {"summary": [], "requirements": []},
            "error": None,
        }

    # ── 실제 RAG 경로 ──
    try:
        # 1) 임시 디렉토리에 저장 (create_and_ingest 가 run 폴더로 복사해 가므로
        #    with 블록이 끝나면 임시본은 지워져도 안전)
        with tempfile.TemporaryDirectory() as tmp:
            upload_dir = Path(tmp) / "uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            safe_name = Path(file_name).name  # 경로 조작 방지
            (upload_dir / safe_name).write_bytes(file_bytes)

            # 2) run 생성 + ingest (파싱→청킹→임베딩)
            ingest = rag.create_and_ingest(str(upload_dir))

        if ingest.get("status") != "ready":
            return _analysis_error(ingest.get("error") or "문서 인덱싱에 실패했습니다.")

        run_id = ingest["run_id"]

        # 4) 요약(extract_facts) + 요구사항(extract_requirements)
        summary_res = rag.summarize(run_id)
        req_res = rag.extract_requirements(run_id)

        # 부분 실패 허용: 한쪽이 죽어도 다른 쪽은 보여준다
        errors = [e for e in (summary_res.get("error"), req_res.get("error")) if e]

        # 5) UI 형태로 변환
        structured = summary_res.get("structured_output")
        return {
            "mode": "rag",
            "run_id": run_id,
            "meta": _build_meta(structured, safe_name),
            "summary": (
                summary_res.get("reply")
                or "요약을 생성하지 못했습니다. 대화형 탐색에서 직접 질문해보세요."
            ),
            "requirements": _flatten_requirements(
                req_res.get("structured_output"), req_res.get("reply") or ""
            ),
            "sources": {
                "summary": _citations_to_sources(summary_res.get("citations")),
                "requirements": _citations_to_sources(req_res.get("citations")),
            },
            "error": " / ".join(errors) if errors else None,
        }

    except Exception as exc:
        return _analysis_error(str(exc))


def _analysis_error(message: str) -> dict[str, Any]:
    return {
        "mode": "rag",
        "run_id": None,
        "meta": {}, "summary": "", "requirements": [],
        "sources": {"summary": [], "requirements": []},
        "error": message,
    }


def chat_ask(question: str, run_id: str | None,
             selected_doc_ids: list[str] | None = None) -> tuple[str, list[tuple[str, str]]]:
    """워크스페이스 채팅 질의. 기존 mock_chat 과 동일한 (answer, sources) 시그니처.

    run_id 가 있으면 실제 RAG(ask_with_document_filter), 없으면 Mock.
    반환 형식을 mock_chat 과 맞췄기 때문에 workspace.py 의 렌더링 코드는
    호출부 한 줄만 바꾸면 됩니다.
    """
    rag = _load_rag()

    if rag is None or not run_id:
        from utils.mock_data import mock_chat
        return mock_chat(question)

    response = rag.ask_with_document_filter(run_id, question, selected_doc_ids)

    if response.get("error"):
        return (f"답변 생성 중 오류가 발생했습니다: {response['error']}", [])

    reply = response.get("reply") or "문서에서 확인하지 못했습니다."
    return (reply, _citations_to_sources(response.get("citations")))


def get_document_ids(run_id: str | None) -> list[dict[str, Any]]:
    """run 의 문서 목록. 문서 필터 UI 용 (없으면 빈 리스트)."""
    rag = _load_rag()
    if rag is None or not run_id:
        return []
    try:
        return rag.get_documents(run_id)
    except Exception:
        return []
