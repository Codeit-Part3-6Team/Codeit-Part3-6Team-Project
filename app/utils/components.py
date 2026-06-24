"""
공통 UI 컴포넌트
================
여러 페이지에서 재사용하는 요소들 (아이콘, 상단 네비바, 푸터).
한 곳에서 고치면 모든 페이지에 반영됩니다.
"""

import streamlit as st


# ── SVG 아이콘 ────────────────────────────────────────────────────────────────
def _svg(paths, fill="none"):
    return (f'<svg viewBox="0 0 24 24" fill="{fill}" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{paths}</svg>')

IC_DOC    = _svg('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>')
IC_UPLOAD = _svg('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>')
IC_BOLT   = _svg('<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>')
IC_CHAT   = _svg('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>')
IC_CHART  = _svg('<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>')
IC_SHIELD = _svg('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>')
IC_FILES  = _svg('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="13" y2="17"/>')
IC_USERS  = _svg('<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>')

# 페이지 경로 (st.navigation 에 등록된 경로와 동일해야 함)
P_HOME      = "views/home.py"
P_ANALYZE   = "views/analyze.py"
P_WORKSPACE = "views/workspace.py"
P_PRICING   = "views/pricing.py"


def topbar():
    """상단 네비바: 좌측 브랜드 + 우측 페이지 링크(홈/요금제)."""
    left, right = st.columns([3, 1.3], vertical_alignment="center")
    with left:
        st.markdown(f'<div class="brand">{IC_DOC} BidAI</div>', unsafe_allow_html=True)
    with right:
        n1, n2 = st.columns(2)
        with n1:
            st.page_link(P_HOME, label="홈")
        with n2:
            st.page_link(P_PRICING, label="요금제")
    st.markdown('<div class="topbar-line"></div>', unsafe_allow_html=True)


def footer():
    st.markdown('<div class="foot">© 2026 BidAI · RFP 입찰 분석 서비스 · hello@bidai.kr</div>',
                unsafe_allow_html=True)
