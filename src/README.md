# Source Directory

`src/`는 파이프라인의 실제 구현 코드가 들어가는 곳입니다.

현재 프로젝트의 기본 구현 대상은 RAG입니다. `src/train.py`, `src/predict.py`, `src/models/`는 기존 분류/HuggingFace 학습 파이프라인 참고용으로 남아 있습니다.

## 구조

```text
src/
|-- rag/            # RAG 문서 처리, 검색, 답변, 평가
|-- config.py       # YAML config 로딩과 JSON 저장
|-- artifacts.py    # 실험 산출물, run status, failure log, backup
|-- experiments.py  # 여러 실험 결과 요약
|-- metrics.py      # 공통 metric 계산
|-- utils/          # logging, path, seed
|-- data.py         # 참고용 분류 데이터 로딩
|-- train.py        # 참고용 분류/HF 학습 루프
|-- predict.py      # 참고용 분류 예측
`-- models/         # 참고용 분류 모델 구현체
```

## RAG 모듈

| 모듈 | 책임 |
| --- | --- |
| `src/rag/document_loader.py` | txt, pdf, docx, hwpx, hwp 문서 로딩 |
| `src/rag/engines/` | LangChain 기본 엔진과 local fallback 엔진 |
| `src/rag/chunker.py` | 문서를 검색 가능한 chunk로 분할 |
| `src/rag/embedder.py` | chunk text를 embedding vector로 변환 |
| `src/rag/vector_store.py` | embedding 기반 검색 |
| `src/rag/retriever.py` | keyword, semantic, hybrid retrieval |
| `src/rag/answerer.py` | 검색된 근거 기반 답변과 citation 생성 |
| `src/rag/adapters.py` | local fallback용 provider 선택 |
| `src/rag/pipeline.py` | ingest, retrieve, chat, evaluate 실행 흐름 |
| `src/rag/validation.py` | RAG config와 입력 경로 검증 |
| `src/rag/comparison.py` | retriever 비교 리포트 생성 |

## 공통 모듈

| 모듈 | 책임 |
| --- | --- |
| `src/config.py` | config 로드와 저장 |
| `src/artifacts.py` | output directory, status, failure log, backup |
| `src/experiments.py` | 실험 summary 생성 |
| `src/metrics.py` | metric 계산 |
| `src/utils/` | 경로, seed, logging 유틸 |

## RAG 흐름

```text
run_rag_ingest.py
  -> document_loader.py
  -> engines/base.py
  -> engines/langchain.py 또는 engines/local.py
  -> embeddings.jsonl
  -> rag_ingest_checkpoint.json

run_rag_retrieve.py
  -> pipeline.py
  -> engines/*
  -> retrieval_results.jsonl

run_rag_chat.py
  -> retrieve
  -> engines/*
  -> answers.jsonl

run_rag_chat.py --evaluate
  -> metrics.json
  -> bad_retrievals.csv
  -> unsupported_answers.csv
  -> failed_questions.csv
```

## 참고용 ML 코드

아래 코드는 현재 RAG 프로젝트의 메인 경로가 아닙니다.

- `src/train.py`
- `src/predict.py`
- `src/data.py`
- `src/models/`

삭제하지 않는 이유는 기존 smoke test, artifact 정책, backup 정책, HuggingFace 참고 구현을 보존하기 위해서입니다. 새 RAG 기능을 추가할 때는 우선 `src/rag/`를 수정합니다.
