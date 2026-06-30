"""
전역 스타일 (CSS)
=================
모든 페이지가 공유하는 디자인. 색·폰트·여백을 한 곳에서 관리합니다.
색감을 바꾸고 싶으면 아래 :root 의 색상 값만 수정하세요.
"""

CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');

:root{
  --bg:#080b13;
  --bg-soft:#0b0f18;
  --panel:#0f1420;
  --panel-2:#121828;
  --border:#1b2333;
  --border-soft:#161d2a;
  --blue:#4f7cff;
  --blue-bright:#7aa0ff;
  --text:#e9ecf3;
  --text-2:#878fa3;
  --text-3:#565d70;
}

.stApp{ background:var(--bg); }
html, body, [class*="css"]{
  font-family:'Pretendard','Pretendard Variable',-apple-system,BlinkMacSystemFont,
  'Segoe UI',Roboto,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;
  color:var(--text);
}
.block-container{ max-width:1240px; padding-top:2.4rem; padding-bottom:2rem; }
#MainMenu, footer{ visibility:hidden; height:0; }

/* ── 상단 네비바 ───────────────────────────────────────────── */
.brand{ display:flex; align-items:center; gap:9px; font-weight:800;
  font-size:1.18rem; color:var(--blue); letter-spacing:-.01em; padding-top:6px;}
.brand svg{ width:20px; height:20px; }
.topbar-line{ border-bottom:1px solid var(--border-soft); margin:14px 0 6px; }

/* 상단 네비 링크(st.page_link) */
[data-testid="stPageLink"] a{
  color:var(--text-2) !important; font-size:.92rem !important; font-weight:500 !important;
  justify-content:flex-end; padding:6px 4px !important; border-radius:8px;
}
[data-testid="stPageLink"] a:hover{ color:var(--text) !important; background:transparent !important; }
[data-testid="stPageLink"] a p{ font-size:.92rem !important; }

/* 브랜드 링크(IT'S MINE) — 서비스 이름이라 크게 강조. 클릭하면 홈으로 이동.
   topbar() 의 st.container(key="brandbar") 안에 있는 page_link 만 골라서 키운다. */
.st-key-brandbar [data-testid="stPageLink"] a{
  justify-content:flex-start !important; padding:4px 2px !important; }
.st-key-brandbar [data-testid="stPageLink"] a p{
  font-size:1.7rem !important; font-weight:800 !important;
  color:var(--blue) !important; letter-spacing:-.02em; }
.st-key-brandbar [data-testid="stPageLink"] a:hover p{ color:var(--blue-bright) !important; }

/* 상단바 메뉴 링크 hover 효과 — 메뉴(navbar)에만 적용(요구사항 4).
   밑줄은 빼고, 옅은 파란 배경 알약 + 글자색 강조 + 살짝 떠오르는 반응. */
.st-key-navbar [data-testid="stPageLink"] a{
  text-decoration:none !important;
  transition:background .16s ease, color .16s ease, transform .16s ease; }
.st-key-navbar [data-testid="stPageLink"] a:hover{
  background:rgba(79,124,255,.12) !important; transform:translateY(-1px); }
.st-key-navbar [data-testid="stPageLink"] a:hover p{ color:var(--blue-bright) !important; }

/* ── 히어로 ───────────────────────────────────────────────── */
.hero-pad{ padding-top:60px; }
.badge{
  display:inline-flex; align-items:center; gap:7px;
  background:rgba(79,124,255,.08); border:1px solid rgba(79,124,255,.28);
  color:var(--blue-bright); font-size:.78rem; font-weight:600; letter-spacing:.04em;
  padding:7px 14px; border-radius:999px; margin-bottom:26px;
}
.hero-title{ font-size:3.35rem; line-height:1.18; font-weight:800; letter-spacing:-.02em;
  margin:0 0 22px; color:var(--text); }
.hero-title .accent{ color:var(--blue); }
.hero-sub{ font-size:1.06rem; line-height:1.7; color:var(--text-2); max-width:460px; margin-bottom:34px; }

