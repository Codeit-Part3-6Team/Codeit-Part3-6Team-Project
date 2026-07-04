"""
공통 UI 컴포넌트
================
여러 페이지에서 재사용하는 요소들 (아이콘, 상단 네비바, 푸터, HTML 이스케이프).
한 곳에서 고치면 모든 페이지에 반영됩니다.
"""

import html

import streamlit as st


# ── HTML 이스케이프 (F2: unsafe_allow_html 주입값 보호) ───────────────────────
def esc(value) -> str:
    """사용자/문서에서 온 문자열을 HTML 에 넣기 전에 이스케이프합니다.

    문서 제목·요약·요구사항·발주기관 등은 `<`, `&`, 따옴표를 포함할 수 있어,
    st.markdown(..., unsafe_allow_html=True) 에 그대로 넣으면 레이아웃이 깨지거나
    HTML 주입이 될 수 있습니다. 화면에 넣는 모든 동적 문자열은 이 함수를 거칩니다.
    """
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


# ── SVG 아이콘 ────────────────────────────────────────────────────────────────
def _svg(paths, fill="none"):
    return (f'<svg viewBox="0 0 24 24" fill="{fill}" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{paths}</svg>')

IC_DOC    = _svg('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>')
IC_SEARCH = _svg('<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>')
IC_BOLT   = _svg('<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>')
IC_CHAT   = _svg('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>')
IC_CHART  = _svg('<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>')
IC_SHIELD = _svg('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>')
IC_FILES  = _svg('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="13" y2="17"/>')
IC_USERS  = _svg('<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>')
IC_LAYERS = _svg('<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>')
IC_COMPARE = _svg('<line x1="12" y1="3" x2="12" y2="21"/><polyline points="8 8 4 12 8 16"/><polyline points="16 8 20 12 16 16"/>')

# 페이지 경로 (st.navigation 에 등록된 경로와 동일해야 함)
P_HOME      = "views/home.py"
P_ABOUT     = "views/about.py"       # 서비스 소개
P_DOCS      = "views/documents.py"   # 내부 문서 목록/검색/선택 (구 analyze)
P_WORKSPACE = "views/workspace.py"   # 요약·요구사항·질문
P_PRICING   = "views/pricing.py"
P_SEARCH    = "views/search.py"      # 정부제안서 검색(외부 사이트 모음)


def topbar():
    """상단 네비바.
    좌측 끝 : 브랜드 'IT'S MINE' (크게 · 클릭하면 홈으로 이동)
    우측 끝 : 서비스 소개 / 정부제안서 검색 / 요금제 (균등 폭으로 모음)
    """
    left, mid, right = st.columns([2, 3, 3], vertical_alignment="center")
    with left:
        with st.container(key="brandbar"):
            st.page_link(P_HOME, label="IT'S MINE")
    with right:
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
    st.markdown('<div class="foot">© 2026 IT\'S MINE · 내부 RFP 문서 분석 서비스 · hello@itsmine.kr</div>',
                unsafe_allow_html=True)
