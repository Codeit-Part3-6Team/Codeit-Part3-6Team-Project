# 노트북 사용성 체크리스트

이 문서는 로컬 RAG 노트북과 Colab 실행 노트북이 팀원이 따라가기 쉬운 상태인지 확인하기 위한 기준입니다.

## 노트북 목표

- config를 바꾸며 RAG 실험을 실행할 수 있습니다.
- 실행 결과가 어디에 저장되는지 알 수 있습니다.
- metric과 그래프를 보고 결과를 해석할 수 있습니다.
- 로컬과 Colab 중 어떤 환경에서 실행하는지 이해할 수 있습니다.

## 첫 셀에서 확인할 것

- 현재 실행 위치
- Python 버전
- 필요한 패키지 설치 여부
- project root 경로
- 사용할 config 경로

## config 설명 기준

노트북에는 아래 옵션을 바꾸면 무엇이 달라지는지 설명이 있어야 합니다.

| config 위치 | 설명 |
| --- | --- |
| `experiment.name` | 실험 산출물 폴더 이름 |
| `paths.raw_docs_dir` | 읽을 원본 문서 위치 |
| `paths.output_dir` | 결과가 저장될 위치 |
| `rag.splitter.chunk_size` | chunk 하나의 최대 길이 |
| `rag.splitter.chunk_overlap` | chunk 사이에 겹쳐 남길 길이 |
| `rag.embedding.provider` | embedding 구현체 |
| `rag.retriever.method` | keyword, semantic, hybrid 검색 방식 |
| `rag.retriever.top_k` | 검색 결과 개수 |
| `rag.answerer.mode` | extractive 또는 llm 답변 방식 |
| `artifact_policy.run_id` | 같은 실험 안에서 실행 결과를 분리하는 이름 |

## 실행 셀 기준

- `check_rag_pipeline.py`로 config를 먼저 확인합니다.
- `run_rag_ingest.py`로 문서, chunk, embedding 산출물을 만듭니다.
- `run_rag_retrieve.py`로 질문별 검색 결과를 확인합니다.
- `run_rag_chat.py`로 답변과 citation을 확인합니다.
- `run_rag_chat.py --evaluate`로 metric을 확인합니다.

## 결과 확인 셀 기준

노트북에는 아래 파일을 읽는 셀이 있으면 좋습니다.

- `parsed_documents.csv`
- `chunks.csv`
- `retrieval_results.jsonl`
- `answers.jsonl`
- `evaluation_results.csv`
- `metrics.json`
- `bad_retrievals.csv`
- `unsupported_answers.csv`
- `failed_questions.csv`

## 그래프 기준

초기에는 복잡한 시각화보다 아래 정도면 충분합니다.

- metric bar chart
- 질문별 retrieval hit 여부
- 질문별 citation correctness 여부
- 실패 유형별 count

## Colab 기준

- Colab에서 실행하는 사람이 바로 따라 할 수 있게 시작 셀을 둡니다.
- Drive mount 위치를 명확히 적습니다.
- GitHub repo URL을 바꿔야 하는 위치를 표시합니다.
- 데이터 파일은 Git에 올리지 않고 Drive 또는 별도 저장소에 둔다고 설명합니다.
- 백업 경로와 실험 산출물 경로를 분리합니다.

## 완료 기준

- 처음 보는 팀원이 어떤 config를 바꿔야 하는지 알 수 있습니다.
- 실행 후 어떤 파일을 봐야 하는지 알 수 있습니다.
- metric이 1.0이 아니어도 어디를 확인해야 하는지 알 수 있습니다.
- 로컬 실행과 Colab 실행 중 어느 환경에서 실행 중인지 헷갈리지 않습니다.
