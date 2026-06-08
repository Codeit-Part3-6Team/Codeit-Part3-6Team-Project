# ML 프로젝트 파이프라인 스캐폴드

코드잇 스프린트 중급 프로젝트를 시작하기 전에 작업 방식과 ML 파이프라인을 미리 검증하기 위한 기본 구조입니다.
목표는 높은 성능의 모델을 바로 만드는 것이 아니라, 데이터 계약 검증부터 config 기반 실험, 산출물 저장, 역할별 작업 흐름까지 재현 가능한 뼈대를 만드는 것입니다.

## 프로젝트 구조

```text
.
|-- app/                       # 데모 앱/API 연동 후보 영역
|-- configs/                   # 실험 및 전처리 설정
|-- data/
|   |-- raw/                   # 원본 데이터
|   |-- interim/               # 중간 처리 데이터
|   `-- processed/             # Data Contract를 만족하는 모델 입력 데이터
|-- docs/                      # 운영 문서와 역할 가이드
|-- experiments/               # 실험 결과 자동 저장
|-- models/                    # 공유용 모델 artifact 후보
|-- notebooks/                 # Colab/로컬 실험 템플릿
|-- reports/                   # Daily report와 실험 로그
|-- scripts/                   # 팀원이 실행하는 공식 진입점
|-- src/                       # 파이프라인 소스 코드
`-- tests/                     # 가벼운 검증 테스트
```

## 환경 세팅

```bash
conda env create -f environment.yml
conda activate codeit-ml-pipeline
```

또는 이미 환경이 있다면:

```bash
pip install -r requirements.txt
```

## Smoke Test

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

## HuggingFace Fine-Tuning 예시

HuggingFace 실험은 처음 실행할 때 base model을 내려받기 때문에 인터넷 연결이 필요합니다. 실제 프로젝트 데이터에서는 Colab/GPU 환경 사용을 권장합니다.

환경이 HuggingFace 모델까지 실제로 실행 가능한지 빠르게 확인하려면 작은 테스트 모델을 사용합니다. 이 config는 성능 검증용이 아니라 다운로드, 학습, 저장, 예측 흐름 확인용입니다.

```bash
python scripts/run_train.py --config configs/smoke_test_hf_tiny.yaml --project-root .
python scripts/run_predict.py --config configs/smoke_test_hf_tiny.yaml --project-root . --input data/text_processed/sample_positive.txt
```

실제 fine-tuning 후보 config:

```bash
python scripts/run_train.py --config configs/exp002_hf_text_finetune.yaml --project-root .
python scripts/run_predict.py --config configs/exp002_hf_text_finetune.yaml --project-root . --input data/text_processed/sample_positive.txt
```

base model은 config에서 바꿉니다.

```yaml
model:
  name: huggingface_sequence_classifier
  model_name: distilbert-base-multilingual-cased
```

한국어 데이터라면 `klue/bert-base`, `klue/roberta-base`, `beomi/KcELECTRA-base` 같은 모델을 후보로 검토할 수 있습니다.

## 실험 산출물

실험 결과는 `experiments/{experiment.name}/` 아래에 저장됩니다.

```text
experiments/smoke_test_text/
|-- best_model.json
|-- config.yaml
|-- history.csv
|-- metrics.json
|-- predictions.csv
|-- README.md
`-- run_info.json
```

HuggingFace 실험은 추가로 `hf_model/` 폴더에 tokenizer와 model weight를 저장합니다.

여러 실험을 비교하려면 요약 스크립트를 실행합니다.

```bash
python scripts/summarize_experiments.py --project-root .
```

기본 산출물은 `reports/experiment_summary.csv`와 `reports/experiment_summary.json`입니다.

## 운영 원칙

- `data/raw`는 원본 데이터로 둡니다.
- `data/processed`는 Data Contract를 만족하는 재생성 가능한 모델 입력 데이터로 봅니다.
- 공통 전처리는 여러 모델이 함께 쓸 수 있는 최소 표준 형태까지만 수행합니다.
- 학습 성능 개선용 증강/transform은 config와 train pipeline에서 관리합니다.
- valid/test/predict transform은 항상 결정적으로 동작해야 합니다.
- 모든 실험은 config, metrics, history, code version, artifact path를 남깁니다.
- 텍스트 프로젝트는 `keyword_text_classifier`로 smoke test를 먼저 통과시킨 뒤 HuggingFace 모델로 교체합니다.

## 코드 문서화 원칙

- public 함수와 클래스에는 역할을 설명하는 docstring을 남깁니다.
- 주석은 “무엇을 하는가”보다 “왜 이렇게 하는가”를 설명할 때 사용합니다.
- smoke model은 실제 성능 모델이 아니라 파이프라인 검증용임을 명확히 표시합니다.
- 실험 산출물은 팀원이 나중에 읽고 이어서 기록할 수 있는 형태로 남깁니다.

## 킥오프 문서

- `docs/PIPELINE_OVERVIEW.md`: 전체 파이프라인 설명 문서
- `docs/RAG_PIPELINE_SPEC.md`: RAG 전환을 위한 document/chunk/retrieval/answer 계약
- `docs/KICKOFF_GUIDE.md`: 수정하기 쉬운 Markdown 원본
- `docs/kickoff.html`: 팀원 공유/브리핑용 HTML 문서
- `docs/COLAB_GUIDE.md`: Colab/Drive 기반 실험 실행 가이드
- `docs/GIT_WORKFLOW.md`: 브랜치, 커밋, PR 운영 규칙
- `docs/TEAM_WORKFLOW.md`: Issue, Kanban, Daily Report 운영 가이드
