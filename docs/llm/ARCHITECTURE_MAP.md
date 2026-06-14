# Architecture Map for LLM Agents

## 전체 흐름

```text
configs/experiments/rag/*.yaml
    |
    v
scripts/run_rag_*.py
    |
    v
src/
    |
    v
experiments/ + reports/
```

## 경로별 책임

| 경로 | 책임 | 주의 |
| --- | --- | --- |
| `configs/experiments/rag/` | 실제 RAG 실험 조건과 실행 정책 | 새 RAG 실험은 기존 config 복사로 시작 |
| `configs/examples/` | 참고용 config | 분류/HF/smoke/preprocess는 메인 실험이 아님 |
| `scripts/` | RAG 공식 CLI 진입점 | 루트에는 RAG 실행 script를 우선 둠 |
| `scripts/examples/classification/` | 기존 분류/HF 참고 script | 새 팀원에게 기본 실행 경로로 안내하지 않음 |
| `data/rag_sample/`, `data/rag_realistic/` | RAG 샘플 문서와 평가 질문 | Git에 남기는 작은 fixture |
| `data/examples/classification/` | 기존 분류/HF 참고 fixture | RAG 메인 데이터가 아님 |
| `src/` | 재사용 가능한 구현 코드 | 테스트와 docstring 갱신 |
| `src/rag/` | RAG 구현체 | 입력/출력 계약 유지 |
| `experiments/` | 실험 결과 | 자동 생성 산출물은 보통 커밋하지 않음 |
| `reports/` | 공유용 요약 | 필요한 결과만 선별 |
| `docs/md/` | 관리용 Markdown | 문서 원본 |
| `docs/html/` | 공유/설명용 HTML | 발표나 킥오프용 |
| `tests/` | 회귀 방지 테스트 | 기능 변경 시 함께 갱신 |

## RAG 실행 흐름

```text
configs/experiments/rag/*.yaml
    -> scripts/check_rag_pipeline.py
    -> config, input path, output path, provider option 점검

run_rag_ingest.py
    -> src/config.py
    -> src/rag/document_loader.py
    -> src/rag/engines/base.py
    -> src/rag/engines/langchain.py 또는 src/rag/engines/local.py
    -> experiments/{name}/parsed_documents.csv
    -> experiments/{name}/chunks.csv
    -> experiments/{name}/embeddings.jsonl
    -> experiments/{name}/rag_ingest_checkpoint.json

run_rag_retrieve.py
    -> src/rag/pipeline.py
    -> src/rag/engines/*
    -> experiments/{name}/retrieval_results.jsonl

run_rag_chat.py
    -> src/rag/pipeline.py
    -> src/rag/engines/*
    -> experiments/{name}/answers.jsonl
    -> experiments/{name}/metrics.json
```

## 기준 Config와 데이터

| config | 데이터 | 확인 범위 |
| --- | --- | --- |
| `configs/experiments/rag/rag_langchain.yaml` | `data/rag_sample/` | TXT 샘플 기준 기본 RAG 흐름 |
| `configs/experiments/rag/rag_realistic_docs.yaml` | `data/rag_realistic/` | DOCX/HWPX loader, chunk, retrieval, answer, evaluation E2E |
| `configs/experiments/rag/rag_keyword.yaml` | `data/rag_sample/` | local keyword retriever 비교 |
| `configs/experiments/rag/rag_semantic.yaml` | `data/rag_sample/` | local semantic retriever 비교 |
| `configs/experiments/rag/rag_hybrid.yaml` | `data/rag_sample/` | local hybrid retriever 비교 |

## 작업별 수정 위치

| 작업 | 주 수정 위치 | 함께 볼 파일 |
| --- | --- | --- |
| RAG config 옵션 추가 | `src/rag/validation.py`, `configs/experiments/rag/*.yaml` | `configs/README.md`, `tests/test_rag_validation.py` |
| 새 document loader 추가 | `src/rag/document_loader.py` | `tests/test_rag_document_loader.py` |
| chunking 정책 변경 | `src/rag/engines/langchain.py`, `src/rag/chunker.py` | `docs/md/rag/RAG_PIPELINE_SPEC.md` |
| embedding 구현 추가 | `src/rag/engines/langchain.py`, `src/rag/embedder.py` | `tests/test_rag_engines.py` |
| retriever 구현 추가 | `src/rag/engines/langchain.py`, `src/rag/retriever.py` | `scripts/compare_rag_retrievers.py` |
| answerer 구현 추가 | `src/rag/engines/langchain.py`, `src/rag/answerer.py` | `tests/test_rag_pipeline.py` |
| LLM answerer provider 추가 | `src/rag/engines/langchain.py`, `src/rag/validation.py` | `configs/README.md`, `tests/test_rag_validation.py` |
| artifact 정책 변경 | `src/artifacts.py` | `tests/test_experiments.py` |
| RAG CLI 추가 | `scripts/` | `scripts/README.md`, `tests/test_scripts.py` |
| 참고용 분류 CLI 수정 | `scripts/examples/classification/` | `scripts/examples/classification/README.md`, `tests/test_scripts.py` |
| 노트북 변경 | `notebooks/` | `tests/test_notebooks.py` |
| 문서 구조 변경 | `docs/` | 관련 README와 링크를 함께 확인 |
| 실제 포맷 E2E 검증 추가 | `data/rag_realistic/`, `configs/experiments/rag/*.yaml`, `tests/test_rag_quality_gate.py` | `docs/md/overview/RAG_QUALITY_CHECKLIST.md` |

## Engine 판단 기준

현재 RAG runtime은 `rag.engine`으로 구현체를 선택합니다.
기본 실행은 `langchain`이고, `local`은 dependency-free smoke/fallback 용도로 유지합니다.

새 engine/provider를 추가할 때는 다음 순서를 지킵니다.

1. config 계약을 먼저 정합니다.
2. validation에서 지원 provider와 필수 옵션을 점검합니다.
3. engine 내부에서 LangChain 결과를 프로젝트 표준 dict로 변환합니다.
4. 작은 동작 확인 테스트와 artifact 변환 테스트를 추가합니다.
5. README와 RAG spec을 갱신합니다.

LLM answerer는 LangChain 엔진에서 `ollama`, `openai`를 사용할 수 있습니다.
pipeline 밖으로 LangChain `Document`나 chain output을 그대로 넘기지 않는 것이 핵심 원칙입니다.

## 산출물 계약

RAG 실험은 가능하면 아래 파일들을 안정적으로 남깁니다.

```text
experiments/{experiment_name}/
|-- config.yaml
|-- run_info.json
|-- run_status.json
|-- parsed_documents.csv
|-- chunks.csv
|-- embeddings.jsonl
|-- retrieval_results.jsonl
|-- answers.jsonl
|-- evaluation_results.csv
|-- metrics.json
|-- bad_retrievals.csv
|-- unsupported_answers.csv
|-- failed_questions.csv
|-- failure.log
`-- rag_ingest_checkpoint.json
```
