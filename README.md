# Codeit 중급 프로젝트 파이프라인

코드잇 스프린트 중급 프로젝트를 시작하기 전에, 팀이 공통으로 사용할 실험 파이프라인과 문서화 규칙을 미리 검증하기 위한 저장소입니다.

이 저장소의 목표는 “성능 좋은 모델 하나를 바로 만드는 것”보다 다음에 가깝습니다.

- 데이터 입력 형식과 산출물 형식을 먼저 고정합니다.
- config만 바꿔도 실험 조건을 바꿀 수 있게 만듭니다.
- 학습, 예측, RAG 문서 검색, 평가, 백업, checkpoint/resume 흐름을 한 번에 설명 가능한 구조로 둡니다.
- 팀원이 맡은 역할과 상관없이 `scripts/` 명령만 보고 같은 방식으로 실행할 수 있게 합니다.

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

## 프로젝트 구조

```text
.
|-- app/                 # 추후 웹앱/API 연결을 위한 예비 영역
|-- configs/             # 실험, RAG, artifact, backup, scheduler 설정
|-- data/                # raw/interim/processed/external 데이터 영역
|-- docs/
|   |-- md/              # 원본/관리용 Markdown 문서
|   `-- html/            # 공유/설명용 HTML 문서
|-- experiments/         # 실험 실행 결과가 저장되는 기본 위치
|-- models/              # 모델 구현체와 별도의 공유 artifact 예비 위치
|-- notebooks/           # 로컬/Colab 실험 노트북 템플릿
|-- reports/             # 실험 요약, Daily Report 템플릿
|-- scripts/             # 팀원이 직접 실행하는 공식 진입점
|-- src/                 # 파이프라인 실제 구현
`-- tests/               # 단위 테스트와 smoke test
```

모듈 구조를 한눈에 보고 싶다면 아래 문서를 먼저 보면 됩니다.

- [모듈 구조 설명 HTML](docs/html/module_architecture.html)
- [모듈 구조 설명 Markdown](docs/md/MODULE_ARCHITECTURE.md)

## 실행 흐름

이 프로젝트는 기본적으로 `config -> script -> src 구현체 -> experiments 산출물` 흐름으로 동작합니다.

1. `configs/*.yaml`에서 데이터 경로, 모델, RAG 옵션, checkpoint, backup 정책을 정합니다.
2. `scripts/*.py`를 실행합니다.
3. `src/` 하위 모듈이 config를 읽고 실제 작업을 수행합니다.
4. 결과는 `experiments/{experiment.name}/` 또는 config에 지정한 `paths.output_dir`에 저장됩니다.

## 분류 모델 Smoke Test

이미지 분류:

```bash
python scripts/run_validate.py --data-dir data/processed
python scripts/run_train.py --config configs/smoke_test.yaml --project-root .
python scripts/run_predict.py --config configs/smoke_test.yaml --project-root . --input data/processed/images/red_000.ppm
```

텍스트 분류:

```bash
python scripts/run_validate.py --data-dir data/text_processed
python scripts/run_train.py --config configs/smoke_test_text.yaml --project-root .
python scripts/run_predict.py --config configs/smoke_test_text.yaml --project-root . --input data/text_processed/sample_positive.txt
```

HuggingFace tiny 모델 smoke test:

```bash
python scripts/run_train.py --config configs/smoke_test_hf_tiny.yaml --project-root .
python scripts/run_predict.py --config configs/smoke_test_hf_tiny.yaml --project-root . --input data/text_processed/sample_positive.txt
```

## RAG Smoke Test

RAG는 문서 로딩, chunking, embedding, retrieval, answer, evaluation 흐름을 config 기반으로 검증합니다.

```bash
python scripts/run_rag_ingest.py --config configs/rag_smoke_test.yaml --project-root .
python scripts/check_rag_pipeline.py --config configs/rag_smoke_test.yaml --project-root .
python scripts/run_rag_retrieve.py --config configs/rag_smoke_test.yaml --project-root . --question "예산은 얼마야?"
python scripts/run_rag_chat.py --config configs/rag_smoke_test.yaml --project-root . --question "예산은 얼마야?"
python scripts/run_rag_chat.py --config configs/rag_smoke_test.yaml --project-root . --evaluate
python scripts/compare_rag_retrievers.py --project-root .
```

현재 RAG 구현체는 다음을 실제로 지원합니다.

- 문서 로더: `txt`, `pdf`, `docx`, `hwpx`, `hwp`
- embedding: local hashing, HuggingFace mean pooling
- retriever: keyword, semantic, hybrid
- answerer: local extractive answer
- checkpoint/resume: `parsed_documents.csv`, `chunks.csv`, `embeddings.jsonl` 단계 단위 재사용

FAISS, Chroma, Elasticsearch, reranker, OpenAI/HuggingFace LLM 답변은 config 계약과 검증 규칙을 먼저 잡아둔 상태이며, 실제 프로젝트 요구가 확정되면 adapter 구현체를 붙이면 됩니다.

