# RAG 기반 RFP 문서 분석 챗봇

입찰 공고, 제안요청서(RFP), 긴 업무 문서에서 필요한 정보를 빠르게 찾고 근거와 함께 답변하기 위한 RAG 프로젝트입니다.

이 저장소는 최종 서비스 구현 전에 팀이 공통으로 사용할 RAG 파이프라인, 실험 config, 산출물 규칙, 문서화 방식을 미리 검증하기 위해 준비했습니다. 목표는 단순히 “답변이 나오는 챗봇”이 아니라, 문서를 읽고, 나누고, 검색하고, 답변하고, 평가하는 전체 흐름을 재현 가능하게 만드는 것입니다.

## 프로젝트 배경

RFP 문서는 분량이 길고 구조가 복잡해서 담당자가 직접 읽으며 예산, 자격 요건, 제출 기한, 평가 기준을 찾는 데 시간이 많이 듭니다.

단순 키워드 검색만으로는 “이 사업의 핵심 요구사항은 뭐야?”, “예산 근거는 어디에 있어?”, “지원 자격을 요약해줘” 같은 문맥 기반 질문에 안정적으로 답하기 어렵습니다. 그래서 이 프로젝트는 RAG 구조를 사용해 관련 문단을 먼저 찾고, 답변과 citation을 함께 남기는 방식을 기본으로 합니다.

## 해결하려는 문제

- 긴 문서에서 핵심 정보를 빠르게 찾습니다.
- 답변의 근거가 되는 chunk와 citation을 함께 남깁니다.
- retriever, chunk 크기, embedding 설정을 config로 바꿔 실험합니다.
- 평가 질문 세트로 retrieval hit rate, citation correctness 같은 RAG metric을 확인합니다.
- 팀원이 같은 명령어와 같은 폴더 구조로 실험을 반복할 수 있게 합니다.

## 현재 구현 상태

현재는 RAG 프로젝트를 시작하기 위한 기본 실험 인프라가 중심입니다.

| 영역 | 현재 상태 |
| --- | --- |
| 문서 로더 | `txt`, `pdf`, `docx`, `hwpx`, `hwp` 지원 |
| Chunking | 문자 기준 size/overlap config 지원 |
| Embedding | local hashing, HuggingFace mean pooling |
| Retrieval | keyword, semantic, hybrid |
| Answer | local extractive answer |
| Evaluation | retrieval hit rate, citation correctness, answer contains expected |
| Checkpoint/Resume | RAG ingest 단계 산출물 재사용 |
| Config Validation | RAG 실행 전 config와 입력 경로 점검 |
| 문서화 | Markdown 원본과 HTML 공유 문서 병행 |

FAISS, Chroma, Elasticsearch, reranker, OpenAI/HuggingFace LLM 답변은 config 계약과 검증 규칙을 먼저 잡아둔 상태이며, 실제 프로젝트 요구가 확정되면 adapter 구현체를 붙이면 됩니다.

## 프로젝트 구조

