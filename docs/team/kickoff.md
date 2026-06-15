# RAG 기반 RFP 문서 분석 프로젝트 킥오프

이 문서는 프로젝트 시작 시 팀이 함께 합의해야 할 목표, 운영 방식, 역할, 일정, 리스크를 정리한 킥오프 문서입니다.

세부 구현 방법은 `docs/md/`와 `docs/llm/`에 나누어 관리합니다. 이 문서는 세부 문서를 전부 대신하지 않고, 팀이 같은 방향으로 출발하기 위한 기준선 역할을 합니다.

## 목차

1. [프로젝트 맥락과 목표](#1-프로젝트-맥락과-목표)
2. [기술 방향](#2-기술-방향)
3. [협업 인프라와 운영 원칙](#3-협업-인프라와-운영-원칙)
4. [역할 분담 원칙](#4-역할-분담-원칙)
5. [단계별 진행 계획](#5-단계별-진행-계획)
6. [주요 리스크와 대응](#6-주요-리스크와-대응)
7. [성공 기준](#7-성공-기준)
8. [첫 액션 아이템](#8-첫-액션-아이템)
9. [함께 볼 문서](#9-함께-볼-문서)

## 1. 프로젝트 맥락과 목표

### 문제 상황

RFP와 입찰 공고 문서는 길고, 요구사항, 제출 조건, 평가 기준, 예산 같은 핵심 정보를 찾기 어렵습니다. 팀은 이런 문서를 읽고 질문에 답할 수 있는 RAG 파이프라인을 준비합니다.

### 우리가 만들 기준선

이번 프로젝트의 1차 목표는 config 기반 RAG 실험 파이프라인과 산출물 규칙을 안정적으로 준비하고, 실험으로 검증된 최적 설정을 바탕으로 RFP 문서 분석 서비스를 완성하는 것입니다.

기본 흐름은 다음과 같습니다.

```text
raw docs -> chunk -> embedding/index -> retrieve -> answer -> citation/evaluate
```

### 남겨야 할 산출물

- 사용한 문서와 질문 예시
- 검색된 근거 chunk
- 답변과 citation
- metric 또는 실패 사례
- 실험 config와 실행 기록
- 발표에서 설명할 한계와 개선 방향

## 2. 기술 방향

### RAG 파이프라인

파이프라인은 문서를 읽고, chunk로 나누고, 질문과 관련 있는 근거를 검색한 뒤, 답변과 citation을 함께 남기는 흐름으로 봅니다.

현재 핵심은 RAG 실행 자체보다 산출물 계약을 지키는 것입니다. 답변만 확인하지 않고 `retrieval_results.jsonl`, `answers.jsonl`, `metrics.json`, 실패 분석 파일을 함께 봅니다.

### LangChain 사용 범위

팀은 LangChain을 주요 RAG 실행 엔진으로 사용합니다. 다만 프로젝트 코드는 LangChain을 그대로 노출하는 앱이 아니라, config와 artifact 규칙을 관리하는 실험 harness 역할을 합니다.

Experiment Lead는 다음 영역을 우선 확인합니다.

- retriever 설정
- answerer 설정
- LangChain config
- evaluation 결과
- citation과 failure artifact

### 실행 환경

GCP VM 환경에서 실험을 진행합니다.

- 로컬: 빠른 수정, smoke test, 작은 샘플 실험
- GCP VM: GPU와 충분한 메모리로 실제 문서 실험을 진행합니다.
- OpenAI/Ollama: 답변 품질, 비용, 재현성, 로컬 자원 상황을 보고 선택

## 3. 협업 인프라와 운영 원칙

### GitHub를 정본으로 둡니다

GitHub repository는 코드, config, 문서, Issue, PR, 실험 기록의 기준 위치입니다.

### 브랜치와 PR

- `main`: 항상 공유 가능한 기준선
- 작업 브랜치: 책임 단위로 분리
- PR: 변경 요약, 테스트 결과, 산출물 경로를 남김

문서, 노트북, 운영 템플릿, RAG 구현 변경은 가능하면 같은 PR에 섞지 않습니다.

### Kanban

보드 컬럼은 아래 흐름을 기본으로 둡니다.

```text
Backlog -> Ready -> In Progress -> Review -> Done
```

초기에는 카드를 Backlog에 두고, 담당자와 완료 기준이 분명해진 카드만 Ready로 옮깁니다.

### Daily Report

Daily Report는 감시용 문서가 아니라 막힘을 빨리 발견하기 위한 장치입니다.

- 어제 한 일
- 오늘 할 일
- 막힌 점
- 공유 링크
- 다음 액션

## 4. 역할 분담 원칙

역할은 사람을 고정하기 위한 이름이 아니라 책임 경계를 분명히 하기 위한 장치입니다.

| 역할 | 핵심 책임 | 주요 산출물 |
| --- | --- | --- |
| PM | 일정, 보드, 역할 배정, 막힘 관리, merge 기준 | 보드, 결정 사항, 회의 후 액션 |
| Data Engineer | 원본 문서 확보, loader 확인, 평가 질문 준비 | 데이터 후보, 로딩 결과, 평가 질문 CSV |
| Experiment Lead | retriever, answerer, LangChain config, evaluation 관리 | config, metric, 실패 사례, 비교 메모 |
| Application Engineer | 입출력 계약, 데모/API 후보, citation 표시 방식 | 응답 예시, 데모 방식 후보, API 범위 |
| Presentation Lead | 문제 설명, 용어 정리, 발표 흐름과 시각 자료 | 발표 흐름, 예시 화면, 한계 정리 |

역할별 세부 첫 작업은 `docs/team/roles.md`에서 확인합니다.

## 5. 단계별 진행 계획

공식 일정은 평일 기준으로 관리합니다.

| 기간 | 집중할 일 | 완료 기준 |
| --- | --- | --- |
| 2026-06-17 | 프로젝트 설명과 운영 기준 합의 | 팀이 목표, 역할, 보드 사용 방식을 이해합니다. |
| 2026-06-18 ~ 2026-06-19 | 환경, 문서, 역할, 보드 정리 | 팀원이 실행 방법과 Issue/PR 흐름을 이해합니다. |
| 2026-06-22 ~ 2026-06-26 | 데이터 후보와 RAG baseline 실행 | 문서 loader, 평가 질문, 기본 RAG 산출물이 확인됩니다. |
| 2026-06-29 ~ 2026-07-03 | retriever, answerer, config 실험 | 비교 가능한 config와 metric, 실패 사례가 남습니다. |
| 2026-07-06 ~ 2026-07-07 | 발표 자료와 데모 흐름 정리 | 질문, 답변, citation, 한계가 발표 흐름으로 연결됩니다. |
| 2026-07-08 | 발표 | 결과, 한계, 개선 방향을 설명합니다. |

주말은 공식 일정에 넣지 않습니다. 추가 작업이 필요하면 그때 따로 합의합니다.

## 6. 주요 리스크와 대응

| 리스크 | 영향 | 대응 |
| --- | --- | --- |
| 실제 RFP 문서가 늦게 확보됨 | 평가 질문과 loader 검증이 늦어짐 | 샘플 문서로 산출물 계약을 먼저 고정합니다. |
| parser가 문서를 제대로 읽지 못함 | retrieval 품질이 낮아짐 | 실패 문서와 깨진 텍스트를 Data Engineer가 따로 기록합니다. |
| 답변만 보고 검색 근거를 놓침 | 그럴듯하지만 검증 어려운 결과가 됨 | retrieval 결과, citation, failure artifact를 함께 확인합니다. |
| 자원 차이가 크면 | 팀원별 실행 가능 범위가 달라짐 | GCP VM으로 통일된 환경을 제공합니다. |
| config와 코드 변경이 섞임 | 실험 비교가 어려워짐 | 실험 조건은 config에 두고, 코드 변경은 별도 PR로 관리합니다. |
| PR 책임이 섞임 | 리뷰와 rollback이 어려워짐 | 문서, 노트북, 운영 템플릿, 구현 변경을 분리합니다. |

## 7. 성공 기준

### 기술 기준

- RAG pipeline이 config 기반으로 실행됩니다.
- 검색 결과, 답변, citation, metric이 artifact로 남습니다.
- 최소 1개 이상의 평가 질문 세트로 결과를 확인합니다.
- 실패 사례를 설명할 수 있습니다.

### 협업 기준

- 모든 주요 작업이 Issue나 Kanban 카드로 추적됩니다.
- PR에 변경 이유와 확인 방법이 남습니다.
- 막힌 점이 Daily Report나 회의에서 공유됩니다.
- 팀원이 자기 역할의 입력과 출력을 설명할 수 있습니다.

### 발표 기준

- 문제 상황을 한 문단으로 설명할 수 있습니다.
- 질문, 검색 근거, 답변, citation 예시를 보여줄 수 있습니다.
- 어떤 설정을 바꿨고 결과가 어떻게 달라졌는지 설명할 수 있습니다.
- 한계와 다음 개선 방향을 말할 수 있습니다.

## 8. 첫 액션 아이템

### 팀 전체

- [ ] `docs/team/README.md`에서 처음 볼 문서를 확인합니다.
- [ ] `docs/team/roles.md`에서 자기 역할의 첫 작업을 확인합니다.
- [ ] GCP VM 또는 로컬에서 RAG 실행 흐름을 한 번 확인합니다.
- [ ] 첫 Issue나 Kanban 카드에 완료 기준을 적습니다.

### PM

- [ ] GitHub Project 보드와 라벨을 확인합니다.
- [ ] 첫 주 카드를 Backlog에 등록합니다.
- [ ] 역할별 담당자와 Review 기준을 정합니다.

### Data Engineer

- [ ] 실제 RFP 후보 문서와 파일 형식을 정리합니다.
- [ ] 원본 데이터 저장 위치와 Git 제외 규칙을 확인합니다.
- [ ] 평가 질문 CSV 초안을 준비합니다.

### Experiment Lead

- [ ] `configs/experiments/rag/`의 기본 config를 확인합니다.
- [ ] `retrieval_results.jsonl`, `answers.jsonl`, `metrics.json`의 의미를 확인합니다.
- [ ] retriever, answerer, evaluation 중 먼저 비교할 축을 정합니다.

### Application Engineer

- [ ] 답변 API나 데모 화면에 필요한 입력/출력 예시를 정리합니다.
- [ ] citation을 어떤 형태로 보여줄지 후보를 정합니다.

### Presentation Lead

- [ ] 문제 상황, RAG 흐름, 산출물 예시를 발표 흐름으로 묶습니다.
- [ ] 팀원이 모르는 용어를 쉬운 말로 바꿉니다.

## 9. 함께 볼 문서

- `docs/team/timeline.md`
- `docs/team/roles.md`
- `docs/team/first-week.md`
- `docs/team/operations.md`
- `docs/team/workflow.md`
- `docs/md/rag/RAG_PIPELINE_SPEC.md`
- `docs/md/data/DATA_CONTRACT.md`
- `docs/md/experiments/EXPERIMENT_GUIDE.md`
- `docs/html/overview/pipeline_explainer.html`
- `docs/html/overview/module_architecture.html`
