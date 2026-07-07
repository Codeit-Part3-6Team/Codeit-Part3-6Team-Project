"""
IT'S MINE · 내부 RFP 문서 분석 서비스 (데모)
=============================================
실행:  python -m streamlit run app.py

이 서비스는 '내부에 미리 인덱싱된 나라장터 RFP 문서(약 98건)'를 대상으로 합니다.
사용자는 파일을 올리지 않고, 목록에서 문서를 검색·선택해 요약·질문합니다.

이 파일은 '진입점'입니다. 하는 일은 3가지뿐:
  1) 페이지 공통 설정(set_page_config) + 전역 CSS 주입
  2) 페이지 등록 (홈 / 서비스 소개 / 문서 분석 / 정부제안서 검색 / 워크스페이스 / 요금제)
  3) 내비게이션 실행 (사이드바는 숨김 → 상단바로만 이동)

실제 화면 코드는 views/ 폴더, 공통 코드는 utils/ 폴더에 있습니다.
"""

import streamlit as st
from utils.styles import CSS

# ── 1) 공통 설정 + 전역 스타일 (모든 페이지에 적용) ──────────────────────────
st.set_page_config(
    page_title="IT'S MINE · 내부 RFP 문서 분석",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(CSS, unsafe_allow_html=True)

# ── 공유 세션 상태 (페이지가 바뀌어도 유지됨) ────────────────────────────────
ss = st.session_state
ss.setdefault("run_id", None)            # 내부 corpus run ID (백엔드 인덱스 식별자)
ss.setdefault("corpus_mode", None)       # "rag" | "mock"
ss.setdefault("selected_doc_ids", [])    # 선택한 문서 ID 목록
ss.setdefault("selected_docs", [])       # 선택한 문서 레코드(title/org/amount 등)
ss.setdefault("analyzed", False)         # 분석(요약/요구사항) 완료 여부
ss.setdefault("analysis", None)          # 분석 결과 dict
ss.setdefault("messages", [])            # 채팅 기록
ss.setdefault("pending_q", None)         # 추천 질문 클릭 처리용
ss.setdefault("pending_chat_request", None)  # rerun 후 안전하게 처리할 채팅 요청
ss.setdefault("active_chat_job_id", None)    # 백그라운드 채팅 job ID

# ── 2) 페이지 등록 ───────────────────────────────────────────────────────────
home = st.Page("views/home.py", title="홈", icon="🏠", default=True)
about = st.Page("views/about.py", title="서비스 소개", icon="✨")
documents = st.Page("views/documents.py", title="문서 분석", icon="📚")
search = st.Page("views/search.py", title="정부제안서 검색", icon="🔎")
workspace = st.Page("views/workspace.py", title="워크스페이스", icon="🗂️")
chat = st.Page("views/chat.py", title="대화형 탐색", icon="💬")
pricing = st.Page("views/pricing.py", title="요금제", icon="💳")

# ── 3) 내비게이션 실행 ───────────────────────────────────────────────────────
# position="hidden" : 자동 사이드바 메뉴를 만들지 않음. 이동은 상단바로만.
pg = st.navigation(
    [home, about, documents, search, workspace, chat, pricing],
    position="hidden",
)
pg.run()
