"""
서비스 소개 (about)
===================
IT'S MINE 이 어떤 서비스인지 소개하는 독립 페이지.
상단바의 '서비스 소개' 링크가 이 페이지로 연결됩니다.

문구는 아래 LEAD / FEATURES / STEPS 만 고치면 되도록 한곳에 모았습니다.
"""

import streamlit as st

from utils.components import (
    topbar, footer, P_DOCS, P_PRICING,
    IC_BOLT, IC_CHAT, IC_SHIELD,
)

topbar()

# ── 히어로 ───────────────────────────────────────────────────────────────────
st.markdown('<div style="height:18px"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="eyebrow">ABOUT</div>'
    '<h2 class="sec-title" style="margin-bottom:18px">'
    '입찰 준비의 시간을 줄이는<br>가장 빠른 방법</h2>'
    '<div class="about-lead">'
    'IT\'S MINE 은 나라장터에 올라온 RFP(제안요청서)를 미리 수집·분석해 둔 '
    '내부 문서 분석 서비스입니다. 수백 페이지짜리 공고문을 AI가 대신 읽어, '
    '핵심 요구사항·예산·일정·참가자격을 자동으로 뽑아줍니다. '
    '문서를 선택하기만 하면 요약부터 출처 기반 질의응답까지 한 화면에서 확인할 수 있습니다.'
    '</div>', unsafe_allow_html=True)

# ── 무엇을 해주나 (3카드) ────────────────────────────────────────────────────
FEATURES = [
    (IC_BOLT,    "핵심 요약",   "수백 페이지를 몇 초 만에 요약합니다. 사업 개요·요구사항·제출 조건을 한눈에 확인하세요."),
    (IC_CHAT,    "대화형 탐색", "RAG 기반 챗봇에게 \u201c참가 자격은?\u201d처럼 물어보면, 문서 속 출처(페이지)와 함께 답해줍니다."),
    (IC_SHIELD,  "근거 확인",   "답변에 사용된 문서 위치를 함께 보여주어 중요한 입찰 조건을 다시 검증할 수 있습니다."),
]
st.markdown('<div class="eyebrow" style="margin-top:46px">무엇을 해주나요</div>',
            unsafe_allow_html=True)
cards = "".join(
    f'<div class="about-card"><div class="about-ico">{ic}</div>'
    f'<div class="about-card-name">{name}</div>'
    f'<div class="about-card-desc">{desc}</div></div>'
    for ic, name, desc in FEATURES
)
st.markdown(f'<div class="about-grid">{cards}</div>', unsafe_allow_html=True)

# ── 어떻게 쓰나 (단계) ───────────────────────────────────────────────────────
STEPS = [
    ("1", "문서 검색·선택", "내부에 등록된 나라장터 RFP 문서를 사업명·발주기관으로 검색해 선택합니다."),
    ("2", "AI 분석",       "선택한 문서의 핵심 요약·요구사항·메타정보(예산·발주기관)를 자동으로 추출합니다."),
    ("3", "워크스페이스",  "추출된 요약을 확인하고, 궁금한 점은 챗봇에게 출처와 함께 바로 질문할 수 있습니다."),
]
st.markdown('<div class="eyebrow" style="margin-top:54px">어떻게 쓰나요</div>'
            '<div class="panel" style="margin-top:14px">'
            + "".join(
                f'<div class="about-step"><div class="about-step-num">{n}</div>'
                f'<div><div class="about-step-t">{t}</div>'
                f'<div class="about-step-d">{d}</div></div></div>'
                for n, t, d in STEPS
            )
            + '</div>', unsafe_allow_html=True)

# ── 마무리 CTA ───────────────────────────────────────────────────────────────
st.markdown('<div style="height:30px"></div>', unsafe_allow_html=True)
b1, b2, _ = st.columns([1, 1, 2])
with b1:
    if st.button("문서 분석 시작하기  ›", type="primary", use_container_width=True, key="about_start"):
        st.switch_page(P_DOCS)
with b2:
    if st.button("요금제 보기", type="secondary", use_container_width=True, key="about_pricing"):
        st.switch_page(P_PRICING)

st.markdown('<div style="height:40px"></div>', unsafe_allow_html=True)
footer()
