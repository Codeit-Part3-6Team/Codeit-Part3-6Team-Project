# Task Prompts for LLM Collaboration

이 문서는 팀원이 LLM에게 작업을 맡길 때 사용할 수 있는 요청 예시를 모읍니다.

## 기본 프롬프트

```text
먼저 AGENTS.md를 읽고, 관련 README와 docs/llm 문서를 확인한 뒤 작업해줘.
작업 후에는 변경한 파일, 실행한 테스트, 남은 리스크를 짧게 정리해줘.
```

## RAG 기능 구현 요청

```text
AGENTS.md와 docs/llm/ARCHITECTURE_MAP.md를 읽고 진행해줘.
RAG 파이프라인에서 {기능명}을 추가하고 싶어.
가능하면 config로 켜고 끌 수 있게 만들고, scripts는 얇게 유지해줘.
관련 테스트와 README도 갱신해줘.
```

## Config 옵션 추가 요청

```text
configs/README.md와 docs/md/rag/RAG_PIPELINE_SPEC.md를 먼저 읽어줘.
{옵션명}을 config에서 조정할 수 있게 추가해줘.
validation, 예시 config, 테스트, 문서까지 같이 맞춰줘.
```

## 버그 수정 요청

```text
이 에러를 재현하는 테스트를 먼저 확인하거나 추가해줘.
원인을 찾은 뒤 최소 범위로 수정하고, 관련 README나 문서에 영향이 있으면 같이 갱신해줘.

에러:
{에러 로그}
```

## 코드 리뷰 요청

```text
코드 리뷰 관점으로 봐줘.
버그, 회귀 위험, 테스트 누락, 문서 누락을 우선순위대로 알려줘.
문제가 없으면 남은 리스크만 짧게 말해줘.
```

## 문서화 요청

```text
처음 보는 팀원이 이해할 수 있게 문서를 보강해줘.
가능하면 Mermaid mindmap과 텍스트 기반 디렉터리 구조를 함께 넣어줘.
문서 변경 후 docs 구조 테스트를 돌려줘.
```

## 실험 노트북 요청

```text
notebooks/README.md와 docs/md/experiments/COLAB_GUIDE.md를 읽고,
{실험 목적}을 진행하기 쉬운 노트북 셀을 추가해줘.
각 셀에는 처음 보는 사람이 이해할 수 있는 짧은 설명과 주석을 넣어줘.
```

## GitHub 운영 문서 요청

```text
AGENTS.md와 docs/md/workflow/GITHUB_OPERATIONS.md를 읽고 진행해줘.
{운영 주제}에 필요한 Issue, PR, Kanban, Daily Report 규칙을 정리해줘.
이미 있는 템플릿과 충돌하지 않게 하고, 팀원이 바로 복사해서 쓸 수 있는 형태로 작성해줘.
문서를 수정했다면 관련 README 링크도 확인해줘.
```

## 첫 주 태스크 정리 요청

```text
docs/md/workflow/FIRST_WEEK_KANBAN.md와 docs/md/workflow/ROLE_GUIDE.md를 읽고,
{역할 또는 목표}에 맞는 첫 주 작업 카드를 보강해줘.
각 카드는 목적, 담당 후보, 완료 기준, 확인 방법이 드러나게 작성해줘.
기능 구현으로 바로 넘어가지 말고, 프로젝트 시작 전에 필요한 운영 준비를 우선해줘.
```

## GitHub Project 카드 Seed 요청

```text
docs/md/workflow/GITHUB_PROJECT_CARD_SEED.md를 읽고,
GitHub Project에 옮길 카드 목록을 {상황}에 맞게 정리해줘.
각 카드에는 Title, Labels, Owner 후보, 초기 컬럼, 완료 기준이 있어야 해.
너무 큰 카드는 하루 안에 끝낼 수 있는 작은 카드로 쪼개줘.
```

## 노트북 사용성 점검 요청

```text
notebooks/README.md와 docs/md/experiments/EXPERIMENT_GUIDE.md를 읽고,
처음 보는 팀원이 노트북에서 어떤 config를 바꿔야 하는지 이해할 수 있는지 점검해줘.
부족한 셀 설명, metric 확인, 그래프 확인, 산출물 경로 설명을 보강해줘.
테스트가 있으면 tests/test_notebooks.py를 실행해줘.
```

## 좋은 작업 결과 형식

LLM에게 마지막 정리를 요청할 때는 아래 형식을 권장합니다.

```text
변경한 것:
- ...

확인한 것:
- ...

남은 것:
- ...
```
