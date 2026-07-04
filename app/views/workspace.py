"""
워크스페이스 (다중 레이아웃)
============================
내부 문서를 선택·분석한 뒤 사용하는 작업 화면.
왼쪽: 분석 결과 탭(핵심 요약 / 핵심 요구사항 / 사업 개요)
오른쪽: RAG 대화형 탐색(질문 → 출처와 함께 답변)

세션 상태(ss.analysis, ss.messages, ss.selected_docs)는 페이지가 바뀌어도
유지되므로 '문서 분석'에서 만든 결과를 여기서 그대로 사용합니다.
"""

import streamlit as st

from utils.components import topbar, esc, P_DOCS
from utils.mock_data import stream_words
from services.frontend_adapter import chat_ask

ss = st.session_state
topbar()
st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

# ── 가드: 분석 결과가 없으면 문서 선택 페이지로 유도 ─────────────────────────
if not ss.analyzed or not ss.analysis:
    st.markdown('<div class="eyebrow">WORKSPACE</div>'
                '<h2 class="sec-title" style="margin-bottom:18px">분석된 문서가 없습니다</h2>',
                unsafe_allow_html=True)
    st.info("먼저 내부 문서 목록에서 분석할 문서를 선택해주세요.")
    if st.button("📚 문서 선택하러 가기", type="primary", key="goto_docs"):
        st.switch_page(P_DOCS)
    st.stop()

data = ss.analysis
selected_docs = ss.selected_docs or []
selected_ids = ss.selected_doc_ids or []
titles = [str(d.get("title") or d.get("document_id")) for d in selected_docs]

# 헤더 표기: 1건이면 문서명, 여러 건이면 "문서명 외 N건"
if len(titles) == 1:
    head_label = titles[0]
elif titles:
    head_label = f"{titles[0]} 외 {len(titles) - 1}건"
else:
    head_label = "선택 문서"

# ── 상단 문서 헤더 ───────────────────────────────────────────────────────────
h1, h2 = st.columns([3, 1], vertical_alignment="center")
with h1:
    # F2: 문서명은 문서에서 온 값이므로 esc() 처리
    st.markdown(f'<div class="panel-title">🗂️ {esc(head_label)}'
                f'<span class="status-ok" style="margin-left:12px">● 분석 완료</span></div>',
                unsafe_allow_html=True)
with h2:
    if st.button("다른 문서 분석", type="secondary", use_container_width=True, key="ws_change"):
        # F5: 이전 분석의 흔적(선택 문서·결과·대화·추천질문)을 전부 초기화.
        #     run_id 는 '내부 corpus 인덱스'라 문서와 무관하게 유지합니다.
        ss.selected_doc_ids = []
        ss.selected_docs = []
        ss.analyzed = False
        ss.analysis = None
        ss.messages = []
        ss.pending_q = None
        st.switch_page(P_DOCS)

st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

# ── 다중 레이아웃: 좌(분석) / 우(채팅) ───────────────────────────────────────
left, right = st.columns([1.25, 1], gap="large")

# ----- 왼쪽: 분석 결과 탭 -----
with left:
    tab1, tab2, tab3 = st.tabs(["핵심 요약", "핵심 요구사항", "사업 개요"])

    with tab1:
        # summary_ok=False 면 백엔드가 빈 응답("(응답 없음)" 등)을 준 경우 →
        # 원문을 그대로 보여주지 않고 친절한 안내 + 채팅 유도.
        if data.get("summary_ok", True) and str(data.get("summary") or "").strip():
            # F2: 요약은 RAG/문서에서 온 값 → esc 처리.
            #     줄바꿈은 <br> 로 살려 가독성 유지 (esc 후 변환이라 안전).
            summary_html = esc(data["summary"]).replace("\n", "<br>")
            st.markdown(f'<div class="panel" style="margin-top:10px">'
                        f'<div style="color:var(--text-2);font-size:.95rem;line-height:1.75">'
                        f'{summary_html}</div></div>', unsafe_allow_html=True)
            _summary_srcs = (data.get("sources") or {}).get("summary") or []
            if _summary_srcs:
                st.caption("근거: " + " · ".join(f"{p} {s}" for p, s in _summary_srcs))
        else:
            st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
            st.info("이 문서에서는 자동 요약을 생성하지 못했어요. "
                    "오른쪽 **대화형 탐색**에서 예산·자격·일정 등을 직접 질문하면 "
                    "문서 근거와 함께 답을 받을 수 있습니다.\n\n"
                    "문서가 방금 인덱싱되었거나 본문 추출이 부분적일 때 나타날 수 있습니다.")

    with tab2:
        reqs = "".join(
            f'<div class="req-item"><span class="req-num">{i:02d}</span>'
            f'<span>{esc(r)}</span></div>'
            for i, r in enumerate(data["requirements"], 1)
        )
        st.markdown(f'<div class="panel" style="margin-top:10px">{reqs}</div>',
                    unsafe_allow_html=True)
        _req_srcs = (data.get("sources") or {}).get("requirements") or []
        if _req_srcs:
            st.caption("근거: " + " · ".join(f"{p} {s}" for p, s in _req_srcs))

    with tab3:
        meta_cells = "".join(
            f'<div class="meta-cell"><div class="meta-k">{esc(k)}</div>'
            f'<div class="meta-v">{esc(v)}</div></div>'
            for k, v in data["meta"].items()
        )
        st.markdown(f'<div class="panel" style="margin-top:10px">'
                    f'<div class="meta-grid">{meta_cells}</div></div>',
                    unsafe_allow_html=True)

