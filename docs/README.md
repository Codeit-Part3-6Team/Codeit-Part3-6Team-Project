# Docs

이 디렉터리는 프로젝트 문서를 역할에 따라 나눠 관리합니다.

처음 보는 팀원에게는 [team/README.md](team/README.md)만 먼저 보여줍니다. 세부 구현 문서는 필요할 때만 `md/`에서 찾아봅니다.

## 문서 분류

```text
docs/
|-- team/  킥오프, 운영 방식, 작업 흐름, 역할별 첫 작업
|-- md/    RAG, 데이터, 실험, 인프라 같은 세부 참고 문서
|-- html/  발표와 설명에 쓰기 좋은 시각 자료
`-- llm/   LLM에게 작업을 맡길 때 읽히는 컨텍스트
```

## 먼저 볼 문서

| 목적 | 문서 |
| --- | --- |
| 팀원 온보딩 입구 | [team/README.md](team/README.md) |
| 프로젝트와 역할 설명 | [team/kickoff.md](team/kickoff.md) |
| PR, Issue, Daily Report 운영 | [team/operations.md](team/operations.md) |
| Data 준비부터 발표까지 작업 흐름 | [team/workflow.md](team/workflow.md) |
| 역할별 초기 작업 | [team/roles.md](team/roles.md) |
| 첫 주 작업 카드 | [team/first-week.md](team/first-week.md) |

## 세부 참고 문서

| 필요 상황 | 문서 |
| --- | --- |
| RAG 입출력 계약 확인 | [md/rag/RAG_PIPELINE_SPEC.md](md/rag/RAG_PIPELINE_SPEC.md) |
| 데이터 제공 형식 확인 | [md/data/DATA_CONTRACT.md](md/data/DATA_CONTRACT.md) |
| 실험 실행 방법 확인 | [md/experiments/EXPERIMENT_GUIDE.md](md/experiments/EXPERIMENT_GUIDE.md) |
| 노트북 사용 방법 확인 | [md/experiments/NOTEBOOK_USAGE_CHECKLIST.md](md/experiments/NOTEBOOK_USAGE_CHECKLIST.md) |
| 전체 파이프라인 구조 확인 | [md/overview/PIPELINE_OVERVIEW.md](md/overview/PIPELINE_OVERVIEW.md) |
| 모듈 관계 확인 | [md/overview/MODULE_ARCHITECTURE.md](md/overview/MODULE_ARCHITECTURE.md) |

## 설명용 HTML

HTML은 모든 Markdown의 변환본이 아닙니다. 발표나 설명에 직접 도움이 되는 시각 자료만 남깁니다.

- [html/overview/pipeline_explainer.html](html/overview/pipeline_explainer.html): 비전공자에게 설명하기 쉬운 파이프라인 소개
- [html/overview/module_architecture.html](html/overview/module_architecture.html): 모듈 관계와 RAG 구조 다이어그램
- [html/kickoff/kickoff.html](html/kickoff/kickoff.html): 킥오프 공유용 HTML 문서

## 관리 원칙

- 팀원에게는 `docs/team/`만 먼저 안내합니다.
- 세부 구현 문서는 필요한 역할만 찾아보게 합니다.
- 중복 설명이 생기면 `docs/team/`에는 요약만 남기고 자세한 내용은 `docs/md/`로 보냅니다.
- 코드 구조, 실행 방식, 산출물 위치가 바뀌면 `docs/llm/` 문서도 함께 확인합니다.
