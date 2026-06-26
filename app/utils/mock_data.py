"""
Mock 백엔드 (가짜 데이터)
=========================
실제 RAG 모델이 완성되면 이 파일의 함수만 교체하세요.
입력/출력 형식만 맞추면 UI 코드는 수정할 필요가 없습니다.

  mock_analyze(filename)  ->  {"meta": dict, "summary": str, "requirements": [str]}
  mock_chat(question)     ->  (answer: str, sources: [(page, section)])
"""

import time

MOCK_META = {
    "사업명": "차세대 전자조달 시스템 구축",
    "발주기관": "조달청",
    "사업예산": "12억 8천만원",
    "사업기간": "12개월",
    "제출마감": "2026-07-15 18:00",
    "문서분량": "247 페이지",
}

MOCK_SUMMARY = (
    "노후화된 전자조달 시스템을 클라우드 네이티브 환경으로 전면 재구축하는 사업입니다. "
    "대용량 동시접속 처리, 공공기관 보안 인증(CC인증 EAL4), 레거시 데이터 무중단 "
    "마이그레이션이 핵심 요구사항으로 도출되었습니다."
)

MOCK_REQS = [
    "클라우드 네이티브 아키텍처 기반 시스템 설계 (필수)",
    "동시 접속자 10,000명 이상 처리 성능 보장",
    "CC인증 EAL4 등급 보안 요구사항 충족",
    "기존 레거시 데이터 무중단 마이그레이션",
    "장애 복구 시간(RTO) 4시간 이내 보장",
]


def mock_analyze(filename: str) -> dict:
    """문서 분석 Mock. 실제로는 RAG 인덱싱 + 요약 결과를 반환."""
    time.sleep(1.4)  # 분석 시간 시뮬레이션
    return {"meta": MOCK_META, "summary": MOCK_SUMMARY, "requirements": MOCK_REQS}


def mock_chat(question: str):
    """질문에 대한 Mock 답변 + 출처. 실제로는 RAG 검색 결과를 반환."""
    if "마감" in question or "언제" in question:
        ans = ("제안서 제출 마감은 **2026년 7월 15일 18:00**까지입니다. "
               "마감 직전에는 업로드가 집중되니 여유 있게 제출하시길 권장합니다.")
        srcs = [("p.12", "2.3 제출 안내"), ("p.13", "2.4 일정표")]
    elif "예산" in question or "금액" in question:
        ans = ("총 사업 예산은 **12억 8천만원**(부가세 포함)이며, 단계별 분할 지급입니다. "
               "착수 30% · 중간 40% · 완료 30% 구조로 명시되어 있습니다.")
        srcs = [("p.8", "1.4 사업 예산"), ("p.31", "5.2 대가 지급")]
    elif "보안" in question:
        ans = ("핵심 보안 요구사항은 **CC인증 EAL4 등급** 충족과 개인정보 암호화 저장입니다. "
               "망분리 환경 구성과 접근통제(MFA) 적용도 필수로 요구됩니다.")
        srcs = [("p.42", "3.2 보안 요구사항"), ("p.44", "3.3 인증 기준")]
    else:
        ans = ("문서를 기반으로 답변드리면, 해당 내용은 제안요청서 본문의 관련 조항을 "
               "교차 확인한 결과입니다. 예산·일정·보안 등 구체적 항목을 질문하시면 "
               "출처와 함께 정확히 안내해 드릴게요.")
        srcs = [("p.5", "1.1 사업 개요"), ("p.19", "3.1 요구사항 총괄")]
    return ans, srcs


def stream_words(text: str, delay: float = 0.03):
    """답변을 단어 단위로 흘려보내는 제너레이터 (타이핑 효과)."""
    acc = ""
    for word in text.split(" "):
        acc += word + " "
        yield acc
        time.sleep(delay)