```text
.
|-- app/                         # 추후 웹앱/API 연결을 위한 예비 영역
|-- configs/
|   |-- experiments/rag/          # RAG 실험 config
|   |-- examples/classification/  # 분류/HF 참고 예제 config
|   |-- preprocess/               # 전처리 config
|   `-- smoke/                    # 빠른 파이프라인 검증 config
|-- data/                         # raw/interim/processed/external 데이터 영역
|-- docs/
|   |-- md/                       # 원본/관리용 Markdown 문서
|   `-- html/                     # 공유/설명용 HTML 문서
|-- experiments/                  # 실험 실행 결과 저장 위치
|-- notebooks/                    # 로컬/Colab 실험 노트북 템플릿
|-- reports/                      # 실험 요약, Daily Report 템플릿
|-- scripts/                      # 팀원이 직접 실행하는 공식 진입점
|-- src/                          # 파이프라인 실제 구현
`-- tests/                        # 단위 테스트와 smoke test
```

## 빠른 시작

```bash
conda env create -f environment.yml
conda activate codeit-ml-pipeline
```

이미 Python 환경이 있다면 다음처럼 설치해도 됩니다.

```bash
pip install -r requirements.txt
```

전체 테스트:

```bash
python -m pytest
```

## RAG 기본 실행

RAG 기본 config는 `configs/experiments/rag/rag_smoke_test.yaml`입니다.

```bash
python scripts/check_rag_pipeline.py --config configs/experiments/rag/rag_smoke_test.yaml --project-root .
python scripts/run_rag_ingest.py --config configs/experiments/rag/rag_smoke_test.yaml --project-root .
python scripts/run_rag_retrieve.py --config configs/experiments/rag/rag_smoke_test.yaml --project-root . --question "예산은 얼마야?"
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_smoke_test.yaml --project-root . --question "예산은 얼마야?"
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_smoke_test.yaml --project-root . --evaluate
python scripts/compare_rag_retrievers.py --project-root .
```

## 실험 산출물

RAG 실험 결과는 `experiments/{experiment.name}/` 아래에 저장됩니다.

```text
experiments/rag_smoke_test/
|-- config.yaml
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
|-- run_info.json
`-- rag_ingest_checkpoint.json
```

## Config로 바꾸는 주요 옵션

```yaml
rag:
  chunk:
    size: 500
    overlap: 80
  embedding:
    provider: local
    model_name: hashing-char-ngram-v1
  retriever:
    method: hybrid
    top_k: 3
  answerer:
    mode: extractive
    provider: local
  checkpoint:
    enabled: true
    resume: true

artifact_policy:
  run_id: run_001
  on_existing: overwrite

backup:
  enabled: true
  on_finish: true
  on_failure: true
```

## 주요 문서

| 문서 | 설명 |
| --- | --- |
| [RAG Pipeline Spec](docs/md/rag/RAG_PIPELINE_SPEC.md) | RAG 입력, chunk, 검색, 답변, 평가 계약 |
| [Pipeline Overview](docs/md/overview/PIPELINE_OVERVIEW.md) | 전체 실행 흐름과 산출물 구조 |
| [Module Architecture HTML](docs/html/overview/module_architecture.html) | 팀원 설명용 모듈 구조 다이어그램 |
| [Pipeline Explainer HTML](docs/html/overview/pipeline_explainer.html) | 비전공자도 이해하기 쉬운 파이프라인 설명 |
| [Experiment Guide](docs/md/experiments/EXPERIMENT_GUIDE.md) | 실험 실행과 결과 확인 방법 |
| [Colab Guide](docs/md/experiments/COLAB_GUIDE.md) | Colab/Drive 기반 실행 가이드 |
| [Kickoff HTML](docs/html/kickoff/kickoff.html) | 킥오프 설명용 HTML |
| [LLM 작업 문서](docs/llm/README.md) | LLM 기반 작업자가 먼저 읽을 압축 문맥과 체크리스트 |

## 노트북

- [로컬 실험 노트북](notebooks/local_experiment_template.ipynb)
- [Colab 실험 노트북](notebooks/colab_experiment_template.ipynb)

노트북에서는 config 선택, RAG 실행, metric 확인, 학습 곡선/평가 그래프 확인 흐름을 실습할 수 있습니다.

## 운영 원칙

- `data/raw`에는 원본 데이터를 둡니다.
- 모델이나 RAG가 바로 읽을 수 있는 최소 전처리 결과만 `processed` 계열에 둡니다.
- chunking, retriever, scheduler, checkpoint, backup 같은 실험 정책은 가능하면 config에서 조정합니다.
- 실험 결과에는 config, metric, status, 실행 환경 정보를 함께 남깁니다.
- smoke test는 최종 성능용이 아니라 파이프라인 검증용입니다.
