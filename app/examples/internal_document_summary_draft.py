"""내부 RFP 문서 선택형 Streamlit UI 초안.

기존에 ingest된 run을 재사용하는 화면 예시입니다.
최종 UI에 직접 연결하지 않고, 프론트 구현 참고용으로 둡니다.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.services.rag_service import (
    ask_with_document_filter,
    compare,
    extract_requirements,
    get_documents,
    list_runs,
    summarize,
)


def _run_label(run: dict) -> str:
    created = run.get("created_at") or "unknown time"
    status = run.get("status") or "unknown"
    docs = run.get("documents", 0)
    return f"{run['run_id']} · {status} · {docs} docs · {created}"


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

st.title("내부 RFP 문서 분석 초안")

runs = list_runs()
if not runs:
    st.info("아직 재사용할 RAG run이 없습니다. 먼저 ingest를 실행해 주세요.")
    st.stop()

selected_run = st.selectbox(
    "분석할 run",
    options=runs,
    format_func=_run_label,
)
run_id = selected_run["run_id"]

documents = get_documents(run_id)
if not documents:
    st.warning("선택한 run에 문서 목록이 없습니다.")
    st.stop()

doc_options = {doc["document_id"]: doc for doc in documents}
selected_doc_ids = st.multiselect(
    "분석할 내부 문서",
    options=list(doc_options.keys()),
    format_func=lambda doc_id: f"{doc_options[doc_id]['title']} ({doc_options[doc_id]['chunk_count']} chunks)",
)

active_doc_ids = selected_doc_ids or None

st.caption(
    "문서를 선택하지 않으면 run 전체 문서를 대상으로 분석합니다. "
    "문서를 선택하면 선택한 문서의 chunk만 검색합니다."
)

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
