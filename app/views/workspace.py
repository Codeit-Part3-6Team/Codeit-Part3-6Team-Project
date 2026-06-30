"""
워크스페이스 (다중 레이아웃)
============================
RFP 분석 후 사용하는 작업 화면.
왼쪽: 분석 결과 탭(핵심 요약 / 요구사항 / 사업 개요)
오른쪽: RAG 대화형 탐색(질문 → 출처와 함께 답변)

데모 모드: mock_data.py
실전 모드: rag_service.py → RAG 파이프라인
"""

import streamlit as st
from utils.components import topbar, P_ANALYZE
from utils.mock_data import mock_chat, stream_words

ss = st.session_state
topbar()
st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

is_real = ss.get("mode", "demo") == "real"

# ── 가드: 분석 결과가 없으면 분석 페이지로 유도 ─────────────────────────────
if is_real:
    if ss.run_id:
        from services.rag_service import get_run_info

        info = get_run_info(ss.run_id)
        if info.get("exists") and info.get("status") in ("success", "ready"):
            ss.analyzed = True
            ss.analysis = {
                "meta": {
                    "run_id": ss.run_id,
                    "문서 수": info.get("document_count", 0),
                },
                "summary": "",
                "requirements": [],
            }
        else:
            ss.analyzed = False

    if not ss.run_id or not ss.analyzed:
        st.markdown(
            '<div class="eyebrow">WORKSPACE</div>'
            '<h2 class="sec-title" style="margin-bottom:18px">분석된 문서가 없습니다</h2>',
            unsafe_allow_html=True,
        )
        st.info("먼저 RFP 문서를 업로드하고 RAG 분석을 완료해주세요.")
        if st.button("📤 분석하러 가기", type="primary", key="goto_analyze"):
            st.switch_page(P_ANALYZE)
        st.stop()
    data = ss.analysis or {"summary": "", "requirements": [], "meta": {"run_id": ss.run_id}}
else:
    if not ss.analyzed or not ss.analysis:
        st.markdown(
            '<div class="eyebrow">WORKSPACE</div>'
            '<h2 class="sec-title" style="margin-bottom:18px">분석된 문서가 없습니다</h2>',
            unsafe_allow_html=True,
        )
        st.info("먼저 RFP 문서를 업로드하고 분석을 완료해주세요.")
        if st.button("📤 분석하러 가기", type="primary", key="goto_analyze"):
            st.switch_page(P_ANALYZE)
        st.stop()
    data = ss.analysis

# ── 상단 문서 헤더 ───────────────────────────────────────────────────────────
h1, h2 = st.columns([3, 1], vertical_alignment="center")
with h1:
    display = f"Run: {ss.run_id[:16]}..." if is_real else ss.doc_name
    st.markdown(
        f'<div class="panel-title">&#x1F5C2;&#xFE0F; {display}'
        f'<span class="status-ok" style="margin-left:12px">● 분석 완료</span></div>',
        unsafe_allow_html=True,
    )
with h2:
    if st.button("다른 문서 분석", type="secondary", use_container_width=True, key="ws_change"):
        if is_real:
            from services.rag_service import clear_chatbot
            clear_chatbot(ss.run_id)
            ss.run_id = None
        ss.doc_name = None
        ss.analyzed = False
        ss.analysis = None
        ss.messages = []
        st.switch_page(P_ANALYZE)

st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

# ── 실전 모드: 문서 선택 체크박스 ──────────────────────────────────────────
selected_doc_ids: list[str] = []
if is_real:
    from services.rag_service import get_documents
    docs = get_documents(ss.run_id)
    if docs:
        with st.expander(f"분석된 문서 ({len(docs)}개) — 선택하여 범위 좁히기", expanded=False):
            for d in docs:
                label = d["title"] or d["document_id"][:40]
                if st.checkbox(f"{label} ({d['chunk_count']} chunks)", key=f"doc_{d['document_id']}"):
                    selected_doc_ids.append(d["document_id"])

# ── 다중 레이아웃: 좌(분석) / 우(채팅) ───────────────────────────────────────
left, right = st.columns([1.25, 1], gap="large")

