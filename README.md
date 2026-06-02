# ML 프로젝트 파이프라인 스캐폴드

코드잇 스프린트 중급 프로젝트를 시작하기 전에 협업 방식과 ML 파이프라인을 먼저 검증하기 위한 기본 구조입니다.
첫 목표는 높은 성능이 아니라, 데이터 계약 검증부터 config 기반 실험, 산출물 저장, 역할별 협업 흐름까지 한 번에 이어지는 재현 가능한 뼈대를 만드는 것입니다.

## 프로젝트 구조

```text
.
|-- app/                       # 데모 앱/API 연동 영역
|-- configs/                   # 실험 및 전처리 설정
|-- data/
|   |-- raw/                   # 원본 데이터, 직접 수정 금지
|   |-- interim/               # 중간 전처리 산출물
|   `-- processed/             # Data Contract를 만족하는 모델 입력 데이터
|-- docs/                      # 운영 문서와 역할 가이드
|-- models/                    # 학습된 weight 등 로컬 모델 artifact
|-- notebooks/                 # Colab/로컬 실험 템플릿
|-- reports/                   # 데일리 리포트와 실험 로그
|-- scripts/                   # 유틸리티 스크립트
|-- src/                       # 파이프라인 소스 코드
`-- tests/                     # 가벼운 검증 명령/테스트
```

## 첫 Smoke Test

conda 환경 생성:

```bash
conda env create -f environment.yml
conda activate codeit-ml-pipeline
```

현재 스캐폴드는 외부 ML 패키지 없이도 흐름을 검증할 수 있도록 작은 ASCII PPM 이미지를 사용합니다.

```bash
python scripts/run_validate.py --data-dir data/processed
python scripts/run_train.py --config configs/smoke_test.yaml --project-root .
python scripts/run_predict.py --config configs/smoke_test.yaml --project-root . --input data/processed/images/red_000.ppm
```

텍스트 분류 smoke test:

```bash
python scripts/run_validate.py --data-dir data/text_processed
python scripts/run_train.py --config configs/smoke_test_text.yaml --project-root .
python scripts/run_predict.py --config configs/smoke_test_text.yaml --project-root . --input data/text_processed/sample_positive.txt
```

예상 산출물:

```text
experiments/smoke_test/
|-- best_model.json
|-- config.yaml
|-- history.csv
|-- metrics.json
|-- predictions.csv
|-- README.md
`-- run_info.json
```

## 운영 원칙

- `data/raw`는 정본 데이터로 둔다.
- `data/processed`는 Data Contract를 만족하는 재생성 가능한 캐시로 본다.
- 공통 전처리는 여러 모델이 읽을 수 있는 최소 표준 형태까지만 수행한다.
- 학습용 증강과 모델별 transform은 config와 파이프라인 코드에서 관리한다.
- valid/test/predict transform은 항상 결정적으로 동작해야 한다.
- 모든 실험은 config, metrics, history, code version, artifact path를 남긴다.
- 모델 구현 코드는 `src/models/`에 두고, 학습된 weight나 큰 모델 파일은 `models/` 또는 실험 폴더에 둔다.
- 공통 로깅, 경로 처리, seed 설정은 `src/utils/`에 모아둔다.
- 텍스트 프로젝트는 `keyword_text_classifier`로 smoke test를 먼저 통과시킨 뒤 HuggingFace 모델로 교체한다.

## 킥오프 문서

팀원에게 처음 공유할 브리핑 문서는 아래 두 파일로 관리합니다.

- `docs/KICKOFF_GUIDE.md`: 수정하기 쉬운 Markdown 원본
- `docs/kickoff.html`: 공유/브리핑용 HTML 문서

## 역할 간 인터페이스

```text
PM -> 전체: 일정, Issue/PR 규칙, 통합 기준
Data Engineer -> Experiment Lead: processed data, dataset_info, class_map, known issues
Experiment Lead -> Application Engineer: model artifact, inference function, input/output spec
Experiment Lead -> Presentation Lead: experiment log, final model rationale
Application Engineer -> Presentation Lead: demo flow, screenshots, API usage notes
Presentation Lead -> 전체: 최종 스토리, 부족한 근거 요청
```
