"""RAG 서비스 어댑터 연결 예시 화면."""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from services.rag_service import (
    ask_with_document_filter,
    create_and_ingest,
    extract_requirements,
    get_documents,
    summarize,
)
from utils.components import footer, topbar


def _save_uploads(uploaded_files: list, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for uploaded in uploaded_files:
        safe_name = Path(uploaded.name).name
        (target_dir / safe_name).write_bytes(uploaded.getbuffer())


def _citation_label(citation: dict) -> str:
    page = citation.get("page") or citation.get("page_start")
    source = Path(str(citation.get("source_path") or "")).name
    if page not in (None, "", "?"):
        return f"{source or '원문'} p.{page}"
    return source or "원문 근거"


def _render_response(response: dict) -> None:
    if response.get("error"):
        st.error(response["error"])
        return

    reply = response.get("reply") or "표시할 응답이 없습니다."
    st.markdown(reply)

    citations = response.get("citations") or []
    if citations:
        labels = []
        seen = set()
        for citation in citations:
            label = _citation_label(citation)
            if label in seen:
                continue
            seen.add(label)
            labels.append(label)
        if labels:
            st.caption("근거: " + " · ".join(labels))


topbar()
st.title("RAG 연결 예시")

ss = st.session_state
ss.setdefault("contract_run_id", None)
ss.setdefault("contract_documents", [])
ss.setdefault("contract_summary", None)
ss.setdefault("contract_requirements", None)
ss.setdefault("contract_messages", [])

uploaded_files = st.file_uploader(
    "RFP 문서 업로드",
    type=["pdf", "docx", "hwp", "hwpx", "txt", "csv"],
    accept_multiple_files=True,
)

if st.button("분석 실행", type="primary", disabled=not uploaded_files):
    with st.spinner("문서를 읽고 검색 인덱스를 만드는 중입니다."):
        with tempfile.TemporaryDirectory() as tmp:
            upload_dir = Path(tmp) / "uploads"
            _save_uploads(uploaded_files, upload_dir)
            ingest = create_and_ingest(str(upload_dir))

    if ingest.get("status") != "ready":
        st.error(ingest.get("error") or "문서 분석에 실패했습니다.")
    else:
        run_id = ingest["run_id"]
        ss.contract_run_id = run_id
        ss.contract_documents = get_documents(run_id)
        ss.contract_summary = summarize(run_id)
        ss.contract_requirements = extract_requirements(run_id)
        ss.contract_messages = []
        st.success("분석이 완료되었습니다.")

if ss.contract_run_id:
    st.caption(f"Run: {ss.contract_run_id}")

    doc_options = {
        doc["document_id"]: doc.get("title") or doc["document_id"]
        for doc in ss.contract_documents
    }
    selected_doc_ids = st.multiselect(
        "문서 범위",
        options=list(doc_options.keys()),
        format_func=lambda doc_id: doc_options.get(doc_id, doc_id),
    )
    active_doc_ids = selected_doc_ids or None

    left, right = st.columns(2)
    with left:
        st.subheader("핵심 요약")
        _render_response(ss.contract_summary or {})
    with right:
        st.subheader("참가 자격/제출 서류")
        _render_response(ss.contract_requirements or {})

    st.subheader("대화형 질의")
    for message in ss.contract_messages:
        with st.chat_message(message["role"]):
            _render_response(message["content"]) if message["role"] == "assistant" else st.markdown(message["content"])

    question = st.chat_input("질문을 입력하세요")
    if question:
        ss.contract_messages.append({"role": "user", "content": question})
        with st.spinner("답변을 생성하는 중입니다."):
            response = ask_with_document_filter(
                ss.contract_run_id,
                question,
                selected_doc_ids=active_doc_ids,
            )
        ss.contract_messages.append({"role": "assistant", "content": response})
        st.rerun()
else:
    st.info("문서를 업로드하고 분석 실행을 누르면 요약과 질의를 바로 확인할 수 있습니다.")

footer()
