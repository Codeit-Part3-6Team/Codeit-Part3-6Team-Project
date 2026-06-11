# LLM 작업 요청 프롬프트

이 문서는 LLM에게 작업을 맡길 때 복사해서 쓸 수 있는 요청 예시를 모읍니다.

먼저 루트 `AGENTS.md`를 읽고, 팀 공유 문서는 `docs/team/`, 세부 참고 문서는 `docs/md/`, LLM 컨텍스트는 `docs/llm/`에서 확인하게 합니다.

## 기본 요청

```text
AGENTS.md를 먼저 읽고 진행해줘.
관련 README와 docs/llm 문서를 확인한 뒤 작업해줘.
작업 후에는 변경한 파일, 실행한 테스트, 남은 리스크를 짧게 정리해줘.
```

## RAG 기능 구현 요청

```text
AGENTS.md, docs/llm/ARCHITECTURE_MAP.md, docs/md/rag/RAG_PIPELINE_SPEC.md를 읽고 진행해줘.
RAG 파이프라인에 {기능명}을 추가해줘.
가능하면 config로 켜고 끌 수 있게 만들고, scripts 진입점은 얇게 유지해줘.
관련 테스트와 README도 함께 갱신해줘.
```

## Config 옵션 추가 요청

```text
configs/README.md와 docs/md/rag/RAG_PIPELINE_SPEC.md를 먼저 읽어줘.
{옵션명}을 config에서 조정할 수 있게 추가해줘.
validation, 예시 config, 테스트, 문서까지 같이 맞춰줘.
```

## GitHub 운영 문서 요청

```text
AGENTS.md와 docs/team/operations.md를 읽고 진행해줘.
{운영 주제}에 필요한 Issue, PR, Kanban, Daily Report 규칙을 정리해줘.
팀원이 바로 복사해서 쓸 수 있는 형태로 작성해줘.
```

## 첫 주 태스크 정리 요청

```text
docs/team/first-week.md와 docs/team/roles.md를 읽고 진행해줘.
{역할 또는 목표}에 맞는 첫 주 작업 카드를 보강해줘.
각 카드에는 목적, 담당 후보, 완료 기준, 확인 방법을 넣어줘.
```

## 역할별 설명 문서 요청

```text
docs/team/roles.md를 읽고 진행해줘.
{역할명} 팀원이 처음 봐야 할 집중 포인트를 더 이해하기 쉽게 보강해줘.
긴 링크 목록보다 첫 작업 순서, 판단 기준, 산출물 중심으로 정리해줘.
```

## 노트북 사용성 점검 요청

```text
notebooks/README.md와 docs/md/experiments/EXPERIMENT_GUIDE.md를 읽고 진행해줘.
처음 보는 팀원이 노트북에서 어떤 config를 바꿔야 하는지 이해할 수 있는지 점검해줘.
설명 셀, metric 확인, 그래프 확인, 산출물 경로 설명이 부족하면 보강해줘.
```

## 문서 정리 요청

```text
docs/README.md와 docs/team/README.md를 읽고 진행해줘.
중복되는 문서가 있으면 하나로 합치거나 참고 문서로 내려줘.
팀원이 처음 볼 문서와 세부 참고 문서가 섞이지 않게 정리해줘.
```
