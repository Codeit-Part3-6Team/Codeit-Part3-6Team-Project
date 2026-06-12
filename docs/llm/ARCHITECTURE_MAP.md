# Architecture Map for LLM Agents

## 전체 흐름

```text
configs/*.yaml
    |
    v
scripts/*.py
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
| `configs/` | 실험 조건과 실행 정책 | 새 실험은 기존 config 복사로 시작 |
| `scripts/` | 사람이 실행하는 CLI 진입점 | 로직을 많이 넣지 않음 |
| `src/` | 재사용 가능한 구현 코드 | 테스트와 docstring 갱신 |
| `src/rag/` | RAG 구현체 | 입력/출력 계약 유지 |
| `experiments/` | 실험 결과 | 자동 생성 산출물은 보통 커밋하지 않음 |
| `reports/` | 공유용 요약 | 필요한 결과만 선별 |
| `docs/md/` | 관리용 Markdown | 문서 원본 |
| `docs/html/` | 공유/설명용 HTML | 발표나 킥오프용 |
| `tests/` | 회귀 방지 테스트 | 기능 변경 시 함께 갱신 |

## RAG 실행 흐름

```text
run_rag_ingest.py
    -> src/config.py
    -> src/rag/document_loader.py
    -> src/rag/chunker.py
    -> src/rag/adapters.py
    -> src/rag/embedder.py
    -> experiments/{name}/parsed_documents.csv
    -> experiments/{name}/chunks.csv
    -> experiments/{name}/embeddings.jsonl
    -> experiments/{name}/rag_ingest_checkpoint.json

run_rag_retrieve.py
    -> src/rag/retriever.py
    -> experiments/{name}/retrieval_results.jsonl

run_rag_chat.py
    -> src/rag/answerer.py
    -> experiments/{name}/answers.jsonl
    -> experiments/{name}/metrics.json
```

## 작업별 수정 위치

| 작업 | 주 수정 위치 | 함께 볼 파일 |
| --- | --- | --- |
| RAG config 옵션 추가 | `src/rag/validation.py`, `configs/experiments/rag/*.yaml` | `configs/README.md`, `tests/test_rag_validation.py` |
| 새 document loader 추가 | `src/rag/document_loader.py` | `tests/test_rag_document_loader.py` |
| chunking 정책 변경 | `src/rag/chunker.py` | `docs/md/rag/RAG_PIPELINE_SPEC.md` |
| embedding 구현 추가 | `src/rag/embedder.py`, `src/rag/adapters.py` | `tests/test_rag_adapters.py` |
| retriever 구현 추가 | `src/rag/retriever.py`, `src/rag/adapters.py` | `scripts/compare_rag_retrievers.py` |
| answerer 구현 추가 | `src/rag/answerer.py`, `src/rag/adapters.py` | `tests/test_rag_pipeline.py` |
| LLM answerer provider 추가 | `src/rag/adapters.py`, `src/rag/validation.py` | `configs/README.md`, `tests/test_rag_validation.py` |
| artifact 정책 변경 | `src/artifacts.py` | `tests/test_experiments.py` |
| CLI 추가 | `scripts/` | `scripts/README.md`, `tests/test_scripts.py` |
| 노트북 변경 | `notebooks/` | `tests/test_notebooks.py` |
| 문서 구조 변경 | `docs/` | `tests/test_docs_structure.py` |

## Adapter 판단 기준

현재 RAG adapter는 config로 구현체를 선택하는 방향입니다.

새 provider를 추가할 때는 다음 순서를 지킵니다.

1. config 계약을 먼저 정합니다.
2. validation에서 지원 provider와 필수 옵션을 점검합니다.
3. adapter registry에서 provider를 선택하게 합니다.
4. 작은 동작 확인 테스트를 추가합니다.
5. README와 RAG spec을 갱신합니다.

LLM answerer는 현재 `openai`, `huggingface`, `ollama` provider 계약만 검증합니다.
실제 API/server 호출 구현은 프로젝트 진행 중 결정합니다.

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