# ----- 왼쪽: 분석 결과 탭 -----
with left:
    tab1, tab2, tab3 = st.tabs(["핵심 요약", "핵심 요구사항", "사업 개요"])

    with tab1:
        if is_real:
            st.markdown(
                '<div class="panel" style="margin-top:10px">'
                '<div style="color:var(--text-2);font-size:.95rem;line-height:1.75">'
                '하단 챗봇에서 "요약해줘" 라고 질문하거나, 분석 버튼을 사용하세요.'
                '</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="panel" style="margin-top:10px">'
                f'<div style="color:var(--text-2);font-size:.95rem;line-height:1.75">'
                f'{data["summary"]}</div></div>',
                unsafe_allow_html=True,
            )

    with tab2:
        if is_real:
            st.markdown(
                '<div class="panel" style="margin-top:10px">'
                '<div style="color:var(--text-2);font-size:.95rem;line-height:1.75">'
                '하단 "참가자격/제출서류 추출" 버튼을 눌러 요구사항을 분석하세요.'
                '</div></div>',
                unsafe_allow_html=True,
            )
        else:
            reqs = "".join(
                f'<div class="req-item"><span class="req-num">{i:02d}</span><span>{r}</span></div>'
                for i, r in enumerate(data["requirements"], 1)
            )
            st.markdown(
                f'<div class="panel" style="margin-top:10px">{reqs}</div>',
                unsafe_allow_html=True,
            )

    with tab3:
        if is_real:
            st.markdown(
                '<div class="panel" style="margin-top:10px">'
                '<div style="color:var(--text-2);font-size:.95rem;line-height:1.75">'
                'Run ID, 문서 수, 청크 수 등의 메타 정보입니다.'
                '</div></div>',
                unsafe_allow_html=True,
            )
            for k, v in data["meta"].items():
                st.markdown(f"- **{k}**: {v}")
        else:
            meta_cells = "".join(
                f'<div class="meta-cell"><div class="meta-k">{k}</div><div class="meta-v">{v}</div></div>'
                for k, v in data["meta"].items()
            )
            st.markdown(
                f'<div class="panel" style="margin-top:10px">'
                f'<div class="meta-grid">{meta_cells}</div></div>',
                unsafe_allow_html=True,
            )