.upload-card{
  border:1.5px dashed var(--border); border-radius:18px;
  background:linear-gradient(180deg,rgba(18,24,40,.55),rgba(12,16,24,.35));
  padding:42px 28px 30px; text-align:center; margin-top:8px;
}
.upload-ico{ width:54px; height:54px; border-radius:14px; margin:0 auto 18px;
  display:flex; align-items:center; justify-content:center;
  background:rgba(79,124,255,.1); border:1px solid rgba(79,124,255,.22); }
.upload-ico svg{ width:24px; height:24px; stroke:var(--blue-bright); }
.upload-title{ font-size:1.02rem; font-weight:600; color:var(--text); margin-bottom:8px; }
.upload-sub{ font-size:.84rem; color:var(--text-3); margin-bottom:18px; }
.pill-row{ display:flex; gap:9px; justify-content:center; }
.pill{ font-size:.74rem; font-weight:600; color:var(--text-2);
  background:var(--panel-2); border:1px solid var(--border);
  padding:5px 12px; border-radius:8px; letter-spacing:.02em; }

/* ── 통계 ─────────────────────────────────────────────────── */
.stats{ display:grid; grid-template-columns:repeat(4,1fr);
  border-top:1px solid var(--border-soft); margin-top:70px; }
.stat{ padding:34px 16px 30px; text-align:center; }
.stat + .stat{ border-left:1px solid var(--border-soft); }
.stat-num{ font-size:2rem; font-weight:800; color:var(--blue); letter-spacing:-.01em; }
.stat-label{ font-size:.86rem; color:var(--text-3); margin-top:8px; }

/* ── 섹션/핵심 기능 ───────────────────────────────────────── */
.section{ padding:96px 4px 0; }
.eyebrow{ color:var(--blue); font-size:.86rem; font-weight:700; letter-spacing:.06em; margin-bottom:14px; }
.sec-title{ font-size:2.4rem; font-weight:800; letter-spacing:-.02em; color:var(--text); margin:0 0 54px; }
.feat-grid{ display:grid; grid-template-columns:repeat(3,1fr); column-gap:54px; row-gap:0; }
.feat-card{ padding:30px 0 44px; }
.feat-card.row1{ border-bottom:1px solid var(--border-soft); padding-bottom:46px; }
.feat-icon{ width:46px; height:46px; border-radius:12px; margin-bottom:22px;
  display:flex; align-items:center; justify-content:center;
  background:rgba(79,124,255,.09); border:1px solid rgba(79,124,255,.18); }
.feat-icon svg{ width:22px; height:22px; stroke:var(--blue-bright); }
.feat-name{ font-size:1.06rem; font-weight:700; color:var(--text); margin-bottom:11px; }
.feat-desc{ font-size:.92rem; line-height:1.65; color:var(--text-2); max-width:280px; }

/* ── 하단 CTA / 푸터 ─────────────────────────────────────── */
.cta{ text-align:center; padding:120px 4px 70px; border-top:1px solid var(--border-soft); margin-top:96px; }
.cta-title{ font-size:2.3rem; font-weight:800; color:var(--text); letter-spacing:-.02em; margin-bottom:16px; }
.cta-sub{ font-size:1rem; color:var(--text-2); margin-bottom:34px; }
.foot{ text-align:center; padding:30px 4px; border-top:1px solid var(--border-soft);
  color:var(--text-3); font-size:.82rem; }

/* ── 버튼 ─────────────────────────────────────────────────── */
.stButton>button{ border-radius:10px; font-weight:600; font-size:.95rem;
  padding:.62rem 1.3rem; transition:all .18s ease; }
