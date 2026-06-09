# 파이프라인 설명서

이 문서는 팀원에게 현재 프로젝트 파이프라인을 설명하기 위한 개요 문서입니다.
세부 명령어는 `README.md`, 실험 규칙은 `docs/EXPERIMENT_GUIDE.md`, Colab 실행은 `docs/COLAB_GUIDE.md`를 참고합니다.
운영 기능의 현재 상태와 남은 보강 항목은 `docs/PIPELINE_INFRA_CHECKLIST.md`에서 관리합니다.

## 한 줄 요약

현재 파이프라인은 **config 하나를 기준으로 데이터 검증, 학습, 예측, 실험 산출물 저장, 실험 요약까지 재현 가능하게 실행하는 구조**입니다.

```text
config
  -> data validation
  -> train
  -> predict
  -> experiment artifacts
  -> experiment summary
```

## 왜 이렇게 나누는가

팀 프로젝트에서는 “내 컴퓨터에서는 됐는데 다른 사람은 안 됨”이 자주 생깁니다.
그래서 실행 방식과 산출물 위치를 고정해두면 다음 장점이 있습니다.

- 팀원이 같은 명령어로 같은 흐름을 실행할 수 있습니다.
- 실험 결과가 흩어지지 않고 `experiments/` 아래에 모입니다.
- 모델, 데이터, metric, 실행 환경을 나중에 다시 확인할 수 있습니다.
- 발표 자료를 만들 때 실험 근거를 찾기 쉬워집니다.

## 주요 폴더 역할

```text
configs/      실험 설정 파일
data/         원본/중간/처리 데이터
scripts/      사람이 직접 실행하는 명령어 진입점
src/          재사용 가능한 파이프라인 코드
experiments/  실험 결과 자동 저장 위치
reports/      실험 요약과 Daily Report
docs/         팀 운영 및 파이프라인 문서
tests/        파이프라인이 깨졌는지 확인하는 테스트
```

## Config 중심 실행

실험은 config에서 시작합니다.

예시:

```yaml
experiment:
  name: smoke_test_text
  seed: 42

paths:
  data_dir: data/text_processed
  output_dir: experiments/smoke_test_text

data:
  task: text_classification
  train_csv: train.csv
  valid_csv: valid.csv
  test_csv: test.csv

model:
  name: keyword_text_classifier
```

config에는 다음 정보가 들어갑니다.

- 어떤 데이터를 쓸지
- 어떤 모델을 쓸지
- 결과를 어디에 저장할지
- 어떤 metric을 기준으로 볼지
- seed, batch size, learning rate 같은 실험 조건

## 실행 단계

### 1. 데이터 검증

```bash
python scripts/run_validate.py --data-dir data/text_processed --project-root .
```

확인하는 것:

- `train.csv`, `valid.csv`, `test.csv`가 있는지
- 필수 컬럼이 있는지
- label이 `class_map.json`에 정의되어 있는지
- split 간 중복이나 누락이 없는지

### 2. 학습

```bash
python scripts/run_train.py --config configs/smoke_test_text.yaml --project-root .
```

학습 단계에서 하는 일:

- config 로드
- 데이터 검증
- 데이터 로드
- 모델 생성
- 학습 실행
- valid/test metric 계산
- 산출물 저장

### 3. 예측

```bash
python scripts/run_predict.py \
  --config configs/smoke_test_text.yaml \
  --project-root . \
  --input data/text_processed/sample_positive.txt
```

예측 단계에서 하는 일:

- 실험 폴더의 `best_model.json` 또는 모델 artifact 로드
- 입력 데이터 전처리
- prediction 생성
- `predictions.csv` 저장

### 4. 실험 요약

```bash
python scripts/summarize_experiments.py --project-root .
```

여러 실험의 `metrics.json`, `config.yaml`, `run_info.json`을 모아 다음 파일을 만듭니다.

```text
reports/experiment_summary.csv
reports/experiment_summary.json
```

## 실험 산출물

