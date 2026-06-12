# RAG 파이프라인 리허설

이 문서는 팀원에게 공유하기 전, 현재 저장소의 RAG 파이프라인이 설명 가능한 상태인지 확인하는 최종 리허설 절차입니다.

목표는 모델 성능을 자랑하는 것이 아니라, 같은 config로 문서를 읽고, 근거를 검색하고, 답변과 citation과 평가 산출물이 남는지 확인하는 것입니다.

## 빠른 리허설

팀원에게 보여줄 때는 먼저 `notebooks/rag/rag_config_run.ipynb`를 엽니다.
노트북의 마지막 `팀 공유 전 리허설` 섹션에서 기본 TXT 샘플과 DOCX/HWPX 준실제 샘플을 함께 확인할 수 있습니다.

터미널에서 빠르게 확인하고 싶다면 아래 명령 하나로 같은 리허설을 실행합니다.

```bash
python scripts/run_rag_rehearsal.py --project-root .
```

통과 기준:

- 결과 JSON의 최상위 `ok`가 `true`
- 각 run의 `ingest.documents`, `ingest.chunks`, `ingest.embeddings`가 0보다 큼
- `metrics.not_found_rate`가 `0.0`
- `missing_artifacts`가 빈 배열
- `failure_log_exists`가 `false`

## 리허설 대상

| config | 데이터 | 확인 포인트 |
| --- | --- | --- |
| `configs/experiments/rag/rag_langchain.yaml` | `data/rag_sample/` | 기본 RAG 흐름과 산출물 계약 |
| `configs/experiments/rag/rag_realistic_docs.yaml` | `data/rag_realistic/` | DOCX/HWPX 문서 로딩, chunk, 검색, 답변, 평가 |

## 손으로 확인하는 순서

문제가 생기면 아래 순서대로 쪼개서 확인합니다.

```bash
python scripts/check_rag_pipeline.py --config configs/experiments/rag/rag_langchain.yaml --project-root .
python scripts/run_rag_ingest.py --config configs/experiments/rag/rag_langchain.yaml --project-root .
python scripts/run_rag_retrieve.py --config configs/experiments/rag/rag_langchain.yaml --project-root . --question "예산은 얼마야?"
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_langchain.yaml --project-root . --question "예산은 얼마야?"
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_langchain.yaml --project-root . --evaluate
```

DOCX/HWPX fixture는 config만 바꿔서 확인합니다.

```bash
python scripts/check_rag_pipeline.py --config configs/experiments/rag/rag_realistic_docs.yaml --project-root .
python scripts/run_rag_ingest.py --config configs/experiments/rag/rag_realistic_docs.yaml --project-root .
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_realistic_docs.yaml --project-root . --evaluate
```

## 산출물 체크

각 실험의 `experiments/{experiment_name}/` 아래에서 아래 파일을 확인합니다.

```text
config.yaml
parsed_documents.csv
chunks.csv
embeddings.jsonl
retrieval_results.jsonl
answers.jsonl
evaluation_results.csv
bad_retrievals.csv
unsupported_answers.csv
failed_questions.csv
metrics.json
run_status.json
rag_ingest_checkpoint.json
```

발표나 설명에서는 특히 아래 4개를 봅니다.

| 파일 | 설명할 내용 |
| --- | --- |
| `retrieval_results.jsonl` | 질문에 대해 어떤 chunk가 근거로 검색됐는지 |
| `answers.jsonl` | 답변, citation, 답변 상태 |
| `metrics.json` | retrieval, answer, citation 평가 지표 |
| 실패 CSV 3종 | 실패가 retrieval 문제인지, answer 문제인지, 실행 문제인지 |

## 실패했을 때

| 증상 | 먼저 볼 것 |
| --- | --- |
| `check` 실패 | config 경로, `paths.raw_docs_dir`, `evaluation.questions_path` |
| 문서 수가 0 | loader `file_types`, 데이터 위치, 파일 확장자 |
| metric이 낮음 | `retrieval_results.jsonl`, `bad_retrievals.csv` |
| citation이 이상함 | chunk metadata의 `chunk_id`, `source_path`, `page`, `section` |
| 실행 중 예외 | `run_status.json`, `failure.log` |

## 외부 LLM provider

기본 리허설은 비용이 들지 않는 local provider만 사용합니다.

Ollama/OpenAI 예시는 `configs/examples/rag/`에 있으며, 해당 config를 직접 선택해서 실행할 때만 외부 모델을 호출합니다. OpenAI는 `OPENAI_API_KEY` 같은 환경변수가 준비된 경우에만 실제 호출 대상으로 봅니다.
