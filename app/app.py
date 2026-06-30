"""
IT'S MINE · RFP 입찰 분석 서비스 (데모)
======================================
실행:  python -m streamlit run app.py

이 파일은 '진입점'입니다. 하는 일은 3가지뿐:
  1) 페이지 공통 설정(set_page_config) + 전역 CSS 주입
  2) 페이지 등록 (홈 / 서비스 소개 / 분석하기 / 정부제안서 검색 / 워크스페이스 / 요금제)
  3) 내비게이션 실행 (단, 사이드바는 숨김 → 상단바로만 이동)

실제 화면 코드는 views/ 폴더, 공통 코드는 utils/ 폴더에 있습니다.
"""

import streamlit as st
from utils.styles import CSS

# ── 1) 공통 설정 + 전역 스타일 (모든 페이지에 적용) ──────────────────────────
st.set_page_config(
    page_title="IT'S MINE · RFP 입찰 분석",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="auto",
)
st.markdown(CSS, unsafe_allow_html=True)

# ── 공유 세션 상태 (페이지가 바뀌어도 유지됨) ────────────────────────────────
ss = st.session_state
ss.setdefault("mode", "demo")        # "demo" | "real"
ss.setdefault("run_id", None)       # real 모드: experiments/streamlit/{run_id}
ss.setdefault("doc_name", None)     # 데모 모드: 업로드/선택한 문서명
ss.setdefault("analyzed", False)    # 분석 완료/ready 여부
ss.setdefault("analysis", None)     # 분석 결과 dict
ss.setdefault("messages", [])       # 채팅 기록
ss.setdefault("pending_q", None)    # 추천 질문 클릭 처리용

# ── 2) 사이드바: 모드 선택 + run 목록 ────────────────────────────────────────
with st.sidebar:
    st.markdown("## IT'S MINE")
    st.caption("RFP 입찰 분석")

    prev_mode = ss.mode
    ss.mode = st.radio(
        "운영 모드",
        options=["demo", "real"],
        format_func=lambda m: "데모 모드" if m == "demo" else "실전 모드",
        horizontal=True,
    )
    if ss.mode != prev_mode:
        # 모드 전환 시 상태 초기화
        ss.doc_name = None
        ss.analyzed = False
        ss.analysis = None
        ss.messages = []
        ss.run_id = None
        from app.services.rag_service import clear_chatbot
        clear_chatbot()

    st.markdown("---")

    if ss.mode == "demo":
        st.caption("데모 모드: 가상 데이터로 UI 체험")
    else:
        st.caption("실전 모드: 문서 업로드 → RAG 분석 → 챗봇")
        # 기존 run 선택
        from app.services.rag_service import list_runs
        runs = list_runs()
        if runs:
            run_options = {r["run_id"]: f"{r['run_id'][:20]}... ({r['status']})" for r in runs}
            selected_run = st.selectbox(
                "기존 분석 선택",
                options=[""] + list(run_options.keys()),
                format_func=lambda r: run_options.get(r, "새로 업로드"),
            )
            if selected_run:
                ss.run_id = selected_run
                ss.analyzed = True
                ss.doc_name = selected_run

# ── 3) 페이지 등록 ───────────────────────────────────────────────────────────
# st.page_link 로 이동하려면 그 페이지가 아래 목록에 등록돼 있어야 합니다.
home = st.Page("views/home.py", title="홈", icon="🏠", default=True)
about = st.Page("views/about.py", title="서비스 소개", icon="✨")
analyze = st.Page("views/analyze.py", title="분석하기", icon="📤")
search = st.Page("views/search.py", title="정부제안서 검색", icon="🔎")
workspace = st.Page("views/workspace.py", title="워크스페이스", icon="🗂️")
pricing = st.Page("views/pricing.py", title="요금제", icon="💳")

# ── 4) 내비게이션 실행 ───────────────────────────────────────────────────────
# position="hidden" : 자동 사이드바 메뉴를 만들지 않음(요구사항 5: 사이드바 삭제).
#                     페이지 이동은 상단바(topbar)로만 합니다.
pg = st.navigation(
    [home, about, analyze, search, workspace, pricing],
    position="hidden",
)
pg.run()
