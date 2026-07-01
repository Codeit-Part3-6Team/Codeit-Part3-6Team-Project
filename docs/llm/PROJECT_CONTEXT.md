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

분류 모델, HuggingFace fine-tuning, 이미지/text 동작 확인은 파이프라인 구조 검증과 참고용 예제로 남아 있습니다. 새 기능을 추가할 때 기본 판단 기준은 RAG 실험에 도움이 되는지입니다.

참고용 분류 자산은 메인 경로에서 분리되어 있습니다.

- config: `configs/examples/classification/`
- data fixture: `data/examples/classification/`
- script: `scripts/examples/classification/`

## 현재 구현된 기능

| 영역 | 구현 상태 |
| --- | --- |
| 문서 로딩 | `txt`, `pdf`, `docx`, `hwpx`, `hwp`, `csv` loader |
| Engine | LangChain 기본 실행, local fallback |
| Chunking | local splitter, LangChain RecursiveCharacterTextSplitter |
| Embedding | local hashing, HuggingFace/Ollama/OpenAI LangChain embedding 후보 |
| Retrieval | LangChain similarity, local keyword/semantic/hybrid |
| Answering | local extractive answer, LangChain Ollama/OpenAI |
| Evaluation | retrieval hit rate, citation correctness, answer contains expected |
| Config validation | RAG 실행 전 config와 경로 점검 |
| Checkpoint/Resume | RAG ingest stage 단위 artifact 재사용 |
| Failure artifact | `run_status.json`, `failure.log`, 실패 분석 CSV |
| Experiment summary | 여러 실험의 metric/config/run info 요약 |
| Notebook | 로컬 RAG walkthrough, 분석 노트북 |
| Docs | Markdown 원본, HTML 설명 문서, README 지도 |
| 실제 포맷 점검 | `configs/experiments/rag/rag_realistic_docs.yaml` 기준 DOCX/HWPX 준실제 샘플 확인, PDF loader 단위 검증 통과 |
| Agent Loop | Phase DAG + Tool dispatch 기반 자동화 루프 (`src/rag/agent.py`) |
| Chatbot 모드 | LLM 동적 Tool 선택 방식의 대화형 실행 (`src/rag/chatbot.py`) |
| Structured Output | Pydantic `output_schema` 기반 정형 출력 제어 (`src/rag/schema_parser.py`) |
| Phase 간 데이터 전달 | `input_from` 필드로 이전 Phase 산출물을 다음 Phase 입력으로 연결 |
| Agent config | `agent.enabled`, `agent.phases`, `agent.tools`, `agent.chatbot` 등 agent.* 설정 체계 (`configs/experiments/rag/agent/`) |
| Agent CLI | `scripts/run_rag_agent.py` |

## 아직 구현 후보인 기능

| 후보 | 상태 | 우선순위 판단 |
| --- | --- | --- |
| FAISS/Elasticsearch adapter | 계약만 있음 | 실제 데이터 규모가 커지면 필요 |
| OpenAI/Ollama answerer | LangChain 엔진에서 사용 가능 | API/로컬 서버 사용 가능 여부, 비용, 환각률 확인 후 본 실험에 적용 |
| reranker | 계약만 있음 | retrieval 품질 병목 확인 후 필요 |
| vector index 저장/로드 | Chroma provider 계약 있음 | 검색 비용이 커지면 실제 index 저장소로 승격 |
| fine-grained resume | 미구현 | 대량 문서 처리 중단 문제가 생기면 필요 |
| 실제 외부 RFP PDF/HWP E2E | 대기 | 실제 공고 원문 확보 후 PDF/HWP/HWPX 품질 재검증 |
| 웹앱/데모 | 예비 구조 | 담당자와 범위 확정 후 구현 |

## 작업 우선순위

1. 팀 공유 문서는 `docs/team/kickoff.md`를 상위 개요로 두고, `README -> timeline -> operations -> workflow -> roles -> first-week` 흐름을 유지합니다.
2. 검색 품질을 비교할 수 있도록 retriever config와 metric을 정리합니다.
3. OpenAI/Ollama answerer 또는 UI는 팀 범위, API 사용 가능 여부, 비용을 확인한 뒤 실제 실험 config로 승격합니다.
4. RAG와 무관한 참고 자산은 `examples/` 하위에 유지해 메인 흐름과 섞이지 않게 합니다.
5. 문서와 README는 팀원이 이해하기 쉬운 수준을 유지합니다.

## 기준 검증 Config

| config | 목적 | 최소 확인 명령 |
| --- | --- | --- |
| `configs/experiments/rag/rag_langchain.yaml` | TXT 샘플 기준 기본 LangChain RAG 흐름 | `python scripts/run_rag_chat.py --config configs/experiments/rag/rag_langchain.yaml --project-root . --evaluate` |
| `configs/experiments/rag/rag_realistic_docs.yaml` | DOCX/HWPX 준실제 RFP 문서 포맷 점검 | `python scripts/run_rag_chat.py --config configs/experiments/rag/rag_realistic_docs.yaml --project-root . --evaluate` |
| `configs/experiments/rag/rag_keyword.yaml` | local keyword retriever 비교 | `python scripts/compare_rag_retrievers.py --project-root .` |
| `configs/experiments/rag/rag_semantic.yaml` | local semantic retriever 비교 | `python scripts/compare_rag_retrievers.py --project-root .` |
| `configs/experiments/rag/rag_hybrid.yaml` | local hybrid retriever 비교 | `python scripts/compare_rag_retrievers.py --project-root .` |

## 중요한 설계 판단

- config 중심으로 실험을 바꾸는 구조를 유지합니다.
- 이 프로젝트는 LangChain 대체재가 아니라 LangChain 기반 RAG 실행도 같은 산출물/evaluation 계약으로 관리하는 harness입니다.
- LangChain `Document`, retriever result, chain output은 엔진 내부에서 끝내고, pipeline에는 프로젝트 표준 dict만 넘깁니다.
- 검색과 답변 생성을 완전히 chain 안에 숨기지 않습니다. retrieval 결과를 먼저 표준 artifact로 남긴 뒤 answer artifact와 citation을 연결합니다.
- `scripts/`는 얇게 두고, 실제 로직은 `src/`에 둡니다.
- RAG 결과는 답변만 남기지 않고 retrieval 결과와 citation을 함께 남깁니다.
- 실패도 artifact로 남깁니다.
- Git에는 재현 가능한 코드와 작은 샘플만 남깁니다.
- Agent 모드는 `agent.enabled: true`로 RAG와 전환 가능하며, Phase DAG와 Tool dispatch를 통해 기존 RAG 파이프라인과 동일한 산출물 계약을 유지합니다.
