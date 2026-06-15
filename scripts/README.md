# Scripts

`scripts/`는 사람이 직접 실행하는 공식 진입점입니다.

현재 프로젝트의 기본 실행 대상은 RAG입니다. 분류 학습용 script는 `scripts/examples/classification/` 아래에 참고용으로 분리합니다.

## RAG Python 스크립트

| script | 용도 |
| --- | --- |
| `check_rag_pipeline.py` | RAG config, 입력 문서, 평가 질문 경로 점검 |
| `run_rag_ingest.py` | 문서 로딩, chunking, embedding 생성 |
| `run_rag_retrieve.py` | 질문에 대한 검색 결과 확인 |
| `run_rag_chat.py` | 답변 생성 또는 평가 실행 |
| `compare_rag_retrievers.py` | retriever config 비교 리포트 생성 |
| `summarize_experiments.py` | RAG 실험 metric/config/run info 요약 |

## Shell 스크립트 (GCP VM)

| script | 용도 |
| --- | --- |
| `setup_vm.sh` | VM 초기 환경 구성 (Miniconda, Ollama, Jupyter 커널) |
| `sync_data.sh` | Drive ↔ VM 데이터 동기화 (pull/push) |
| `backup_experiments.sh` | 실험 결과 Google Drive 백업 |

## 기본 실행 순서

```bash
python scripts/check_rag_pipeline.py --config configs/experiments/rag/rag_langchain.yaml --project-root .
python scripts/run_rag_ingest.py --config configs/experiments/rag/rag_langchain.yaml --project-root .
python scripts/run_rag_retrieve.py --config configs/experiments/rag/rag_langchain.yaml --project-root . --question "예산은 얼마야?"
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_langchain.yaml --project-root . --question "예산은 얼마야?"
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_langchain.yaml --project-root . --evaluate
python scripts/compare_rag_retrievers.py --project-root .
```

## RAG 산출물

```text
experiments/rag_langchain/
|-- config.yaml
|-- run_info.json
|-- parsed_documents.csv
|-- chunks.csv
|-- embeddings.jsonl
|-- retrieval_results.jsonl
|-- answers.jsonl
|-- evaluation_results.csv
|-- bad_retrievals.csv
|-- unsupported_answers.csv
|-- failed_questions.csv
|-- metrics.json
|-- run_status.json
|-- failure.log
`-- rag_ingest_checkpoint.json
```

## 결과 요약

여러 실험의 `metrics.json`, `config.yaml`, `run_info.json`을 모아 비교하려면 아래 명령을 실행합니다.

```bash
python scripts/summarize_experiments.py --project-root .
```

결과:

```text
reports/experiment_summary.csv
reports/experiment_summary.json
```

## 참고용 ML 명령

아래 명령은 현재 RAG 프로젝트의 기본 흐름이 아니라, 기존 분류/HuggingFace 파이프라인 검증용입니다.

```bash
python scripts/examples/classification/run_validate.py --data-dir data/examples/classification/text_processed
python scripts/examples/classification/run_train.py --config configs/examples/classification/smoke_test_text.yaml --project-root .
python scripts/examples/classification/run_predict.py --config configs/examples/classification/smoke_test_text.yaml --project-root . --input data/examples/classification/text_processed/sample_positive.txt
```

새 팀원에게는 우선 RAG 명령만 안내합니다.
