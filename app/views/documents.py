"""
문서 분석 (내부 문서 목록 · 검색 · 선택)
=========================================
내부에 미리 인덱싱된 RFP 문서(약 98건)를 검색하고 선택하는 화면.
외부 파일 업로드는 없습니다 — 문서를 고르면 바로 분석이 시작됩니다.

- 검색칸: 사업명·발주기관으로 실시간 필터
- 문서 카드: [분석 →] 단일 문서 분석 / [☐ 비교 담기] 여러 문서 비교
- 2건 이상 담으면 상단 바에서 [선택 문서 N건 분석] 실행

백엔드 연결은 services/frontend_adapter.py 를 통합니다:
  - VM(src/ 존재): 실제 RAG corpus run 의 문서 목록
  - 로컬(src/ 없음): 동일한 98건 메타데이터(Mock)로 미리보기
"""

import streamlit as st

from utils.components import topbar, footer, esc, P_WORKSPACE
from services.frontend_adapter import backend_mode, internal_corpus, analyze_selection

ss = st.session_state
topbar()

st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
st.markdown('<div class="eyebrow">DOCUMENTS</div>'
            '<h2 class="sec-title" style="margin-bottom:10px">내부 RFP 문서 분석</h2>'
            '<div style="color:var(--text-2);margin-bottom:4px">'
            '등록된 나라장터 RFP 문서를 검색하고, 분석할 문서를 선택하세요. '
            '여러 문서를 담으면 비교 분석도 가능합니다.</div>',
            unsafe_allow_html=True)

# ── 백엔드 모드 배너 (F1: 비정상 폴백은 빨간색으로 분명히 표시) ──────────────
_mode = backend_mode()
if _mode["mode"] == "rag":
    st.caption("🟢 " + _mode["detail"])
elif _mode["healthy"]:
    st.caption("🟡 " + _mode["detail"])
else:
    st.error("🔴 " + _mode["detail"])

# ── 내부 문서 목록 로드 ──────────────────────────────────────────────────────
corpus = internal_corpus()
ss.corpus_mode = corpus["mode"]
ss.run_id = corpus["run_id"]
documents = corpus["documents"]

if corpus["error"] and not documents:
    st.warning(corpus["error"])
    footer()
    st.stop()

# 문서 수가 비정상적으로 적을 때(예: 예전 업로드 테스트 run) 안내
if corpus.get("warning"):
    st.warning("⚠️ " + corpus["warning"])

# ── 검색칸 ───────────────────────────────────────────────────────────────────
sc1, sc2 = st.columns([3, 1], vertical_alignment="center")
with sc1:
    query = st.text_input(
        "문서 검색",
        placeholder="사업명 또는 발주기관으로 검색  (예: 시스템 고도화, 한국수자원공사)",
        label_visibility="collapsed",
        key="doc_query",
    )
with sc2:
    st.markdown(
        f'<div class="doc-count" style="text-align:right">총 <b>{len(documents)}</b>건 보유</div>',
        unsafe_allow_html=True)

# 사업명 / 발주기관 / 문서ID 부분일치 (대소문자·공백 무시)
def _match(doc: dict, q: str) -> bool:
    q = q.strip().lower()
    if not q:
        return True
    hay = " ".join(str(doc.get(k) or "") for k in ("title", "org", "document_id")).lower()
    return all(tok in hay for tok in q.split())

filtered = [d for d in documents if _match(d, query or "")]

st.markdown(
    f'<div class="doc-count" style="margin:2px 0 10px">검색 결과 '
    f'<b>{len(filtered)}</b>건</div>', unsafe_allow_html=True)

# ── 선택 상태 헬퍼 ───────────────────────────────────────────────────────────
def _selected_ids() -> list[str]:
    return list(ss.selected_doc_ids or [])


def _toggle(doc_id: str, doc: dict, on: bool) -> None:
    ids = _selected_ids()
    if on and doc_id not in ids:
        ids.append(doc_id)
        ss.selected_docs = ss.selected_docs + [doc]
    if not on and doc_id in ids:
        ids.remove(doc_id)
        ss.selected_docs = [d for d in ss.selected_docs if d.get("document_id") != doc_id]
    ss.selected_doc_ids = ids


