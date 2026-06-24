"""
워크스페이스 (다중 레이아웃)
============================
RFP 분석 후 사용하는 작업 화면.
왼쪽: 분석 결과 탭(핵심 요약 / 요구사항 / 사업 개요)
오른쪽: RAG 대화형 탐색(질문 → 출처와 함께 답변)

세션 상태(ss.analysis, ss.messages)는 페이지가 바뀌어도 유지되므로
'분석하기'에서 만든 결과를 여기서 그대로 사용합니다.
"""

import streamlit as st
from utils.components import topbar, P_ANALYZE
from utils.mock_data import mock_chat, stream_words

ss = st.session_state
topbar()
st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

# ── 가드: 분석 결과가 없으면 분석 페이지로 유도 ─────────────────────────────
if not ss.analyzed or not ss.analysis:
    st.markdown('<div class="eyebrow">WORKSPACE</div>'
                '<h2 class="sec-title" style="margin-bottom:18px">분석된 문서가 없습니다</h2>',
                unsafe_allow_html=True)
    st.info("먼저 RFP 문서를 업로드하고 분석을 완료해주세요.")
    if st.button("📤 분석하러 가기", type="primary", key="goto_analyze"):
        st.switch_page(P_ANALYZE)
    st.stop()

data = ss.analysis

# ── 상단 문서 헤더 ───────────────────────────────────────────────────────────
h1, h2 = st.columns([3, 1], vertical_alignment="center")
with h1:
    st.markdown(f'<div class="panel-title">🗂️ {ss.doc_name}'
                f'<span class="status-ok" style="margin-left:12px">● 분석 완료</span></div>',
                unsafe_allow_html=True)
with h2:
    if st.button("다른 문서 분석", type="secondary", use_container_width=True, key="ws_change"):
        ss.doc_name = None
        ss.analyzed = False
        ss.analysis = None
        ss.messages = []
        st.switch_page(P_ANALYZE)

st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

# ── 다중 레이아웃: 좌(분석) / 우(채팅) ───────────────────────────────────────
left, right = st.columns([1.25, 1], gap="large")

# ----- 왼쪽: 분석 결과 탭 -----
with left:
    tab1, tab2, tab3 = st.tabs(["핵심 요약", "핵심 요구사항", "사업 개요"])

    with tab1:
        st.markdown(f'<div class="panel" style="margin-top:10px">'
                    f'<div style="color:var(--text-2);font-size:.95rem;line-height:1.75">'
                    f'{data["summary"]}</div></div>', unsafe_allow_html=True)

    with tab2:
        reqs = "".join(
            f'<div class="req-item"><span class="req-num">{i:02d}</span><span>{r}</span></div>'
            for i, r in enumerate(data["requirements"], 1)
        )
        st.markdown(f'<div class="panel" style="margin-top:10px">{reqs}</div>',
                    unsafe_allow_html=True)

    with tab3:
        meta_cells = "".join(
            f'<div class="meta-cell"><div class="meta-k">{k}</div><div class="meta-v">{v}</div></div>'
            for k, v in data["meta"].items()
        )
        st.markdown(f'<div class="panel" style="margin-top:10px">'
                    f'<div class="meta-grid">{meta_cells}</div></div>', unsafe_allow_html=True)

# ----- 오른쪽: RAG 대화형 탐색 -----
with right:
    st.markdown('<div class="panel-title" style="margin-bottom:6px">💬 대화형 탐색</div>',
                unsafe_allow_html=True)
    st.caption("RAG 연결 전이라 예시 응답입니다. 출처(페이지)는 Mock 데이터입니다.")

    # 추천 질문 칩
    suggested = ["제출 마감일은?", "예산 규모는?", "보안 요구사항은?"]
    chip_cols = st.columns(3)
    for col, q in zip(chip_cols, suggested):
        with col:
            if st.button(q, type="secondary", use_container_width=True, key=f"chip_{q}"):
                ss.pending_q = q
                st.rerun()

    # 대화 기록 렌더
    for m in ss.messages:
        if m["role"] == "user":
            st.markdown(f'<div class="role u">You</div><div class="msg-user">{m["content"]}</div>',
                        unsafe_allow_html=True)
        else:
            tags = "".join(f'<span class="src-tag">📑 {p} · {s}</span>' for p, s in m.get("sources", []))
            st.markdown(f'<div class="role a">BidAI</div><div class="msg-ai">{m["content"]}'
                        f'<div style="margin-top:4px">{tags}</div></div>', unsafe_allow_html=True)

    # 입력 처리 (추천칩 또는 직접 입력)
    typed = st.chat_input("문서에 대해 질문해보세요")
    question = ss.pending_q or typed
    ss.pending_q = None

    if question:
        ss.messages.append({"role": "user", "content": question})
        st.markdown(f'<div class="role u">You</div><div class="msg-user">{question}</div>',
                    unsafe_allow_html=True)

        ans, srcs = mock_chat(question)
        st.markdown('<div class="role a">BidAI</div>', unsafe_allow_html=True)
        ph = st.empty()
        acc = ""
        with st.spinner("문서에서 검색 중..."):
            for acc in stream_words(ans):
                ph.markdown(f'<div class="msg-ai">{acc}▌</div>', unsafe_allow_html=True)
        tags = "".join(f'<span class="src-tag">📑 {p} · {s}</span>' for p, s in srcs)
        ph.markdown(f'<div class="msg-ai">{acc}<div style="margin-top:4px">{tags}</div></div>',
                    unsafe_allow_html=True)
        ss.messages.append({"role": "assistant", "content": acc.strip(), "sources": srcs})
        st.rerun()
