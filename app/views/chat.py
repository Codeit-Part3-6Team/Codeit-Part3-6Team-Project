"""
대화형 탐색
===========
선택한 문서 범위에서 RAG 질의를 수행하는 전용 화면입니다.

RAG 호출은 백그라운드 job으로 분리하고, job_running 중에는
최소 UI만 렌더링하며 2초 간격으로 polling합니다.
"""

from __future__ import annotations

import time

import streamlit as st

from services.chat_jobs import clear_chat_job, get_chat_job, start_chat_job
from utils.components import P_DOCS, P_WORKSPACE, esc, topbar

CHAT_CSS = """
<style>
.block-container{ max-width:960px !important; padding-left:2rem !important; padding-right:2rem !important; }
[data-testid="stChatInput"]{ max-width:800px !important; margin:0 auto !important; }
[data-testid="stChatMessage"] table{ width:100%; border-collapse:collapse; font-size:.92rem;
  margin:8px 0; background:var(--panel-2); border-radius:10px; overflow:hidden; }
[data-testid="stChatMessage"] td, [data-testid="stChatMessage"] th{
  padding:10px 14px; border-bottom:1px solid var(--border-soft); vertical-align:top; line-height:1.55; }
[data-testid="stChatMessage"] th{ color:var(--text-3); font-weight:600; font-size:.8rem;
  text-align:left; white-space:nowrap; }
[data-testid="stChatMessage"] td{ color:var(--text); }
[data-testid="stChatMessage"] td:first-child{ color:var(--blue-bright); font-weight:600;
  white-space:nowrap; min-width:100px; }
</style>
"""
st.markdown(CHAT_CSS, unsafe_allow_html=True)


ss = st.session_state
topbar()
st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)


def _render_sources(sources: list[tuple[str, str]] | None) -> None:
    if sources:
        with st.expander("📄 출처 보기"):
            for p, s in sources:
                st.caption(f"• {p} {s}")


def _selected_titles() -> list[str]:
    return [str(d.get("title") or d.get("document_id")) for d in (ss.selected_docs or [])]


def _head_label(titles: list[str]) -> str:
    if len(titles) == 1:
        return titles[0]
    if titles:
        return f"{titles[0]} 외 {len(titles) - 1}건"
    return "선택 문서"


def _start_question(question: str, selected_ids: list[str], titles: list[str]) -> None:
    clean_question = str(question or "").strip()
    if not clean_question:
        return
    ss.messages.append({"role": "user", "content": clean_question})
    ss.active_chat_job_id = start_chat_job(
        clean_question,
        ss.run_id,
        list(selected_ids),
        list(titles),
    )
    ss.pending_q = None
    ss.pending_chat_request = None
    st.rerun()


def _check_and_collect_job() -> bool:
    """job 상태를 확인합니다. 완료 시 messages에 저장. 실행중이면 True."""
    job_id = ss.get("active_chat_job_id")
    if not job_id:
        return False

    job = get_chat_job(job_id)
    if not job:
        ss.messages.append({
            "role": "assistant",
            "content": "진행 중이던 답변 작업을 찾지 못했습니다.",
            "sources": [],
        })
        ss.active_chat_job_id = None
        return False

    status = job.get("status")
    if status == "running":
        return True

    if status == "done":
        ss.messages.append({
            "role": "assistant",
            "content": str(job.get("answer") or "문서에서 확인하지 못했습니다.").strip(),
            "sources": job.get("sources") or [],
        })
    elif status == "failed":
        ss.messages.append({
            "role": "assistant",
            "content": f"답변 생성 중 오류가 발생했습니다: {job.get('error') or '알 수 없는 오류'}",
            "sources": [],
        })

    clear_chat_job(job_id)
    ss.active_chat_job_id = None
    st.rerun()


# ── 가드 ──
if not ss.analyzed or not ss.analysis:
    st.markdown(
        '<div class="eyebrow">CHAT</div>'
        '<h2 class="sec-title" style="margin-bottom:18px">대화할 문서가 없습니다</h2>',
        unsafe_allow_html=True,
    )
    st.info("먼저 내부 문서 목록에서 분석할 문서를 선택해주세요.")
    if st.button("📚 문서 선택하러 가기", type="primary", key="chat_goto_docs"):
        st.switch_page(P_DOCS)
    st.stop()

selected_ids = list(ss.selected_doc_ids or [])
titles = _selected_titles()
data = ss.analysis or {}
job_running = _check_and_collect_job()

# ── polling: job 실행 중엔 최소 UI → sleep → rerun ──
if job_running:
    st.markdown(
        f'<div class="panel-title">💬 대화형 탐색 · {esc(_head_label(titles))}'
        f'<span class="status-wait" style="margin-left:12px">● 분석 중</span></div>',
        unsafe_allow_html=True,
    )
    st.caption("문서에서 근거를 찾는 중입니다...")
    # 모든 대화 메시지를 동일한 위치(bottom)에 표시
    for message in ss.messages:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(str(message["content"] or ""))
        else:
            with st.chat_message("assistant"):
                st.markdown(str(message["content"] or ""))
    with st.chat_message("assistant"):
        with st.spinner(""):
            time.sleep(2)
    st.rerun()

# ── job 완료: 전체 UI ──
h1, h2 = st.columns([3, 1], vertical_alignment="center")
with h1:
    st.markdown(
        f'<div class="panel-title">💬 대화형 탐색 · {esc(_head_label(titles))}'
        f'<span class="status-ok" style="margin-left:12px">● 분석 완료</span></div>',
        unsafe_allow_html=True,
    )
    if data.get("mode") == "rag" and ss.run_id:
        scope = f"선택한 {len(selected_ids)}개 문서" if len(selected_ids) > 1 else "선택한 문서"
        st.caption(f"{scope} 범위에서 검색합니다. 출처는 문서 내 실제 근거 위치입니다.")
    else:
        st.caption("RAG 미연결(Mock) 모드입니다. 예시 응답과 예시 출처가 표시됩니다.")
with h2:
    if st.button("분석 결과로 돌아가기", type="secondary", use_container_width=True, key="chat_back"):
        ss.pending_q = None
        ss.pending_chat_request = None
        st.switch_page(P_WORKSPACE)

st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

if ss.get("pending_q"):
    _start_question(str(ss.pending_q), selected_ids, titles)

st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

for message in ss.messages:
    role = message.get("role")
    if role == "user":
        with st.chat_message("user"):
            st.markdown(str(message.get("content") or ""))
    else:
        with st.chat_message("assistant"):
            st.markdown(str(message.get("content") or ""))
            _render_sources(message.get("sources") or [])
    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

suggested = ["사업 예산은?", "참가 자격은?", "제출 서류는?", "평가 기준은?"]
chip_cols = st.columns(4)
for col, question in zip(chip_cols, suggested):
    with col:
        if st.button(question, type="secondary", use_container_width=True, key=f"chat_chip_{question}"):
            _start_question(question, selected_ids, titles)

st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)

question = st.chat_input("선택한 문서에 대해 질문해보세요")
if question:
    _start_question(question, selected_ids, titles)