.stButton>button[kind="primary"]{
  background:linear-gradient(135deg,#5b86ff,#3f6dff); color:#fff; border:none;
  box-shadow:0 8px 22px -10px rgba(79,124,255,.75); }
.stButton>button[kind="primary"]:hover{ filter:brightness(1.08); transform:translateY(-1px); }
.stButton>button[kind="secondary"]{ background:transparent; color:var(--text-2); border:1px solid var(--border); }
.stButton>button[kind="secondary"]:hover{ border-color:var(--blue); color:var(--text); }

/* ── 파일 업로더 ──────────────────────────────────────────── */
[data-testid="stFileUploader"]{ background:transparent; }
[data-testid="stFileUploaderDropzone"]{ background:var(--panel); border:1px solid var(--border); border-radius:12px; }
[data-testid="stFileUploaderDropzone"] *{ color:var(--text-2) !important; }

  /* ── 사이드바 ────────────────────────────────────────────────
     자동 페이지 메뉴는 app.py 의 st.navigation(..., position="hidden") 으로 끄고,
     사이드바는 Demo/Real 모드 전환과 기존 run 선택용으로 사용한다. */
  [data-testid="stSidebar"]{
    background:var(--panel);
    border-right:1px solid var(--border);
  }

/* ── 패널/분석 카드 ──────────────────────────────────────── */
.panel{ background:var(--panel); border:1px solid var(--border);
  border-radius:14px; padding:22px 24px; margin-bottom:16px; }
.panel-title{ font-size:1.05rem; font-weight:700; color:var(--text); }
.status-ok{ display:inline-flex; align-items:center; gap:6px;
  background:rgba(46,204,113,.1); color:#3ddc84; border:1px solid rgba(46,204,113,.25);
  font-size:.76rem; font-weight:700; padding:4px 11px; border-radius:999px; }
.status-wait{ display:inline-flex; align-items:center; gap:6px;
  background:rgba(240,160,74,.1); color:#f0a04a; border:1px solid rgba(240,160,74,.25);
  font-size:.76rem; font-weight:700; padding:4px 11px; border-radius:999px; }
.meta-grid{ display:grid; grid-template-columns:repeat(3,1fr); gap:1px;
  background:var(--border-soft); border-radius:10px; overflow:hidden; }
.meta-cell{ background:var(--panel-2); padding:16px 18px; }
.meta-k{ font-size:.78rem; color:var(--text-3); margin-bottom:6px; }
.meta-v{ font-size:1rem; font-weight:700; color:var(--text); }
.req-item{ display:flex; gap:11px; padding:12px 0; border-bottom:1px solid var(--border-soft);
  font-size:.93rem; color:var(--text); line-height:1.55; }
.req-item:last-child{ border-bottom:none; }
.req-num{ color:var(--blue); font-weight:800; flex-shrink:0; }

/* ── 채팅 ─────────────────────────────────────────────────── */
.msg-user{ background:linear-gradient(135deg,#1d2c50,#1a2745); border:1px solid #2a3d68;
  color:#d3e2ff; border-radius:14px 14px 4px 14px; padding:12px 16px; margin:10px 0 10px 18%;
  font-size:.94rem; line-height:1.6; }
.msg-ai{ background:var(--panel-2); border:1px solid var(--border); color:#dde3f2;
  border-radius:14px 14px 14px 4px; padding:12px 16px; margin:10px 0 10px 0;
  font-size:.94rem; line-height:1.65; white-space:pre-wrap; }
.src-tag{ display:inline-block; background:rgba(79,124,255,.1); color:var(--blue-bright);
  border:1px solid rgba(79,124,255,.25); border-radius:7px; font-size:.76rem;
  padding:3px 9px; margin:8px 6px 0 0; }
.role{ font-size:.7rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase;
  opacity:.55; margin-bottom:3px; }
.role.u{ text-align:right; color:var(--blue-bright); }
.role.a{ color:#8a9bff; }

/* ── 탭 (워크스페이스) ───────────────────────────────────── */
.stTabs [data-baseweb="tab-list"]{ gap:4px; border-bottom:1px solid var(--border); }
.stTabs [data-baseweb="tab"]{ color:var(--text-2); font-weight:600; padding:8px 14px; }
.stTabs [aria-selected="true"]{ color:var(--blue-bright) !important; }
.stTabs [data-baseweb="tab-highlight"]{ background:var(--blue) !important; }

/* ── 요금제 ───────────────────────────────────────────────── */
.price-grid{ display:grid; grid-template-columns:repeat(3,1fr); gap:18px; margin-top:14px; }
.price-card{ background:var(--panel); border:1px solid var(--border); border-radius:16px; padding:30px 26px; }
.price-card.popular{ border-color:var(--blue); box-shadow:0 12px 40px -18px rgba(79,124,255,.6); }
.price-name{ font-size:1.05rem; font-weight:700; color:var(--text); margin-bottom:6px; }
.price-tag{ font-size:2.1rem; font-weight:800; color:var(--text); margin:10px 0 4px; }
.price-tag small{ font-size:.9rem; font-weight:500; color:var(--text-3); }
.price-feat{ font-size:.9rem; color:var(--text-2); padding:9px 0; border-bottom:1px solid var(--border-soft); }
.pop-badge{ display:inline-block; background:var(--blue); color:#fff; font-size:.72rem;
  font-weight:700; padding:3px 10px; border-radius:999px; margin-bottom:14px; }

/* ── 정부제안서 검색 (외부 링크 카드 · 4×2 그리드) ──────────── */
.link-grid{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-top:18px; }
.link-card{ display:flex; flex-direction:column; text-decoration:none;
  background:var(--panel); border:1px solid var(--border); border-radius:16px;
  padding:24px 22px; min-height:184px;
  transition:transform .18s ease, border-color .18s ease, box-shadow .18s ease, background .18s ease; }
.link-card:hover{ transform:translateY(-4px); border-color:var(--blue);
  background:var(--panel-2); box-shadow:0 18px 44px -22px rgba(79,124,255,.8); }
.link-card-ico{ width:46px; height:46px; border-radius:12px; margin-bottom:auto;
  display:flex; align-items:center; justify-content:center;
  background:rgba(79,124,255,.1); border:1px solid rgba(79,124,255,.2); }
.link-card-ico svg{ width:22px; height:22px; stroke:var(--blue-bright); }
.link-card-name{ font-size:1.04rem; font-weight:700; color:var(--text); margin-top:18px; }
.link-card-url{ font-size:.78rem; color:var(--blue); font-weight:600;
  margin-top:6px; display:flex; align-items:center; gap:5px; }
.link-card-url .arr{ transition:transform .18s ease; }
.link-card:hover .link-card-url .arr{ transform:translate(3px,-3px); }
@media (max-width:1000px){ .link-grid{ grid-template-columns:repeat(2,1fr); } }
@media (max-width:560px){ .link-grid{ grid-template-columns:1fr; } }

/* ── 서비스 소개 (about) ────────────────────────────────────── */
.about-lead{ font-size:1.12rem; line-height:1.8; color:var(--text-2); max-width:680px; }
.about-grid{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-top:18px; }
.about-card{ background:var(--panel); border:1px solid var(--border);
  border-radius:14px; padding:24px 22px; }
.about-ico{ width:44px; height:44px; border-radius:11px; margin-bottom:16px;
  display:flex; align-items:center; justify-content:center;
  background:rgba(79,124,255,.09); border:1px solid rgba(79,124,255,.18); }
.about-ico svg{ width:21px; height:21px; stroke:var(--blue-bright); }
.about-card-name{ font-size:1.04rem; font-weight:700; color:var(--text); margin-bottom:9px; }
.about-card-desc{ font-size:.92rem; line-height:1.65; color:var(--text-2); }
.about-step{ display:flex; gap:16px; padding:18px 0; border-bottom:1px solid var(--border-soft); }
.about-step:last-child{ border-bottom:none; }
.about-step-num{ flex-shrink:0; width:34px; height:34px; border-radius:10px;
  display:flex; align-items:center; justify-content:center; font-weight:800;
  color:var(--blue); background:rgba(79,124,255,.1); border:1px solid rgba(79,124,255,.2); }
.about-step-t{ font-size:1rem; font-weight:700; color:var(--text); margin-bottom:4px; }
.about-step-d{ font-size:.92rem; line-height:1.6; color:var(--text-2); }
@media (max-width:760px){ .about-grid{ grid-template-columns:1fr; } }

h1,h2,h3,h4{ color:var(--text); }
hr{ border-color:var(--border-soft); }
</style>
"""
