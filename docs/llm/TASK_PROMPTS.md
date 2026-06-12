# LLM 작업 요청 프롬프트

이 문서는 Codex, ChatGPT, Claude 같은 LLM에게 작업을 맡길 때 복사해서 쓸 수 있는 요청 예시를 모읍니다.

핵심은 LLM이 이 저장소를 **직접 만든 RAG 라이브러리**가 아니라 **LangChain 기반 RAG 실험/운영 harness**로 이해하게 만드는 것입니다. 계산 엔진은 LangChain을 써도 되지만, config, scripts, experiments, evaluation artifact 계약은 이 프로젝트가 책임집니다.

## 공통 기본 프롬프트

모든 요청 앞에 아래 문장을 붙이면 작업 방향이 흔들릴 가능성이 줄어듭니다.

```text
AGENTS.md를 먼저 읽고 진행해줘.
이 프로젝트는 LangChain 기반 RAG 실험/운영 harness야.
LangChain 객체를 pipeline 밖으로 그대로 노출하지 말고, retrieval/answer/evaluation 결과는 프로젝트 표준 artifact로 변환해줘.
가능하면 config로 조정할 수 있게 만들고, scripts는 얇은 진입점으로 유지해줘.
작업 후에는 변경한 파일, 실행한 테스트, 남은 리스크를 짧게 정리해줘.
```

## RAG 기능 구현 요청

```text
AGENTS.md, docs/llm/ARCHITECTURE_MAP.md, docs/md/rag/RAG_PIPELINE_SPEC.md를 읽고 진행해줘.
RAG 파이프라인에 {기능명}을 추가해줘.
LangChain을 쓰는 경우에도 Document, retriever result, chain output은 엔진 내부에서 프로젝트 표준 dict로 변환해줘.
retrieval_results.jsonl, answers.jsonl, metrics.json, 실패 CSV 계약이 깨지지 않게 관련 테스트를 보강해줘.
README나 config 예시도 함께 갱신해줘.
```

## LangChain Provider 추가/수정 요청

```text
AGENTS.md와 docs/md/rag/RAG_PIPELINE_SPEC.md를 읽고 진행해줘.
LangChain 기반 {embedding/vector_store/answerer/retriever} provider인 {provider_name}을 추가 또는 수정해줘.
provider 선택은 config에서 가능해야 하고, provider 결과는 pipeline 밖으로 LangChain 객체가 아니라 프로젝트 표준 dict로 넘어가야 해.
mock provider 테스트를 추가해서 실제 외부 API 없이도 artifact 계약을 검증해줘.
```

## Config 옵션 추가 요청

```text
configs/README.md와 docs/md/rag/RAG_PIPELINE_SPEC.md를 먼저 읽어줘.
{옵션명}을 config에서 조정할 수 있게 추가해줘.
validation, 예시 config, 테스트, 문서까지 같이 맞춰줘.
기본 config는 RAG 기준으로 유지하고, 분류/HuggingFace fine-tuning config는 참고 예제로만 다뤄줘.
```

## 테스트 엄밀화 요청

```text
현재 테스트가 단순 smoke 수준인지 확인해줘.
{대상 기능}에 대해 정상 케이스뿐 아니라 config 오류, 빈 입력, artifact 누락, provider 결과 변환, 실패 artifact 생성까지 테스트할 수 있는지 점검해줘.
필요한 테스트를 추가하고, 마지막에 어떤 리스크가 테스트로 고정됐는지 정리해줘.
```

## 실제 문서 포맷 E2E 검증 요청

```text
AGENTS.md, docs/llm/PROJECT_CONTEXT.md, docs/md/overview/RAG_QUALITY_CHECKLIST.md를 읽고 진행해줘.
DOCX/HWPX/PDF 같은 실제 문서 포맷이 RAG pipeline에서 check -> ingest -> chat --evaluate 순서로 동작하는지 검증해줘.
저장소 fixture는 configs/experiments/rag/rag_realistic_docs.yaml과 data/rag_realistic/을 먼저 사용해줘.
실제 외부 원문을 추가로 쓰는 경우 원본 데이터나 큰 파일은 Git에 넣지 말고, 재현 가능한 작은 fixture와 config만 남겨줘.
검증 결과는 documents/chunks/embeddings count, metrics.json 값, 실패 CSV 여부 중심으로 정리해줘.
```

## LLM Answerer 도입 검토 요청

```text
AGENTS.md와 docs/md/rag/RAG_PIPELINE_SPEC.md를 읽고 진행해줘.
OpenAI 또는 Ollama 기반 answerer를 붙이는 것이 현재 config/artifact 계약을 깨지 않는지 검토해줘.
LangChain chain output을 그대로 밖으로 내보내지 말고, answers.jsonl의 answer/citations/status 형식으로 변환해줘.
외부 API가 필요한 테스트는 mock으로 고정하고, 실제 호출 config는 examples 또는 opt-in config로 분리해줘.
비용, 환경변수, 재현성, 환각 가능성을 README에 짧게 남겨줘.
```

## GitHub 운영 문서 요청

```text
AGENTS.md와 docs/team/operations.md를 읽고 진행해줘.
{운영 주제}에 필요한 Issue, PR, Kanban, Daily Report 규칙을 정리해줘.
팀원이 바로 복사해서 쓸 수 있는 template 형태로 작성해줘.
RAG 실험 산출물, config 경로, 평가 결과 링크를 남기는 규칙을 포함해줘.
```

## 첫 주 태스크 정리 요청

```text
docs/team/first-week.md와 docs/team/roles.md를 읽고 진행해줘.
{역할 또는 목표}에 맞는 첫 주 작업 카드를 보강해줘.
각 카드에는 목적, 담당 후보, 입력 자료, 완료 기준, 확인 방법을 넣어줘.
세부 구현 문서 링크를 많이 나열하기보다 팀원이 바로 시작할 작업 순서 중심으로 정리해줘.
```

## 역할별 설명 문서 요청

```text
docs/team/roles.md를 읽고 진행해줘.
{역할명} 팀원이 처음 봐야 할 집중 포인트를 더 이해하기 쉽게 보강해줘.
긴 링크 목록보다 첫 작업 순서, 판단 기준, 산출물 중심으로 정리해줘.
RAG 프로젝트 기준으로 Data Engineer, Experiment Lead, Application Engineer, Presentation Lead가 서로 넘겨야 하는 산출물을 분명히 해줘.
```

## 노트북 사용성 점검 요청

```text
notebooks/README.md와 docs/md/experiments/EXPERIMENT_GUIDE.md를 읽고 진행해줘.
처음 보는 팀원이 노트북에서 어떤 config 값을 바꿔야 하는지 이해할 수 있는지 점검해줘.
설명 셀, metric 확인, 그래프 확인, 산출물 경로 설명이 부족하면 보강해줘.
JSON을 그대로 보여주는 셀은 사람이 읽기 좋은 표나 요약 출력으로 바꿀 수 있는지 확인해줘.
```

## 문서 정리 요청

```text
docs/README.md와 docs/team/README.md를 읽고 진행해줘.
중복되는 문서가 있으면 하나로 합치거나 세부 참고 문서로 내려줘.
팀원이 처음 볼 문서와 세부 참고 문서가 섞이지 않게 정리해줘.
HTML은 모든 Markdown의 백업본이 아니라 설명에 직접 쓰는 자료만 유지해줘.
문서 삭제나 이동이 있으면 링크와 테스트도 함께 갱신해줘.
```
