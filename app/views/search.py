"""
정부제안서 검색 (외부 사이트 모음)
==================================
나라장터 등 공공 입찰공고·제안요청서(RFP)가 올라오는 외부 사이트로 이동하는 링크 모음.
4열 × 2행 = 8칸 그리드. 각 칸에 아이콘 + 사이트 이름 + 주소가 있고,
칸을 누르면 새 탭에서 해당 사이트가 열립니다.

※ 내부 페이지 이동이 아니라 외부 사이트라서, HTML <a target="_blank"> 로 처리합니다.
※ 사이트/문구/아이콘은 아래 SITES 리스트만 고치면 됩니다.
"""

import streamlit as st
from utils.components import topbar, footer, _svg

topbar()

st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
st.markdown('<div class="eyebrow">SEARCH</div>'
            '<h2 class="sec-title" style="margin-bottom:8px">정부제안서 검색</h2>'
            '<div style="color:var(--text-2);margin-bottom:6px">'
            '공공 입찰공고와 제안요청서(RFP)가 올라오는 주요 사이트로 바로 이동하세요. '
            '카드를 누르면 새 탭에서 열립니다.</div>', unsafe_allow_html=True)

# ── 카드용 아이콘 (사이트 성격에 맞춰 코드로 그림. 별도 이미지 파일 불필요) ──
IC_TENDER = _svg('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
                 '<polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/>'
                 '<line x1="8" y1="17" x2="13" y2="17"/>')
IC_DEFENSE = _svg('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>')
IC_AGENCY  = _svg('<path d="M3 21h18"/><path d="M5 21V8l7-5 7 5v13"/>'
                  '<path d="M9 21v-6h6v6"/>')
IC_SHOP    = _svg('<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/>'
                  '<path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>')
IC_BIZ     = _svg('<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>'
                  '<circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/>'
                  '<path d="M16 3.13a4 4 0 0 1 0 7.75"/>')
IC_RND     = _svg('<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/>'
                  '<line x1="6" y1="20" x2="6" y2="14"/>')
IC_PORTAL  = _svg('<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/>'
                  '<path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>')
IC_DATA    = _svg('<ellipse cx="12" cy="5" rx="9" ry="3"/>'
                  '<path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>'
                  '<path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/>')

# (이름, URL, 한 줄 설명(툴팁), 아이콘) — 여기만 고치면 카드가 바뀝니다.
SITES = [
    ("나라장터 (G2B)",       "https://www.g2b.go.kr",     "모든 공공기관 입찰공고가 모이는 국가종합전자조달 단일창구", IC_TENDER),
    ("국방전자조달 (D2B)",   "https://www.d2b.go.kr",     "방위사업청이 운영하는 군수품·국방 분야 전자조달",          IC_DEFENSE),
    ("조달청",               "https://www.pps.go.kr",     "나라장터 운영 주관기관. 조달 정책·공지·교육",              IC_AGENCY),
    ("나라장터 종합쇼핑몰",  "https://shop.g2b.go.kr",    "다수공급자계약(MAS) 기반 카탈로그형 공공조달 쇼핑몰",      IC_SHOP),
    ("기업마당",             "https://www.bizinfo.go.kr", "중앙부처·지자체 지원사업 공고를 한곳에서 검색",            IC_BIZ),
    ("IRIS 범부처통합연구지원", "https://www.iris.go.kr",  "정부 R&D 과제 공고 확인 및 연구과제 신청",                 IC_RND),
    ("정부24",               "https://www.gov.kr",        "정부 민원·서비스 통합 포털. 기관별 공고·고시 확인",        IC_PORTAL),
    ("공공데이터포털",       "https://www.data.go.kr",    "공공기관 데이터·입찰공고를 API로 받아볼 수 있는 통합 창구", IC_DATA),
]

cards = ""
for name, url, desc, icon in SITES:
    short_url = url.replace("https://", "").replace("http://", "")
    cards += (
        f'<a class="link-card" href="{url}" target="_blank" rel="noopener noreferrer" title="{desc}">'
        f'<div class="link-card-ico">{icon}</div>'
        f'<div class="link-card-name">{name}</div>'
        f'<div class="link-card-url">{short_url} <span class="arr">↗</span></div>'
        f'</a>'
    )
st.markdown(f'<div class="link-grid">{cards}</div>', unsafe_allow_html=True)

st.markdown('<div style="height:30px"></div>', unsafe_allow_html=True)
st.caption("※ 외부 사이트로 이동하는 링크입니다. 사이트 사정에 따라 주소가 바뀔 수 있어요.")
footer()