각 실험은 `experiments/{experiment.name}/` 아래에 저장됩니다.

```text
experiments/smoke_test_text/
|-- best_model.json
|-- config.yaml
|-- history.csv
|-- metrics.json
|-- predictions.csv
|-- README.md
|-- run_info.json
`-- train.log
```

HuggingFace 실험은 추가로 다음 폴더를 만듭니다.

```text
experiments/{experiment.name}/hf_model/
```

## Smoke Test와 실제 실험

현재 파이프라인에는 두 종류의 실험이 있습니다.

```text
smoke test: 파이프라인이 정상 동작하는지 빠르게 확인
real experiment: 실제 모델 성능을 확인하는 실험
```

예시:

- `configs/smoke_test_text.yaml`: 빠른 텍스트 smoke test
- `configs/smoke_test_hf_tiny.yaml`: HuggingFace 환경 smoke test
- `configs/exp002_hf_text_finetune.yaml`: 실제 HuggingFace 실험 후보
- `configs/rag_smoke_test.yaml`: RAG 문서 검색/답변 smoke test

`smoke_test_hf_tiny.yaml`은 성능을 보기 위한 config가 아닙니다.
다운로드, 학습, 저장, 예측 흐름이 실제로 도는지 확인하기 위한 config입니다.

## RAG 프로젝트로 바뀌면 무엇이 달라지는가

RAG 프로젝트로 방향이 바뀌어도 가운데 운영 구조는 유지할 수 있습니다.
구체적인 RAG 입력/출력 계약은 `docs/RAG_PIPELINE_SPEC.md`에서 관리합니다.

그대로 쓰는 것:

- `configs/`
- `scripts/`
- `experiments/`
- `reports/`
- `docs/`
- `tests/`
- 실험 요약 방식
- Colab/Drive 실행 방식

바뀌는 것:

```text
분류 프로젝트:
text -> model -> predicted_label

RAG 프로젝트:
document -> chunk -> embedding -> retrieve -> answer + citations
```

즉, 파이프라인의 앞단과 뒷단은 바뀌지만 “config로 실행하고, 실험 산출물을 남기고, 결과를 요약한다”는 운영 구조는 그대로 가져갈 수 있습니다.

현재 RAG smoke pipeline은 외부 모델 없이 hashing embedding 기반 semantic retrieval로 구현되어 있습니다.
loader는 `txt`, `pdf`, `docx`, `hwpx`, `hwp` 확장자를 대상으로 하며, 형식이 달라도 같은 document/chunk 계약으로 변환합니다.
목표는 성능이 아니라 다음 항목을 빠르게 검증하는 것입니다.

- txt 문서를 section 단위로 읽을 수 있는가
- chunk metadata가 유지되는가
- embedding 산출물이 저장되는가
- 질문에 맞는 chunk를 top-k로 찾을 수 있는가
- 답변에 citation을 붙일 수 있는가
- `metrics.json`과 `evaluation_results.csv`를 남길 수 있는가
- 실험 요약에서 RAG metric을 볼 수 있는가

RAG smoke 산출물:

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
`-- metrics.json
```

다음 확장 후보는 `sentence-transformers embedding -> vector index -> semantic retrieval 고도화`입니다.
현재는 `scripts/compare_rag_retrievers.py`로 keyword와 semantic retriever 결과를 비교할 수 있습니다.

## 아직 보강하면 좋은 부분

현재 파이프라인은 기본 실행과 실험 기록 중심입니다.
실제 프로젝트에서 더 단단하게 만들려면 다음 항목을 추가할 수 있습니다.

- macro f1, class별 precision/recall/f1
- confusion matrix
- `eval_predictions.csv`
- `wrong_predictions.csv`
- best model과 last model 구분
- config validation
- 실패한 실험의 `failure.log`
- RAG embedding/vector store
- RAG PDF parser
- RAG unsupported answer 분석 리포트

이 항목들은 프로젝트 주제가 확정된 뒤 우선순위를 정해 추가하는 것이 좋습니다.