# ----- 오른쪽: RAG 대화형 탐색 -----
with right:
    st.markdown(
        '<div class="panel-title" style="margin-bottom:6px">&#x1F4AC; 대화형 탐색</div>',
        unsafe_allow_html=True,
    )

    if is_real:
        st.caption("RAG 파이프라인 기반 실시간 문서 분석")
    else:
        st.caption("RAG 연결 전이라 예시 응답입니다. 출처(페이지)는 Mock 데이터입니다.")

    # ── 빠른 분석 버튼 (실전 모드 전용) ──
    if is_real and ss.run_id:
        btn_cols = st.columns(3)
        with btn_cols[0]:
            if st.button("&#x1F4CB; 요약", type="secondary", use_container_width=True, key="btn_summarize"):
                ss.pending_q = "이 RFP 문서의 핵심 내용을 요약해줘."
                ss.pending_tool = "extract_facts"
                st.rerun()
        with btn_cols[1]:
            if st.button("&#x1F4CB; 요구사항", type="secondary", use_container_width=True, key="btn_requirements"):
                ss.pending_q = "참가자격과 제출서류를 추출해서 보여줘."
                ss.pending_tool = "extract_requirements"
                st.rerun()
        with btn_cols[2]:
            if st.button("&#x1F4CA; 비교", type="secondary", use_container_width=True, key="btn_compare"):
                ss.pending_q = "분석된 문서들을 예산, 기간, 자격요건 기준으로 비교해줘."
                ss.pending_tool = "compare_rfps"
                st.rerun()

    # ── 추천 질문 칩 ──
    if not is_real:
        suggested = ["제출 마감일은?", "예산 규모는?", "보안 요구사항은?"]
    else:
        suggested = ["사업 예산과 기간은?", "참가 자격 요건은?", "주요 리스크는?"]

    chip_cols = st.columns(len(suggested))
    for col, q in zip(chip_cols, suggested):
        with col:
            if st.button(q, type="secondary", use_container_width=True, key=f"chip_{q}"):
                ss.pending_q = q
                st.rerun()

    # ── 대화 기록 렌더 ──
    for m in ss.messages:
        if m["role"] == "user":
            st.markdown(
                f'<div class="role u">You</div><div class="msg-user">{m["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            # 실전 모드: citation 표시
            if is_real and m.get("citations"):
                cite_lines = []
                for c in m["citations"][:6]:
                    chunk_id = c.get("chunk_id", "")[:16]
                    page = c.get("page", c.get("page_start", "?"))
                    section = c.get("section", "")
                    label = f"p.{page} ({section})" if section else f"p.{page}"
                    cite_lines.append(f'<span class="src-tag">&#x1F4C4; {label} · {chunk_id}</span>')
                tags_html = "".join(cite_lines)
            elif m.get("sources"):
                tags_html = "".join(
                    f'<span class="src-tag">&#x1F4D1; {p} · {s}</span>'
                    for p, s in m["sources"]
                )
            else:
                tags_html = ""

            st.markdown(
                f'<div class="role a">BidAI</div><div class="msg-ai">{m["content"]}'
                f'<div style="margin-top:4px">{tags_html}</div></div>',
                unsafe_allow_html=True,
            )

    # ── 입력 처리 ──
    typed = st.chat_input("문서에 대해 질문해보세요")
    question = ss.pending_q or typed
    pending_tool = ss.pending_tool
    ss.pending_q = None
    ss.pending_tool = None

    if question:
        ss.messages.append({"role": "user", "content": question})
        st.markdown(
            f'<div class="role u">You</div><div class="msg-user">{question}</div>',
            unsafe_allow_html=True,
        )

        if is_real and ss.run_id:
            # ── 실전 모드: rag_service.ask() ──
            st.markdown('<div class="role a">BidAI</div>', unsafe_allow_html=True)
            ph = st.empty()

            with st.spinner("문서에서 검색 중... (RAG)"):
                from services.rag_service import ask_with_document_filter, run_tool

                if pending_tool:
                    response = run_tool(
                        ss.run_id,
                        pending_tool,
                        question,
                        selected_doc_ids if selected_doc_ids else None,
                    )
                else:
                    response = ask_with_document_filter(
                        ss.run_id,
                        question,
                        selected_doc_ids if selected_doc_ids else None,
                    )

            reply = response.get("reply", "응답을 생성하지 못했습니다.")
            if response.get("error"):
                reply = f"오류: {response['error']}"

            citations = response.get("citations", [])
            cite_lines = []
            for c in citations[:6]:
                chunk_id = c.get("chunk_id", "")[:16]
                page = c.get("page", c.get("page_start", "?"))
                section = c.get("section", "")
                label = f"p.{page} ({section})" if section else f"p.{page}"
                cite_lines.append(f'<span class="src-tag">&#x1F4C4; {label} · {chunk_id}</span>')
            tags_html = "".join(cite_lines)

            ph.markdown(
                f'<div class="msg-ai">{reply}<div style="margin-top:4px">{tags_html}</div></div>',
                unsafe_allow_html=True,
            )
            ss.messages.append({
                "role": "assistant",
                "content": reply,
                "citations": citations,
            })

            # 답변을 summary/requirements에 반영
            if ss.analysis is None:
                ss.analysis = {"meta": {}, "summary": "", "requirements": []}
            if response.get("tool_used") == "extract_facts" or "요약" in question:
                ss.analysis["summary"] = reply
            elif response.get("tool_used") == "extract_requirements" or "요구사항" in question:
                ss.analysis["requirements"] = [reply]

            st.rerun()

        else:
            # ── 데모 모드: mock_chat() ──
            ans, srcs = mock_chat(question)
            st.markdown('<div class="role a">BidAI</div>', unsafe_allow_html=True)
            ph = st.empty()
            acc = ""
            with st.spinner("문서에서 검색 중..."):
                for acc in stream_words(ans):
                    ph.markdown(f'<div class="msg-ai">{acc}&#x258C;</div>', unsafe_allow_html=True)
            tags = "".join(f'<span class="src-tag">&#x1F4D1; {p} · {s}</span>' for p, s in srcs)
            ph.markdown(
                f'<div class="msg-ai">{acc}<div style="margin-top:4px">{tags}</div></div>',
                unsafe_allow_html=True,
            )
            ss.messages.append({
                "role": "assistant",
                "content": acc.strip(),
                "sources": srcs,
            })
            st.rerun()
