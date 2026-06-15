# 팀원이 처음 볼 문서

이 디렉터리는 킥오프와 첫 작업 안내에 필요한 핵심 문서만 모아둔 곳입니다.

세부 구현 문서는 `docs/md/`에 남겨둡니다. 처음부터 전부 읽을 필요는 없습니다.

## 진행하면서 열어볼 문서

킥오프에서는 먼저 `kickoff.md`로 전체 그림을 공유합니다. 그 다음에는 아래 순서대로 문서를 하나씩 열어, 일정, 운영 방식, 작업 흐름, 역할, 첫 주 카드를 차례로 합의합니다.

| 순서 | 문서 | 목적 |
| --- | --- | --- |
| 1 | [kickoff.md](kickoff.md) | 프로젝트 목표, 운영 방식, 역할, 리스크 합의 |
| 2 | [timeline.md](timeline.md) | 공식 프로젝트 기간과 평일 기준 작업 흐름 |
| 3 | [operations.md](operations.md) | Issue, PR, Daily Report를 어떻게 쓸지 |
| 4 | [workflow.md](workflow.md) | Data 준비부터 발표까지 어떻게 이어지는지 |
| 5 | [roles.md](roles.md) | 내 역할이 처음 무엇을 하면 되는지 |
| 6 | [first-week.md](first-week.md) | 첫 주에 어떤 작업부터 할지 |

## 소개 흐름

| 단계 | 설명할 질문 | 열어볼 문서 |
| --- | --- | --- |
| 1 | 우리는 무엇을 만들고 무엇을 남길 것인가? | [kickoff.md](kickoff.md) |
| 2 | 발표일까지 어떤 순서로 움직일 것인가? | [timeline.md](timeline.md) |
| 3 | Issue, PR, Daily Report는 어떻게 쓸 것인가? | [operations.md](operations.md) |
| 4 | 데이터, 실험, 데모, 발표는 어떻게 이어지는가? | [workflow.md](workflow.md) |
| 5 | 각 역할은 무엇을 맡고 어디까지 책임지는가? | [roles.md](roles.md) |
| 6 | 첫 주에 어떤 카드를 Backlog에서 Ready로 옮길 것인가? | [first-week.md](first-week.md) |

## 큰 흐름

```mermaid
flowchart LR
  A["문서 준비"] --> B["검색/답변 실험"]
  B --> C["결과 확인"]
  C --> D["데모 형태 정리"]
  D --> E["시연/발표"]
```

## 역할별 핵심만 보기

| 역할 | 핵심 책임 | 먼저 볼 곳 |
| --- | --- | --- |
| PM | 일정, 보드, 역할 배정, 막힘 관리 | [roles.md](roles.md)의 PM |
| Data Engineer | 문서 확보, 로딩 확인, 평가 질문 준비 | [roles.md](roles.md)의 Data Engineer |
| Experiment Lead | retriever, answerer, LangChain config, evaluation 관리 | [roles.md](roles.md)의 Experiment Lead |
| Application Engineer | 데모/API 후보, 입출력 형태, citation 표시 방식 | [roles.md](roles.md)의 Application Engineer |
| Presentation Lead | 문제 설명, 쉬운 용어, 발표 흐름과 시각 자료 | [roles.md](roles.md)의 Presentation Lead |

## 세부 문서는 언제 보는가

| 필요 상황 | 참고 문서 |
| --- | --- |
| RAG 입력/출력 계약이 필요할 때 | [../md/rag/RAG_PIPELINE_SPEC.md](../md/rag/RAG_PIPELINE_SPEC.md) |
| 데이터 형식을 맞춰야 할 때 | [../md/data/DATA_CONTRACT.md](../md/data/DATA_CONTRACT.md) |
| 실험 실행 방법이 필요할 때 | [../md/experiments/EXPERIMENT_GUIDE.md](../md/experiments/EXPERIMENT_GUIDE.md) |
| 평가 질문과 정답 데이터를 만들어야 할 때 | [golden_dataset_guide.md](golden_dataset_guide.md) |
| 노트북 설명을 보강할 때 | [../md/experiments/NOTEBOOK_USAGE_CHECKLIST.md](../md/experiments/NOTEBOOK_USAGE_CHECKLIST.md) |
| 파이프라인 산출물을 따로 점검할 때 | [rehearsal.md](rehearsal.md) |
| LLM에게 작업을 맡길 때 | [../llm/README.md](../llm/README.md) |

## 발표까지 남기면 되는 것

- 사용한 문서와 질문 예시
- 검색된 근거 chunk
- 답변과 citation
- metric 또는 실패 사례
- 한계와 개선 가능성
