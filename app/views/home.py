"""
홈 (랜딩 페이지)
================
히어로 → 통계 → 핵심 기능 → 하단 CTA → 푸터로 이어지는 연속 스크롤 화면.
외부 업로드가 없는 '내부 RFP 문서 분석' 서비스에 맞춰 문구·동선을 구성했습니다.
CTA 는 모두 문서 목록(documents) 페이지로 연결됩니다.
"""

import streamlit as st

from utils.components import (
    topbar, footer, P_DOCS, P_PRICING,
    IC_SEARCH, IC_BOLT, IC_CHAT, IC_SHIELD, IC_FILES, IC_LAYERS,
)

ss = st.session_state
topbar()

# ── 히어로 ───────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-pad"></div>', unsafe_allow_html=True)
left, right = st.columns([1.05, 0.95], gap="large")

with left:
    st.markdown("""
    <div class="badge">✦ AI 기반 RFP 분석 엔진</div>
    <div class="hero-title">공공 입찰 문서 분석,<br><span class="accent">AI</span>가 대신합니다</div>
    <div class="hero-sub">나라장터 RFP 문서 98건이 이미 분석 준비를 마쳤습니다.
    문서를 선택하면 핵심 요약과 요구사항을 바로 확인하고, 궁금한 점은 출처와 함께 질문할 수 있습니다.</div>
    """, unsafe_allow_html=True)

    b1, _ = st.columns([1.15, 2.05])
    with b1:
        if st.button("문서 분석 시작하기  ›", type="primary", use_container_width=True, key="hero_start"):
            st.switch_page(P_DOCS)

with right:
    st.markdown(f"""
    <div class="upload-card">
      <div class="upload-ico">{IC_LAYERS}</div>
      <div class="upload-title">내부 RFP 문서 98건 분석 준비 완료</div>
      <div class="upload-sub">사업명·발주기관으로 검색 → 선택 → 즉시 분석</div>
      <div class="pill-row"><span class="pill">요약</span>
      <span class="pill">요구사항</span><span class="pill">질의응답</span></div>
    </div>
    """, unsafe_allow_html=True)

    c = st.columns([1, 2, 1])[1]
    with c:
        if st.button("문서 목록 둘러보기  →", type="secondary",
                     use_container_width=True, key="home_browse"):
            st.switch_page(P_DOCS)

# ── 통계 ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="stats">
  <div class="stat"><div class="stat-num">98건</div><div class="stat-label">분석 가능한 내부 문서</div></div>
  <div class="stat"><div class="stat-num">85곳</div><div class="stat-label">발주기관 커버</div></div>
  <div class="stat"><div class="stat-num">5초</div><div class="stat-label">평균 응답 시간</div></div>
  <div class="stat"><div class="stat-num">RAG</div><div class="stat-label">출처 기반 답변</div></div>
</div>
""", unsafe_allow_html=True)

# ── 핵심 기능 ────────────────────────────────────────────────────────────────
feats = [
    (IC_SEARCH,  "문서 검색·선택", "사업명·발주기관으로 원하는 RFP를 찾아 바로 선택합니다.", "row1"),
    (IC_BOLT,    "즉각적인 요약",  "선택한 문서의 핵심 내용을 AI가 정리해 보여줍니다.", "row1"),
    (IC_CHAT,    "대화형 탐색",    "궁금한 걸 물어보면 문서 어디에 나온 내용인지와 함께 답변합니다.", "row1"),
    (IC_FILES,   "핵심 요구사항",  "제출서류·참가자격·평가기준처럼 실무자가 먼저 확인할 항목을 정리합니다.", "row2"),
    (IC_FILES,   "다양한 형식",    "PDF, DOCX, HWP 등 공공기관 문서를 모두 처리해 두었습니다.", "row2"),
    (IC_SHIELD,  "안전한 인덱스",  "내부에 구축된 문서 인덱스만 사용해 안정적으로 동작합니다.", "row2"),
]
cards = "".join(
    f'<div class="feat-card {cls}"><div class="feat-icon">{ic}</div>'
    f'<div class="feat-name">{name}</div><div class="feat-desc">{desc}</div></div>'
    for ic, name, desc, cls in feats
)
st.markdown(f"""
<div class="section">
  <div class="eyebrow">핵심 기능</div>
  <h2 class="sec-title">왜 IT'S MINE인가요?</h2>
  <div class="feat-grid">{cards}</div>
</div>
""", unsafe_allow_html=True)

# ── 하단 CTA ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="cta">
  <div class="cta-title">지금 바로 시작해보세요</div>
  <div class="cta-sub">문서 선택 → 요약 확인 → 질문까지 한 화면에서</div>
</div>
""", unsafe_allow_html=True)
c = st.columns([1, 1, 1])[1]
with c:
    if st.button("문서 분석 시작하기  ›", type="primary", use_container_width=True, key="cta_start"):
        st.switch_page(P_DOCS)

footer()
