"""내부 RFP 문서 선택형 Streamlit UI 초안.

기존에 ingest된 내부 문서 인덱스를 자동으로 재사용하는 화면 예시입니다.
최종 UI에 직접 연결하지 않고, 프론트 구현 참고용으로 둡니다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = PROJECT_ROOT / "app"
for path in (PROJECT_ROOT, APP_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from services.rag_service import (
    ask_with_document_filter,
    compare,
    extract_requirements,
    get_documents,
    list_runs,
    summarize,
)


def _latest_internal_run() -> dict | None:
    """사용자에게 run을 노출하지 않고 최신 내부 문서 인덱스를 선택합니다."""
    for run in list_runs():
        if int(run.get("documents") or 0) > 0:
            return run
    return None


def _citation_label(citation: dict) -> str:
    source = Path(str(citation.get("source_path") or "")).name or "원문"
    page = citation.get("page") or citation.get("page_start")
    if page not in (None, "", "?"):
        return f"{source} p.{page}"
    return source


def _render_response(response: dict) -> None:
    if response.get("error"):
        st.error(response["error"])
        return

    structured = response.get("structured_output")
    if structured:
        with st.expander("구조화 결과", expanded=True):
            st.json(structured, expanded=False)

    st.markdown(response.get("reply") or "표시할 응답이 없습니다.")

    citations = response.get("citations") or []
    if citations:
        labels: list[str] = []
        seen = set()
        for citation in citations:
            label = _citation_label(citation)
            if label in seen:
                continue
            seen.add(label)
            labels.append(label)
        st.caption("근거: " + " · ".join(labels))


st.set_page_config(
    page_title="내부 RFP 문서 분석 초안",
    page_icon="🗂️",
    layout="wide",
)

st.title("내부 RFP 문서 분석")

internal_run = _latest_internal_run()
if internal_run is None:
    st.info("분석할 내부 문서 인덱스가 없습니다. 먼저 내부 RFP 문서 ingest를 실행해 주세요.")
    st.stop()

run_id = internal_run["run_id"]
documents = get_documents(run_id)
if not documents:
    st.warning("내부 문서 목록을 불러오지 못했습니다.")
    st.stop()

doc_options = {doc["document_id"]: doc for doc in documents}
st.caption(f"내부 문서 {len(documents)}개를 대상으로 분석합니다.")

selected_doc_ids = st.multiselect(
    "특정 문서만 보기",
    options=list(doc_options.keys()),
    format_func=lambda doc_id: f"{doc_options[doc_id]['title']} ({doc_options[doc_id]['chunk_count']} chunks)",
)

active_doc_ids = selected_doc_ids or None
if active_doc_ids:
    st.caption(f"선택 문서 {len(active_doc_ids)}개만 검색합니다.")
else:
    st.caption("선택한 문서가 없으면 전체 내부 문서를 검색합니다.")

tab_summary, tab_requirements, tab_compare, tab_chat = st.tabs(
    ["핵심 요약", "참가 자격/서류", "문서 비교", "질문"]
)

with tab_summary:
    if st.button("요약 실행", type="primary"):
        with st.spinner("요약 중입니다."):
            _render_response(summarize(run_id, active_doc_ids))

with tab_requirements:
    if st.button("참가 자격/서류 추출"):
        with st.spinner("요건을 추출하는 중입니다."):
            _render_response(extract_requirements(run_id, active_doc_ids))

with tab_compare:
    if len(selected_doc_ids) < 2:
        st.info("비교는 문서 2개 이상 선택했을 때 사용하는 흐름입니다.")
    elif st.button("선택 문서 비교"):
        with st.spinner("비교 중입니다."):
            _render_response(compare(run_id, selected_doc_ids))

with tab_chat:
    question = st.text_input("질문", placeholder="사업 예산과 기간은?")
    if st.button("질문하기", disabled=not question):
        with st.spinner("답변 생성 중입니다."):
            _render_response(ask_with_document_filter(run_id, question, active_doc_ids))