## 실험 산출물

일반적인 실험 결과는 다음과 같은 형태로 저장됩니다.

```text
experiments/smoke_test_text/
|-- best_model.json
|-- config.yaml
|-- history.csv
|-- metrics.json
|-- predictions.csv
|-- README.md
|-- run_info.json
`-- run_status.json
```

HuggingFace 실험에서는 `hf_model/`과 checkpoint 디렉터리가 추가될 수 있습니다.

RAG 실험에서는 다음 산출물이 추가됩니다.

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
`-- rag_ingest_checkpoint.json
```

## Config로 조정하는 주요 기능

```yaml
artifact_policy:
  run_id: run_001
  on_existing: overwrite

checkpoint:
  enabled: true
  save_best: true
  save_last: true
  resume_from:

early_stopping:
  enabled: true
  patience: 3
  min_delta: 0.0

scheduler:
  enabled: true
  name: linear
  warmup_ratio: 0.1

backup:
  enabled: true
  on_finish: true
  on_failure: true
  include_logs: true
  include_checkpoints: true
```

RAG ingest resume:

```yaml
rag:
  checkpoint:
    enabled: true
    resume: true
```

이 resume은 현재 문서별 offset까지 추적하는 초세밀 resume이 아니라, 이미 만들어진 `parsed_documents.csv`, `chunks.csv`, `embeddings.jsonl`을 재사용하는 단계 단위 resume입니다.

## 운영 원칙

- `data/raw`에는 원본 데이터를 둡니다.
- `data/processed`에는 모델이 바로 읽을 수 있는 최소 전처리 결과를 둡니다.
- 증강, scheduler, early stopping, checkpoint, backup 같은 실험 정책은 가능하면 config에서 조정합니다.
- valid/test/predict 단계에는 랜덤 증강을 넣지 않습니다.
- 실험 결과에는 config, metric, history, status, 실행 환경 정보를 함께 남깁니다.
- smoke model은 최종 성능용이 아니라 파이프라인 검증용입니다.

## 문서

Markdown 문서는 `docs/md/`에, 공유용 HTML 문서는 `docs/html/`에 둡니다.
각 `docs/md/*.md` 문서는 같은 이름의 `docs/html/*.html` 파일을 가집니다.

관리용 Markdown:

- [docs/md/PIPELINE_OVERVIEW.md](docs/md/PIPELINE_OVERVIEW.md): 전체 파이프라인 설명
- [docs/md/PIPELINE_INFRA_CHECKLIST.md](docs/md/PIPELINE_INFRA_CHECKLIST.md): 현재 구현된 인프라 기능 점검표
- [docs/md/RAG_PIPELINE_SPEC.md](docs/md/RAG_PIPELINE_SPEC.md): RAG 문서, chunk, 검색, 답변 계약
- [docs/md/MODULE_ARCHITECTURE.md](docs/md/MODULE_ARCHITECTURE.md): 모듈 구조와 실행 흐름
- [docs/md/EXPERIMENT_GUIDE.md](docs/md/EXPERIMENT_GUIDE.md): 실험 실행 가이드
- [docs/md/COLAB_GUIDE.md](docs/md/COLAB_GUIDE.md): Colab/Drive 기반 실험 가이드
- [docs/md/GIT_WORKFLOW.md](docs/md/GIT_WORKFLOW.md): 브랜치, 커밋, PR 운영 규칙
- [docs/md/KICKOFF_GUIDE.md](docs/md/KICKOFF_GUIDE.md): 킥오프 설명용 Markdown

공유용 HTML:

- [docs/html/pipeline_explainer.html](docs/html/pipeline_explainer.html): 비전공자도 이해하기 쉬운 파이프라인 설명 HTML
- [docs/html/module_architecture.html](docs/html/module_architecture.html): 팀원 설명용 HTML 구조 문서
- [docs/html/kickoff.html](docs/html/kickoff.html): 킥오프 설명용 HTML
- [docs/html/PIPELINE_OVERVIEW.html](docs/html/PIPELINE_OVERVIEW.html): Markdown 원본에서 변환한 전체 파이프라인 HTML

Config:

- [configs/README.md](configs/README.md): config 옵션과 실험 변경 방법

노트북:

- [notebooks/local_experiment_template.ipynb](notebooks/local_experiment_template.ipynb): 로컬 Jupyter 실험 템플릿
- [notebooks/colab_experiment_template.ipynb](notebooks/colab_experiment_template.ipynb): Colab/Drive 실험 템플릿

## 코드 문서화 원칙

- public 함수와 클래스에는 “무엇을 담당하는지”가 드러나는 docstring을 둡니다.
- 주석은 코드가 하는 일을 반복하지 않고, 왜 이렇게 나뉘었는지와 어떤 산출물을 보장하는지 설명합니다.
- 팀원이 실험 결과 폴더만 봐도 재현 경로를 알 수 있도록 README, config, status, metric을 함께 저장합니다.
