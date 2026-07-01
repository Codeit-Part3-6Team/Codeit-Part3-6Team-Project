# RAG 산출물 점검 체크리스트

이 문서는 킥오프에서 순서대로 소개하는 필수 문서가 아닙니다.

RAG 실행 결과를 팀에 공유하기 전, 산출물이 설명 가능한 상태인지 따로 확인할 때만 참고합니다. 노트북이나 코드 안에 리허설 책임을 섞지 않고, 실행 결과를 점검하는 체크리스트로만 사용합니다.

## 언제 보는가

| 상황 | 확인할 내용 |
| --- | --- |
| RAG config를 처음 실행했을 때 | 필수 artifact가 생성됐는지 |
| retriever나 answerer 설정을 바꿨을 때 | 검색 근거와 답변이 함께 남았는지 |
| 발표 예시를 고를 때 | 질문, 근거 chunk, 답변, citation이 설명 가능한지 |
| 실패 사례를 정리할 때 | retrieval 문제인지 answer 문제인지 구분되는지 |

## 필수 artifact

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
agent_state.jsonl
agent_metrics.json
run_status.json
rag_ingest_checkpoint.json
```

## 설명할 때 먼저 볼 파일

| 파일 | 설명할 내용 |
| --- | --- |
| `retrieval_results.jsonl` | 질문에 대해 어떤 chunk가 근거로 검색됐는지 |
| `answers.jsonl` | 답변, citation, 답변 상태 |
| `metrics.json` | retrieval, answer, citation 평가 지표 |
| 실패 CSV 3종 | 실패가 retrieval 문제인지, answer 문제인지, 실행 문제인지 |

## 통과 기준

- 문서 수와 chunk 수가 0보다 큽니다.
- 질문별 retrieval 결과가 남습니다.
- 답변에는 citation이 함께 남습니다.
- metric을 보고 성공/실패 질문을 구분할 수 있습니다.
- 실패가 있으면 `bad_retrievals.csv`, `unsupported_answers.csv`, `failed_questions.csv` 중 어디에 남았는지 설명할 수 있습니다.

## 실패했을 때 먼저 볼 것

| 증상 | 먼저 볼 것 |
| --- | --- |
| `check` 실패 | config 경로, `paths.raw_docs_dir`, `evaluation.questions_path` |
| 문서 수가 0 | loader `file_types`, 데이터 위치, 파일 확장자 |
| metric이 낮음 | `retrieval_results.jsonl`, `bad_retrievals.csv` |
| citation이 이상함 | chunk metadata의 `chunk_id`, `source_path`, `page`, `section` |
| 실행 중 예외 | `run_status.json`, `failure.log` |

## 실행 위치

단일 실험 실행은 `notebooks/rag/rag_config_run.ipynb`에서 `EXP_NAME`을 선택해 진행합니다.

비교 실험, DOCX/HWPX fixture 점검은 각각 별도 config, 별도 Issue에서 다룹니다.
