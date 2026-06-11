# GitHub Project 카드 Seed

이 문서는 GitHub Projects나 Issue로 바로 옮길 수 있는 첫 주 카드 목록입니다.

`FIRST_WEEK_KANBAN.md`가 설명용이라면, 이 문서는 실제 보드 입력용입니다.

## 컬럼

```text
Backlog
Ready
In Progress
Review
Done
```

초기에는 모든 카드를 `Ready`에 넣고, 담당자가 정해진 뒤 `In Progress`로 옮깁니다.

## 카드 목록

| Title | Labels | Owner 후보 | 초기 컬럼 | 완료 기준 |
| --- | --- | --- | --- | --- |
| 개발 환경 세팅 확인 | `task` | 전체 | Ready | 각자 테스트 또는 smoke 실행 결과를 댓글로 남깁니다. |
| README와 킥오프 문서 읽기 | `docs` | 전체 | Ready | 질문 또는 이해 안 된 부분을 Issue 댓글로 남깁니다. |
| Daily Report 첫 작성 | `daily` | 전체 | Ready | `.github/ISSUE_TEMPLATE/daily_report.md` 형식으로 1회 작성합니다. |
| GitHub Issue/PR 흐름 연습 | `task` | 전체 | Ready | 작은 문서 수정 PR을 열고 리뷰 흐름을 확인합니다. |
| GitHub 보드 생성 | `task` | PM | Ready | 컬럼, 라벨, 담당자 필드가 준비되어 있습니다. |
| 첫 주 일정 공유 | `task` | PM | Ready | 회의 시간, 마감 기준, Daily Report 작성 시간이 정해져 있습니다. |
| 역할별 담당 범위 확정 | `task` | PM | Ready | 역할별 첫 책임과 담당자가 문서나 Issue에 기록되어 있습니다. |
| 의사결정 로그 시작 | `docs` | PM | Ready | 주요 결정과 이유를 기록할 위치가 정해져 있습니다. |
| 실제 데이터 후보 조사 | `data` | Data Engineer | Ready | RFP/PDF/HWP/HWPX 후보와 접근 방법을 정리합니다. |
| 데이터 반입 규칙 확인 | `data` | Data Engineer | Ready | 원본 데이터 저장 위치와 Git 제외 규칙을 확인합니다. |
| 평가 질문 CSV 초안 작성 | `data` | Data Engineer | Ready | `question`, `expected_answer`, `expected_chunk_ids` 예시를 만듭니다. |
| 문서 로더 검증 계획 작성 | `data` | Data Engineer | Ready | 실제 문서가 들어오면 확인할 loader 체크 항목을 정리합니다. |
| RAG smoke pipeline 실행 | `rag`, `experiment` | Experiment Lead | Ready | ingest, retrieve, chat, evaluate 실행 결과를 공유합니다. |
| retriever 비교 결과 확인 | `rag`, `experiment` | Experiment Lead | Ready | keyword, semantic, hybrid 결과 차이를 설명합니다. |
| config 변경 실험 1회 수행 | `experiment` | Experiment Lead | Ready | `top_k`, `chunk.size`, `retriever.method` 중 하나를 바꿔 비교합니다. |
| metric 해석 메모 작성 | `experiment`, `docs` | Experiment Lead | Ready | 주요 RAG metric의 의미와 확인 위치를 설명합니다. |
| RAG 입출력 계약 확인 | `app`, `rag` | Application Engineer | Ready | 나중에 API를 붙일 request/response 후보를 정리합니다. |
| 산출물 파일 구조 확인 | `app`, `rag` | Application Engineer | Ready | `answers.jsonl`, `retrieval_results.jsonl`, `metrics.json` 용도를 설명합니다. |
| 데모 범위 후보 정리 | `app` | Application Engineer | Ready | FastAPI, Streamlit, Gradio, notebook 선택지를 비교합니다. |
| API 보류 결정 기록 | `app`, `docs` | Application Engineer | Ready | 지금은 API를 보류한다는 결정과 이유를 남깁니다. |
| 비전공자 설명 흐름 점검 | `docs` | Presentation Lead | Ready | 문제, RAG 구조, 산출물, 역할 순서로 설명할 수 있습니다. |
| 킥오프 HTML 확인 | `docs` | Presentation Lead | Ready | 읽기 어려운 부분이나 빠진 내용을 기록합니다. |
| 발표용 용어 목록 작성 | `docs` | Presentation Lead | Ready | RAG, chunk, embedding, retrieval, citation을 쉬운 말로 정리합니다. |
| 진행 상황 공유 템플릿 작성 | `docs` | Presentation Lead | Ready | 주간 공유에 쓸 요약 형식을 만듭니다. |

## Issue 본문 템플릿

카드를 Issue로 만들 때는 아래 구조를 사용합니다.

```text
## 목적

-

## 작업 내용

- [ ]

## 완료 기준

- [ ]

## 확인 방법

-

## 참고 문서

-
```

## PM 확인 순서

1. 같은 의미의 카드가 중복되지 않았는지 봅니다.
2. 카드 하나가 하루 안에 끝낼 수 있는 크기인지 봅니다.
3. 완료 기준이 확인 가능한 문장인지 봅니다.
4. 담당자가 없으면 PM이 임시 담당자로 두고 킥오프에서 배정합니다.
5. 막힌 카드는 `blocked` 라벨을 붙이고 필요한 결정을 따로 적습니다.
