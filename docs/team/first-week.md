# 첫 주 Kanban 태스크 초안

이 문서는 프로젝트 시작 직후 GitHub Projects나 Notion 보드에 옮길 수 있는 첫 주 작업 카드 초안입니다.

## 첫 주 목표

- 팀원이 같은 실행 방법으로 파이프라인을 돌릴 수 있습니다.
- 실제 RFP 데이터가 들어오기 전에도 RAG 흐름과 산출물을 이해합니다.
- 역할별 첫 책임 범위를 작게 나누고, 막힘을 빠르게 공유합니다.
- 발표/문서/실험 기록이 동시에 흩어지지 않게 합니다.

첫 주 기준은 2026-06-18 ~ 2026-06-19입니다. 2026-06-17은 프로젝트 설명을 듣고 운영 기준을 맞추는 날로 봅니다.

## 보드 초기 세팅

```text
Backlog
Ready
In Progress
Review
Done
```

초기에는 아래 카드들을 `Backlog`에 두고, 킥오프 후 담당자와 완료 기준이 분명해진 카드만 `Ready`로 옮깁니다.

## 공통 온보딩

| 카드 | 담당 후보 | 완료 기준 |
| --- | --- | --- |
| 개발 환경 세팅 확인 | 전체 | `python -m pytest` 또는 지정된 동작 확인 결과를 공유합니다. |
| README와 킥오프 문서 읽기 | 전체 | 질문 또는 이해 안 된 부분을 Issue 댓글로 남깁니다. |
| Daily Report 첫 작성 | 전체 | 각자 오늘 할 일과 막힌 점을 1회 작성합니다. |
| GitHub Issue/PR 흐름 연습 | 전체 | 작은 문서 수정 PR을 하나 열고 리뷰 흐름을 확인합니다. |

## PM

| 카드 | 완료 기준 |
| --- | --- |
| GitHub 보드 생성 | 컬럼과 라벨이 준비되어 있습니다. |
| 첫 주 일정 공유 | 회의 시간, 마감 기준, Daily Report 작성 시간이 정해져 있습니다. |
| 역할별 담당 범위 확정 | PM, Data Engineer, Experiment Lead, Application Engineer, Presentation Lead의 첫 책임이 기록되어 있습니다. |
| 의사결정 로그 시작 | 주요 결정과 이유를 문서나 Issue에 남깁니다. |

## Data Engineer

| 카드 | 완료 기준 |
| --- | --- |
| 실제 데이터 후보 조사 | RFP/PDF/HWP/HWPX 후보와 접근 방법을 정리합니다. |
| 데이터 반입 규칙 확인 | 원본 데이터 저장 위치와 Git 제외 규칙을 확인합니다. |
| 평가 질문 CSV 초안 작성 | `question`, `expected_answer`, `expected_chunk_ids` 형식을 이해하고 예시를 만듭니다. |
| 문서 로더 검증 계획 작성 | 실제 PDF/HWP/HWPX가 들어오면 확인할 항목을 정리합니다. |

## Experiment Lead

| 카드 | 완료 기준 |
| --- | --- |
| RAG config 기반 pipeline 실행 | ingest, retrieve, chat, evaluate 명령 결과를 공유합니다. |
| retriever/answerer 설정 확인 | 검색 방식과 답변 방식이 config에서 어디에 있는지 설명합니다. |
| config 변경 실험 1회 수행 | `top_k`, `chunk_size`, `retriever`, `answerer` 중 하나를 바꿔 결과를 비교합니다. |
| metric 해석 메모 작성 | `retrieval_hit_rate`, `citation_correct_rate`, `not_found_rate`의 의미를 설명합니다. |

## Application Engineer

| 카드 | 완료 기준 |
| --- | --- |
| RAG 입출력 계약 확인 | `/rag/chat` 같은 API를 나중에 붙일 때 필요한 request/response 형태를 정리합니다. |
| 산출물 파일 구조 확인 | `answers.jsonl`, `retrieval_results.jsonl`, `metrics.json`의 용도를 설명합니다. |
| 데모 범위 후보 정리 | FastAPI, Streamlit, Gradio, notebook 중 가능한 선택지를 비교합니다. |
| API 보류 결정 기록 | 지금은 API를 보류하고 파이프라인/운영 준비를 우선한다는 결정을 남깁니다. |

## Presentation Lead

| 카드 | 완료 기준 |
| --- | --- |
| 킥오프 설명 흐름 점검 | 문제, RAG 구조, 실험 산출물, 역할 분배 순서로 설명할 수 있습니다. |
| 킥오프 HTML 확인 | 화면에서 읽기 어려운 부분이나 빠진 내용을 기록합니다. |
| 발표용 용어 목록 작성 | RAG, chunk, embedding, retrieval, citation을 쉬운 말로 정리합니다. |
| 진행 상황 공유 템플릿 작성 | 주간 공유에 쓸 요약 형식을 만듭니다. |

## Review로 넘기는 기준

- 관련 문서 또는 Issue에 결과가 남아 있습니다.
- 실행한 명령과 결과가 있습니다.
- 막힌 점이 있으면 다음 액션 또는 필요한 결정이 적혀 있습니다.
- 다른 역할이 이어받아야 할 내용이 분명합니다.

## 첫 주에 무리해서 하지 않을 것

- 실제 앱/API 완성
- 대형 LLM 모델 실행을 전제로 한 품질 평가
- 실제 RFP 데이터가 없는 상태에서 세밀한 parser 튜닝
- 모든 문서를 발표자료 수준으로 꾸미기
