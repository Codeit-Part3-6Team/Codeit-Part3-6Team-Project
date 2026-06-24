"""
요금제
======
Free / Pro / Enterprise 3단 요금제 (Mock).
"""

import streamlit as st
from utils.components import topbar, footer, P_ANALYZE

ss = st.session_state
topbar()

st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
st.markdown('<div class="eyebrow">PRICING</div>'
            '<h2 class="sec-title" style="margin-bottom:8px">요금제</h2>'
            '<div style="color:var(--text-2);margin-bottom:10px">'
            '무료 체험 · 신용카드 불필요 · 즉시 사용 가능</div>', unsafe_allow_html=True)

plans = [
    ("Free", "₩0", "/월", ["문서 5건/월 분석", "기본 요약 추출", "PDF 지원"], False),
    ("Pro", "₩49,000", "/월",
     ["문서 무제한 분석", "RAG 대화형 탐색", "PDF·DOCX·HWP 전체 지원", "경쟁력 분석 리포트"], True),
    ("Enterprise", "별도 문의", "",
     ["전용 인프라 · SSO", "온프레미스 배포", "전담 지원 매니저", "보안 인증 대응"], False),
]

cards = ""
for name, tag, per, feats, pop in plans:
    badge = '<div class="pop-badge">가장 인기</div>' if pop else ''
    flist = "".join(f'<div class="price-feat">✓ {f}</div>' for f in feats)
    cls = "price-card popular" if pop else "price-card"
    cards += (f'<div class="{cls}">{badge}<div class="price-name">{name}</div>'
              f'<div class="price-tag">{tag}<small>{per}</small></div>{flist}</div>')
st.markdown(f'<div class="price-grid">{cards}</div>', unsafe_allow_html=True)

st.markdown('<div style="height:26px"></div>', unsafe_allow_html=True)
c = st.columns([1, 1, 1])[1]
with c:
    if st.button("무료로 시작하기  ›", type="primary", use_container_width=True, key="pricing_start"):
        st.switch_page(P_ANALYZE)

st.markdown('<div style="height:50px"></div>', unsafe_allow_html=True)
footer()
