"""
BidAI · RFP 입찰 분석 서비스 (데모)
====================================
실행:  python -m streamlit run bidai_app/app py (프로젝트 루트에서)

이 파일은 '진입점'입니다. 하는 일은 3가지뿐:
  1) 페이지 공통 설정(set_page_config) + 전역 CSS 주입
  2) 페이지 4개 등록 (홈 / 분석하기 / 워크스페이스 / 요금제)
  3) 내비게이션 실행

실제 화면 코드는 views/ 폴더, 공통 코드는 utils/ 폴더에 있습니다.
"""

import streamlit as st
from utils.styles import CSS

# ── 1) 공통 설정 + 전역 스타일 (모든 페이지에 적용) ──────────────────────────
st.set_page_config(
    page_title="BidAI · RFP 입찰 분석",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)

# ── 공유 세션 상태 (페이지가 바뀌어도 유지됨) ────────────────────────────────
ss = st.session_state
ss.setdefault("doc_name", None)     # 업로드/선택한 문서명
ss.setdefault("analyzed", False)    # 분석 완료 여부
ss.setdefault("analysis", None)     # 분석 결과 dict
ss.setdefault("messages", [])       # 채팅 기록
ss.setdefault("pending_q", None)    # 추천 질문 클릭 처리용

# ── 2) 페이지 등록 ───────────────────────────────────────────────────────────
home = st.Page("views/home.py", title="홈", icon="🏠", default=True)
analyze = st.Page("views/analyze.py", title="분석하기", icon="📤")
workspace = st.Page("views/workspace.py", title="워크스페이스", icon="🗂️")
pricing = st.Page("views/pricing.py", title="요금제", icon="💳")

# ── 3) 내비게이션 실행 ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)

pg = st.navigation([home, analyze, workspace, pricing])
pg.run()
