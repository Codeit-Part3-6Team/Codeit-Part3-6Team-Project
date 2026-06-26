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
P_ABOUT     = "views/about.py"    # 신규: 서비스 소개 페이지
P_ANALYZE   = "views/analyze.py"
P_WORKSPACE = "views/workspace.py"
P_PRICING   = "views/pricing.py"
P_SEARCH    = "views/search.py"   # 정부제안서 검색(외부 사이트 모음)


def topbar():
    """상단 네비바 (A안 레이아웃).
    좌측 끝 : 브랜드 'IT'S MINE' (크게 · 클릭하면 홈으로 이동)
    우측 끝 : 서비스 소개 / 정부제안서 검색 / 요금제 (균등 폭으로 모음)
    """
    # 왼쪽 브랜드 영역은 넓게 잡아 IT'S MINE 을 왼쪽 끝에 두고,
    # 오른쪽 메뉴 영역은 좁게 잡아 3개를 오른쪽 끝으로 몰아준다.
    left, mid, right = st.columns([2, 3, 3], vertical_alignment="center")
    with left:
        # 브랜드 자체가 '홈으로 가는 링크'(요구사항 2).
        # st.container(key="brandbar") → div 에 'st-key-brandbar' 클래스가 붙어
        # styles.py 에서 이 링크만 크게 키운다(요구사항 1).
        with st.container(key="brandbar"):
            st.page_link(P_HOME, label="IT'S MINE")
    with right:
        # 메뉴 3개를 같은 폭으로 나란히 → 오른쪽에 균등 배치.
        # st.container(key="navbar") → hover 효과를 이 메뉴에만 적용(요구사항 4).
        with st.container(key="navbar"):
            n1, n2, n3 = st.columns(3)
            with n1:
                st.page_link(P_ABOUT, label="서비스 소개")
            with n2:
                st.page_link(P_SEARCH, label="정부제안서 검색")
            with n3:
                st.page_link(P_PRICING, label="요금제")
    st.markdown('<div class="topbar-line"></div>', unsafe_allow_html=True)


def footer():
    st.markdown('<div class="foot">© 2026 IT\'S MINE · RFP 입찰 분석 서비스 · hello@bidai.kr</div>',
                unsafe_allow_html=True)
