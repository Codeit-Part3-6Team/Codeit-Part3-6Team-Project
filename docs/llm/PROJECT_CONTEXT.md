# Project Context for LLM Agents

## 프로젝트 목적

이 프로젝트는 RFP, 입찰 공고, 긴 업무 문서를 대상으로 하는 RAG 기반 분석 챗봇을 준비합니다.

핵심 목표는 다음과 같습니다.

- 문서를 표준 형태로 읽습니다.
- 문서를 검색 가능한 chunk로 나눕니다.
- 질문과 관련 있는 근거 chunk를 찾습니다.
- 답변과 citation을 함께 남깁니다.
- 실험 조건과 결과를 config와 artifact로 재현 가능하게 관리합니다.

## 현재 기본 방향

현재 프로젝트의 중심은 RAG입니다.

분류 모델, HuggingFace fine-tuning, 이미지/text smoke test는 파이프라인 구조 검증과 참고용 예제로 남아 있습니다. 새 기능을 추가할 때 기본 판단 기준은 RAG 실험에 도움이 되는지입니다.

## 현재 구현된 기능

| 영역 | 구현 상태 |
| --- | --- |
| 문서 로딩 | `txt`, `pdf`, `docx`, `hwpx`, `hwp` loader |
| Chunking | 문자 기준 size/overlap |
| Embedding | local hashing, HuggingFace mean pooling |
| Retrieval | keyword, semantic, hybrid |
| Answering | local extractive answer |
| Evaluation | retrieval hit rate, citation correctness, answer contains expected |
| Config validation | RAG 실행 전 config와 경로 점검 |
| Checkpoint/Resume | RAG ingest stage 단위 artifact 재사용 |
| Failure artifact | `run_status.json`, `failure.log`, 실패 분석 CSV |
| Experiment summary | 여러 실험의 metric/config/run info 요약 |
| Notebook | local/Colab 실험 템플릿 |
| Docs | Markdown 원본, HTML 설명 문서, README 지도 |

## 아직 구현 후보인 기능

| 후보 | 상태 | 우선순위 판단 |
| --- | --- | --- |
| FAISS/Chroma/Elasticsearch adapter | 계약만 있음 | 실제 데이터 규모가 커지면 필요 |
| LLM answerer | 계약만 있음 | RAG 답변 품질 실험 단계에서 필요 |
| reranker | 계약만 있음 | retrieval 품질 병목 확인 후 필요 |
| vector index 저장/로드 | 일부 후보 | 검색 비용이 커지면 필요 |
| fine-grained resume | 미구현 | 대량 문서 처리 중단 문제가 생기면 필요 |
| 실제 RFP PDF/HWP E2E | 미구현 | 데이터 확보 후 최우선 검증 |
| 웹앱/데모 | 예비 구조 | 담당자와 범위 확정 후 구현 |

## 작업 우선순위

1. 실제 RFP 샘플 문서로 RAG E2E를 검증합니다.
2. 검색 품질을 비교할 수 있도록 retriever config와 metric을 정리합니다.
3. LLM answerer 또는 UI는 팀 범위와 API 사용 가능 여부를 확인한 뒤 붙입니다.
4. 문서와 README는 팀원이 이해하기 쉬운 수준을 유지합니다.

## 중요한 설계 판단

- config 중심으로 실험을 바꾸는 구조를 유지합니다.
- `scripts/`는 얇게 두고, 실제 로직은 `src/`에 둡니다.
- RAG 결과는 답변만 남기지 않고 retrieval 결과와 citation을 함께 남깁니다.
- 실패도 artifact로 남깁니다.
- Git에는 재현 가능한 코드와 작은 샘플만 남깁니다.

