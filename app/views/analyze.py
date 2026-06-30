"""
분석하기 (업로드 + 분석 실행)
=============================
데모 모드: mock_data.py로 가상 분석
실전 모드: rag_service.py로 실제 RAG 파이프라인 실행
"""

import tempfile
from pathlib import Path

import streamlit as st
from utils.components import topbar, footer, P_WORKSPACE
from utils.mock_data import mock_analyze

ss = st.session_state
topbar()

st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="eyebrow">STEP 1</div>'
    '<h2 class="sec-title" style="margin-bottom:22px">RFP 문서 분석</h2>',
    unsafe_allow_html=True,
)

is_real = ss.get("mode", "demo") == "real"

# ── 데모 모드: 기존 동작 유지 ───────────────────────────────────────────────
if not is_real:
    if not ss.doc_name:
        st.info("분석할 RFP 문서를 업로드하거나 샘플 문서로 체험해보세요.")
        up = st.file_uploader(
            "RFP 파일 업로드", type=["pdf", "docx", "hwp", "txt"], key="analyze_upload"
        )
        if up is not None:
            ss.doc_name = up.name
            ss.analyzed = False
            st.rerun()
        if st.button("샘플 문서로 체험", type="secondary", key="analyze_sample"):
            ss.doc_name = "샘플_전자조달시스템_RFP.pdf"
            ss.analyzed = False
            st.rerun()
        footer()
        st.stop()

    status = (
        '<span class="status-ok">● 분석 완료</span>'
        if ss.analyzed
        else '<span class="status-wait">● 분석 대기</span>'
    )
    st.markdown(
        f'<div class="panel"><div style="display:flex;justify-content:space-between;'
        f'align-items:center"><div class="panel-title">&#x1F4C4; {ss.doc_name}</div>{status}</div></div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        if not ss.analyzed:
            if st.button("⚡ AI 분석 시작", type="primary", use_container_width=True, key="run_analyze"):
                with st.spinner("문서를 분석하고 있습니다... (Mock)"):
                    ss.analysis = mock_analyze(ss.doc_name)
                    ss.analyzed = True
                st.rerun()
        else:
            if st.button("🗂️ 워크스페이스 열기", type="primary", use_container_width=True, key="open_ws"):
                st.switch_page(P_WORKSPACE)
    with col2:
        if st.button("다른 문서 선택", type="secondary", use_container_width=True, key="change_doc"):
            ss.doc_name = None
            ss.analyzed = False
            ss.analysis = None
            ss.messages = []
            st.rerun()

    if ss.analyzed:
        st.success("분석이 완료되었습니다. 워크스페이스에서 요약 확인과 질문이 가능합니다.")
    footer()

else:
    # ── 실전 모드: rag_service.py 경유 ───────────────────────────────────────
    run_id = ss.get("run_id")

    if not run_id:
        st.info("RFP 문서를 업로드하고 RAG 분석을 시작하세요. PDF, DOCX, HWP, TXT를 지원합니다.")
        uploaded_files = st.file_uploader(
            "RFP 파일 업로드 (복수 선택 가능)",
            type=["pdf", "docx", "hwp", "hwpx", "txt", "csv"],
            accept_multiple_files=True,
            key="real_upload",
        )

        if uploaded_files:
            st.markdown(
                f'<div class="panel"><div class="panel-title">&#x1F4E4; '
                f'{len(uploaded_files)}개 파일 선택됨</div>'
                f'{"".join(f"<div>· {f.name}</div>" for f in uploaded_files)}</div>',
                unsafe_allow_html=True,
            )

            if st.button("⚡ RAG 분석 시작", type="primary", use_container_width=True, key="run_real_analyze"):
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp = Path(tmpdir)
                    for uf in uploaded_files:
                        dest = tmp / uf.name
                        dest.write_bytes(uf.getbuffer())

                    with st.spinner(f"문서 {len(uploaded_files)}개를 분석 중입니다... (RAG 파이프라인 실행)"):
                        from app.services.rag_service import create_and_ingest

                        result = create_and_ingest(str(tmp))

                if result["status"] == "ready":
                    ss.run_id = result["run_id"]
                    ss.analyzed = True
                    ss.doc_name = result["run_id"]
                    ss.analysis = {
                        "meta": {"run_id": result["run_id"], "문서 수": result["documents"], "청크 수": result["chunks"]},
                        "summary": "",
                        "requirements": [],
                    }
                    st.success(f"분석 완료! 문서 {result['documents']}개, 청크 {result['chunks']}개 생성됨.")
                    st.rerun()
                else:
                    st.error(f"분석 실패: {result.get('error', '알 수 없는 오류')}")

        footer()
        st.stop()

    else:
        # run_id 있음 → ready 상태 표시
        from app.services.rag_service import get_run_info, get_documents

        info = get_run_info(run_id)
        docs = get_documents(run_id)

        display_name = f"Run: {run_id[:16]}..."
        status_html = (
            '<span class="status-ok">● 분석 완료</span>'
            if info["status"] in ("success", "ready")
            else f'<span class="status-wait">● {info["status"]}</span>'
        )
        st.markdown(
            f'<div class="panel"><div style="display:flex;justify-content:space-between;'
            f'align-items:center"><div class="panel-title">&#x1F4C4; {display_name}</div>{status_html}</div></div>',
            unsafe_allow_html=True,
        )

        if docs:
            st.markdown(f"**분석된 문서 ({len(docs)}개)**")
            for d in docs:
                st.markdown(
                    f"- {d['title'] or d['document_id'][:30]} "
                    f"({d['chunk_count']} chunks)",
                )

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🗂️ 워크스페이스 열기", type="primary", use_container_width=True):
                st.switch_page(P_WORKSPACE)
        with col2:
            if st.button("다른 문서 분석", type="secondary", use_container_width=True):
                from app.services.rag_service import clear_chatbot
                clear_chatbot(run_id)
                ss.run_id = None
                ss.analyzed = False
                ss.analysis = None
                ss.messages = []
                ss.doc_name = None
                st.rerun()

        st.success("워크스페이스에서 요약, 질문, 요구사항 추출이 가능합니다.")
        footer()
