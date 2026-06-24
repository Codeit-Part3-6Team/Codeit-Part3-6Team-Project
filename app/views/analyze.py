"""
분석하기 (업로드 + 분석 실행)
=============================
문서를 업로드하거나 샘플을 선택하고, 'AI 분석 시작'을 누르면
Mock 분석을 돌린 뒤 워크스페이스로 이동합니다.
"""

import streamlit as st
from utils.components import topbar, footer, P_WORKSPACE
from utils.mock_data import mock_analyze

ss = st.session_state
topbar()

st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
st.markdown('<div class="eyebrow">STEP 1</div>'
            '<h2 class="sec-title" style="margin-bottom:22px">RFP 문서 분석</h2>',
            unsafe_allow_html=True)

# ── 문서가 없으면 업로드 받기 ────────────────────────────────────────────────
if not ss.doc_name:
    st.info("분석할 RFP 문서를 업로드하거나 샘플 문서로 체험해보세요.")
    up = st.file_uploader("RFP 파일 업로드", type=["pdf", "docx", "hwp", "txt"], key="analyze_upload")
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

# ── 문서 정보 + 상태 ─────────────────────────────────────────────────────────
status = ('<span class="status-ok">● 분석 완료</span>' if ss.analyzed
          else '<span class="status-wait">● 분석 대기</span>')
st.markdown(f'<div class="panel"><div style="display:flex;justify-content:space-between;'
            f'align-items:center"><div class="panel-title">📄 {ss.doc_name}</div>{status}</div></div>',
            unsafe_allow_html=True)

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
