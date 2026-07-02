"""
분석하기 (업로드 + 분석 실행)
=============================
문서를 업로드하거나 샘플을 선택하고, 'AI 분석 시작'을 누르면
RAG 백엔드로 분석을 돌린 뒤 워크스페이스로 이동합니다.

백엔드 연결은 services/frontend_adapter.py 를 통합니다:
  - VM(src/ 존재): 실제 RAG 파이프라인 (ingest → 요약/요구사항 추출)
  - 로컬(src/ 없음) 또는 샘플 체험: Mock 데이터로 자동 폴백
"""

import streamlit as st
from utils.components import topbar, footer, P_WORKSPACE
from services.frontend_adapter import analyze_document, backend_mode

ss = st.session_state
topbar()

st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
st.markdown('<div class="eyebrow">STEP 1</div>'
            '<h2 class="sec-title" style="margin-bottom:22px">RFP 문서 분석</h2>',
            unsafe_allow_html=True)

# 현재 백엔드 모드 표시 (개발 중 확인용 · RAG 연결되면 'RAG 파이프라인 연결됨')
_mode = backend_mode()
st.caption(("🟢 " if _mode["mode"] == "rag" else "🟡 ") + _mode["detail"])

# ── 문서가 없으면 업로드 받기 ────────────────────────────────────────────────
if not ss.doc_name:
    st.info("분석할 RFP 문서를 업로드하거나 샘플 문서로 체험해보세요.")
    up = st.file_uploader("RFP 파일 업로드",
                          type=["pdf", "docx", "hwp", "hwpx", "txt", "csv"],
                          key="analyze_upload")
    if up is not None:
        ss.doc_name = up.name
        ss.doc_bytes = up.getvalue()   # rerun 이후에도 파일 내용 유지 (분석 시 사용)
        ss.analyzed = False
        st.rerun()
    if st.button("샘플 문서로 체험", type="secondary", key="analyze_sample"):
        ss.doc_name = "샘플_전자조달시스템_RFP.pdf"
        ss.doc_bytes = None            # 실제 파일이 없으므로 Mock 분석 경로로 감
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
            # 인덱싱(파싱→청킹→임베딩) + 요약/요구사항 추출까지 한 번에 수행.
            # 실제 RAG 는 문서 크기에 따라 수십 초가 걸릴 수 있음.
            with st.spinner("문서를 분석하고 있습니다... (인덱싱 → 요약 → 요구사항 추출)"):
                result = analyze_document(ss.doc_name, ss.doc_bytes)

            if result["error"] and not result["summary"]:
                # 완전 실패: 화면에 남아 에러 표시 (재시도 가능)
                st.error(f"분석에 실패했습니다: {result['error']}")
            else:
                if result["error"]:
                    # 부분 실패: 진행은 하되 경고 표시
                    st.warning(f"일부 분석이 실패했습니다: {result['error']}")
                ss.analysis = result           # meta/summary/requirements 포함
                ss.run_id = result["run_id"]   # 워크스페이스 채팅이 사용할 인덱스 ID
                ss.analyzed = True
                st.rerun()
    else:
        if st.button("🗂️ 워크스페이스 열기", type="primary", use_container_width=True, key="open_ws"):
            st.switch_page(P_WORKSPACE)
with col2:
    if st.button("다른 문서 선택", type="secondary", use_container_width=True, key="change_doc"):
        ss.doc_name = None
        ss.doc_bytes = None
        ss.analyzed = False
        ss.analysis = None
        ss.run_id = None
        ss.messages = []
        st.rerun()

if ss.analyzed:
    st.success("분석이 완료되었습니다. 워크스페이스에서 요약 확인과 질문이 가능합니다.")

footer()