# ----- 오른쪽: RAG 대화형 탐색 -----
with right:
    st.markdown('<div class="panel-title" style="margin-bottom:6px">💬 대화형 탐색</div>',
                unsafe_allow_html=True)
    # 백엔드 모드에 맞는 안내 문구
    if data.get("mode") == "rag" and ss.run_id:
        scope = f"선택한 {len(selected_ids)}개 문서" if len(selected_ids) > 1 else "선택한 문서"
        st.caption(f"{scope} 범위에서 검색하는 RAG 응답입니다. 출처는 문서 내 실제 근거 위치입니다.")
    else:
        st.caption("RAG 미연결(Mock) 모드입니다. 예시 응답과 예시 출처가 표시됩니다.")

    # 추천 질문 칩
    suggested = ["사업 예산은?", "참가 자격은?", "제출 서류는?"]
    chip_cols = st.columns(3)
    for col, q in zip(chip_cols, suggested):
        with col:
            if st.button(q, type="secondary", use_container_width=True, key=f"chip_{q}"):
                ss.pending_q = q
                st.rerun()

    # 대화 기록 렌더 (F2: 사용자 입력·모델 답변·출처 모두 esc 처리)
    for m in ss.messages:
        if m["role"] == "user":
            st.markdown(f'<div class="role u">You</div>'
                        f'<div class="msg-user">{esc(m["content"])}</div>',
                        unsafe_allow_html=True)
        else:
            tags = "".join(
                f'<span class="src-tag">📑 {esc(p)} · {esc(s)}</span>'
                for p, s in m.get("sources", [])
            )
            body = esc(m["content"]).replace("\n", "<br>")
            st.markdown(f'<div class="role a">IT&#39;S MINE</div>'
                        f'<div class="msg-ai">{body}'
                        f'<div style="margin-top:4px">{tags}</div></div>',
                        unsafe_allow_html=True)

    # 입력 처리 (추천칩 또는 직접 입력)
    typed = st.chat_input("선택한 문서에 대해 질문해보세요")
    question = ss.pending_q or typed
    ss.pending_q = None

    if question:
        ss.messages.append({"role": "user", "content": question})
        st.markdown(f'<div class="role u">You</div>'
                    f'<div class="msg-user">{esc(question)}</div>',
                    unsafe_allow_html=True)

        ans, srcs = chat_ask(question, ss.run_id, selected_ids or None, titles)
        st.markdown('<div class="role a">IT&#39;S MINE</div>', unsafe_allow_html=True)
        ph = st.empty()
        acc = ""
        with st.spinner("문서에서 검색 중..."):
            for acc in stream_words(ans):
                ph.markdown(f'<div class="msg-ai">{esc(acc)}▌</div>',
                            unsafe_allow_html=True)
        tags = "".join(f'<span class="src-tag">📑 {esc(p)} · {esc(s)}</span>'
                       for p, s in srcs)
        body = esc(acc).replace("\n", "<br>")
        ph.markdown(f'<div class="msg-ai">{body}'
                    f'<div style="margin-top:4px">{tags}</div></div>',
                    unsafe_allow_html=True)
        ss.messages.append({"role": "assistant", "content": acc.strip(), "sources": srcs})
        st.rerun()
