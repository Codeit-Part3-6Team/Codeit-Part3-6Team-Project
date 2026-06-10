# 실행 스크립트

팀원이 직접 실행하는 공식 진입점입니다.
`src/`는 재사용 가능한 파이프라인 로직이고, `scripts/`는 사람이 실행하는 명령이라고 보면 됩니다.

## 가벼운 텍스트 smoke test

```bash
python scripts/run_validate.py --data-dir data/text_processed
python scripts/run_train.py --config configs/smoke/smoke_test_text.yaml --project-root .
python scripts/run_predict.py --config configs/smoke/smoke_test_text.yaml --project-root . --input data/text_processed/sample_positive.txt
```

## HuggingFace fine-tuning 예시

처음 실행할 때는 base model을 내려받기 때문에 인터넷 연결이 필요합니다. CPU에서도 실행은 가능하지만, 실제 프로젝트 데이터에서는 GPU/Colab 사용을 권장합니다.

환경 확인용 tiny model:

```bash
python scripts/run_train.py --config configs/smoke/smoke_test_hf_tiny.yaml --project-root .
python scripts/run_predict.py --config configs/smoke/smoke_test_hf_tiny.yaml --project-root . --input data/text_processed/sample_positive.txt
```

실제 실험 후보:

```bash
python scripts/run_train.py --config configs/experiments/exp002_hf_text_finetune.yaml --project-root .
python scripts/run_predict.py --config configs/experiments/exp002_hf_text_finetune.yaml --project-root . --input data/text_processed/sample_positive.txt
```

실험 결과는 config의 `paths.output_dir`에 따라 `experiments/{experiment_name}/` 아래에 저장됩니다.

## RAG smoke test

RFP 분석 챗봇 후보를 위한 최소 RAG 흐름입니다.
처음에는 외부 모델 없이 txt 문서, hashing embedding 기반 semantic retrieval, 추출형 답변으로 파이프라인 연결만 확인합니다.
loader는 `txt`, `pdf`, `docx`, `hwpx`, `hwp`를 대상으로 합니다.
PDF/HWP는 각각 `pypdf`, `olefile` 패키지가 필요합니다.
`check_rag_pipeline.py`는 실제 산출물을 만들기 전에 config, 입력 문서, 평가 질문 경로를 점검합니다.

```bash
python scripts/check_rag_pipeline.py --config configs/rag/rag_smoke_test.yaml --project-root .
python scripts/run_rag_ingest.py --config configs/rag/rag_smoke_test.yaml --project-root .
python scripts/run_rag_retrieve.py --config configs/rag/rag_smoke_test.yaml --project-root . --question "예산이 얼마야?"
python scripts/run_rag_chat.py --config configs/rag/rag_smoke_test.yaml --project-root . --question "예산이 얼마야?"
python scripts/run_rag_chat.py --config configs/rag/rag_smoke_test.yaml --project-root . --evaluate
python scripts/compare_rag_retrievers.py --project-root .
```

기본 산출물:

```text
experiments/rag_smoke_test/
|-- parsed_documents.csv
|-- chunks.csv
|-- embeddings.jsonl
|-- retrieval_results.jsonl
|-- answers.jsonl
|-- evaluation_results.csv
|-- bad_retrievals.csv
|-- unsupported_answers.csv
|-- failed_questions.csv
|-- run_status.json
|-- failure.log
`-- metrics.json
```

검색 방식 비교 산출물:

```text
reports/rag_retriever_comparison.csv
reports/rag_retriever_comparison.json
```

## 실험 결과 요약

여러 실험의 `metrics.json`, `config.yaml`, `run_info.json`을 모아 비교용 CSV/JSON을 생성합니다.

```bash
python scripts/summarize_experiments.py --project-root .
```

기본 산출물:

```text
reports/experiment_summary.csv
reports/experiment_summary.json
```
