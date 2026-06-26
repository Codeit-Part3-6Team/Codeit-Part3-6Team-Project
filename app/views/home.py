"""
홈 (랜딩 페이지)
================
캡처 1 → 2 → 3 을 위→아래로 이어 붙인 연속 스크롤 화면.
히어로 → 통계 → 핵심 기능 → 하단 CTA → 푸터.
"""

import streamlit as st
from utils.components import (
    topbar, footer, P_ANALYZE, P_PRICING,
    IC_UPLOAD, IC_BOLT, IC_CHAT, IC_CHART, IC_SHIELD, IC_FILES, IC_USERS,
)

ss = st.session_state
topbar()

# ── 캡처 1: 히어로 ───────────────────────────────────────────────────────────
st.markdown('<div class="hero-pad"></div>', unsafe_allow_html=True)
left, right = st.columns([1.05, 0.95], gap="large")

with left:
    st.markdown("""
    <div class="badge">✦ AI 기반 RFP 분석 엔진</div>
    <div class="hero-title">입찰 문서 분석,<br><span class="accent">AI</span>가 대신합니다</div>
    <div class="hero-sub">수백 페이지의 RFP 문서를 몇 초 만에 분석하고,
    핵심 요구사항과 경쟁 포인트를 자동으로 추출합니다.</div>
    """, unsafe_allow_html=True)

    b1, _ = st.columns([1.15, 2.05])
    with b1:
        if st.button("무료로 시작하기  ›", type="primary", use_container_width=True, key="hero_start"):
            st.switch_page(P_ANALYZE)

with right:
    st.markdown(f"""
    <div class="upload-card">
      <div class="upload-ico">{IC_UPLOAD}</div>
      <div class="upload-title">RFP 문서를 드래그하거나 클릭하세요</div>
      <div class="upload-sub">PDF, DOCX, HWP 지원 · 최대 200MB</div>
      <div class="pill-row"><span class="pill">.PDF</span>
      <span class="pill">.DOCX</span><span class="pill">.HWP</span></div>
    </div>
    """, unsafe_allow_html=True)

    up = st.file_uploader("RFP 파일 업로드", type=["pdf", "docx", "hwp", "txt"],
                          label_visibility="collapsed", key="home_upload")
    if up is not None:
        ss.doc_name = up.name
        ss.analyzed = False
        st.switch_page(P_ANALYZE)

    c = st.columns([1, 2, 1])[1]
    with c:
        if st.button("샘플 문서로 바로 체험하기  →", type="secondary",
                     use_container_width=True, key="home_sample"):
            ss.doc_name = "샘플_전자조달시스템_RFP.pdf"
            ss.analyzed = False
            st.switch_page(P_ANALYZE)

# ── 통계 ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="stats">
  <div class="stat"><div class="stat-num">12,000+</div><div class="stat-label">분석 완료 문서</div></div>
  <div class="stat"><div class="stat-num">92.5%</div><div class="stat-label">추출 정확도</div></div>
  <div class="stat"><div class="stat-num">5초</div><div class="stat-label">평균 분석 시간</div></div>
  <div class="stat"><div class="stat-num">340개</div><div class="stat-label">도입 기업</div></div>
</div>
""", unsafe_allow_html=True)

# ── 캡처 2: 핵심 기능 ────────────────────────────────────────────────────────
feats = [
    (IC_BOLT,   "즉각적인 요약", "수백 페이지 문서를 AI가 핵심 내용으로 정리합니다.", "row1"),
    (IC_CHAT,   "대화형 탐색",   "궁금한 걸 물어보면 문서 어디에 나온 내용인지와 함께 답변합니다", "row1"),
    (IC_CHART,  "경쟁력 분석",   "낙찰 가능성을 높이는 핵심 전략 포인트를 추출합니다.", "row1"),
    (IC_SHIELD, "보안 처리",     "비밀 문서를 철저한 암호화로 안전하게 지킵니다.", "row2"),
    (IC_FILES,  "다양한 형식",   "PDF, DOCX, HWP 등 공공기관 문서를 모두 지원합니다.", "row2"),
    (IC_USERS,  "팀 협업",       "분석 결과를 팀원과 공유하고 함께 전략을 수립하세요.", "row2"),
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

# ── 캡처 3: 하단 CTA ─────────────────────────────────────────────────────────
st.markdown("""
<div class="cta">
  <div class="cta-title">지금 바로 시작해보세요</div>
  <div class="cta-sub">무료 체험 · 간편 결제 · 즉시 사용 가능</div>
</div>
""", unsafe_allow_html=True)
c = st.columns([1, 1, 1])[1]
with c:
    if st.button("요금제 보기  ›", type="primary", use_container_width=True, key="cta_pricing"):
        st.switch_page(P_PRICING)

footer()