def _reset_workspace() -> None:
    """새 분석을 시작할 때 이전 결과/대화를 비웁니다 (F5와 동일한 초기화 규칙)."""
    ss.analyzed = False
    ss.analysis = None
    ss.messages = []
    ss.pending_q = None


def _run_analysis(doc_ids: list[str], docs: list[dict]) -> None:
    """선택 문서를 분석하고 워크스페이스로 이동합니다."""
    titles = [str(d.get("title") or d.get("document_id")) for d in docs]
    with st.spinner(f"{len(doc_ids)}개 문서를 분석하고 있습니다... (요약 → 요구사항 추출)"):
        result = analyze_selection(ss.run_id, doc_ids, titles)

    if result["error"] and not result["summary"]:
        st.error(f"분석에 실패했습니다: {result['error']}")
        return
    if result["error"]:
        st.warning(f"일부 분석이 실패했습니다: {result['error']}")

    ss.selected_doc_ids = doc_ids
    ss.selected_docs = docs
    ss.analysis = result
    ss.analyzed = True
    ss.messages = []
    ss.pending_q = None
    st.switch_page(P_WORKSPACE)


# ── 선택 바 (2건 이상 담았을 때 비교 분석 실행) ─────────────────────────────
picked = _selected_ids()
if picked:
    names = " · ".join(
        esc(d.get("title")) for d in ss.selected_docs[:3]
    ) + (" 외" if len(picked) > 3 else "")
    st.markdown(
        f'<div class="sel-bar"><div class="sel-bar-t">🗂️ 선택한 문서 {len(picked)}건</div>'
        f'<div class="sel-bar-d">{names}</div></div>',
        unsafe_allow_html=True)
    b1, b2, _sp = st.columns([1.3, 1, 2.7])
    with b1:
        label = ("📊 선택 문서 비교 분석" if len(picked) >= 2
                 else "⚡ 선택 문서 분석 시작")
        if st.button(label, type="primary", use_container_width=True, key="run_selected"):
            _reset_workspace()
            _run_analysis(picked, list(ss.selected_docs))
    with b2:
        if st.button("선택 비우기", type="secondary", use_container_width=True, key="clear_sel"):
            ss.selected_doc_ids = []
            ss.selected_docs = []
            st.rerun()

# ── 문서 카드 그리드 (3열) ───────────────────────────────────────────────────
if not filtered:
    st.info("검색 결과가 없습니다. 다른 키워드로 검색해보세요.")
else:
    N_COLS = 3
    for row_start in range(0, len(filtered), N_COLS):
        cols = st.columns(N_COLS, gap="medium")
        for col, doc in zip(cols, filtered[row_start:row_start + N_COLS]):
            doc_id = str(doc.get("document_id"))
            title = str(doc.get("title") or doc_id)
            org = str(doc.get("org") or "")
            amount = str(doc.get("amount") or "")
            summary = str(doc.get("summary") or "")
            chunks = doc.get("chunk_count")
            is_sel = doc_id in picked

            with col:
                # F2: 문서에서 온 값(title/org/summary)은 전부 esc() 처리
                chips = ""
                if org:
                    chips += f'<span class="doc-chip">🏛 {esc(org)}</span>'
                if amount:
                    chips += f'<span class="doc-chip amt">{esc(amount)}</span>'
                if chunks:
                    chips += f'<span class="doc-chip">{esc(chunks)} chunks</span>'
                sum_html = (f'<div class="doc-sum">{esc(summary)}</div>'
                            if summary else "")
                card_cls = "doc-card selected" if is_sel else "doc-card"
                st.markdown(
                    f'<div class="{card_cls}">'
                    f'<div class="doc-title" title="{esc(title)}">{esc(title)}</div>'
                    f'<div class="doc-meta">{chips}</div>{sum_html}</div>',
                    unsafe_allow_html=True)

                a1, a2 = st.columns([1, 1])
                with a1:
                    if st.button("분석 →", type="primary", use_container_width=True,
                                 key=f"go_{doc_id}"):
                        _reset_workspace()
                        _run_analysis([doc_id], [doc])
                with a2:
                    st.checkbox(
                        "비교 담기", value=is_sel, key=f"pick_{doc_id}",
                        on_change=lambda d=doc, i=doc_id: _toggle(
                            i, d, st.session_state.get(f"pick_{i}", False)),
                    )
        st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)

footer()
