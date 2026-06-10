# 역할 가이드

킥오프에서는 역할명을 짧고 기억하기 쉽게 사용합니다.
각 역할은 직책이라기보다 “주 책임 구역”입니다.
필요하면 서로 도와도 되지만, 아래 산출물은 해당 역할이 책임지고 정리합니다.

## 5명 팀 역할 선택

처음에는 웹앱/데모 담당을 지원받아 봅니다.
맡고 싶은 팀원이 있으면 A안으로 가고, 없다면 B안으로 조정합니다.

```text
A안: 웹앱/데모 시도
PM / Data Engineer / Experiment Lead / Application Engineer / Presentation Lead

B안: 모델/실험 강화
PM / Data Engineer / Model Engineer / Experiment Lead / Presentation Lead
```

Application Engineer는 필수 역할이 아니라 선택형 역할입니다.
웹앱 담당이 없거나 일정이 촉박하면 Colab Demo Notebook과 결과 시각화로 데모 범위를 낮추고, 모델 구현과 실험 관리를 분리합니다.

## PM

- 프로젝트 목표, 범위, 일정, 통합 기준, 리스크를 관리합니다.
- Data Contract, 모델 입출력, 평가 지표, config, logging 같은 공통 기준을 정리합니다.
- 팀원이 바로 실행할 수 있는 공통 파이프라인과 더미 실행 구조를 준비합니다.
- 막힌 역할이 있으면 일정과 업무량을 조정합니다.

주요 산출물:

- 운영 기준
- 일정과 마일스톤
- 역할 분담표
- 결정사항 기록
- 통합 체크리스트

## Data Engineer

- raw 데이터를 모델이 사용할 수 있는 processed data로 정리합니다.
- EDA, 데이터 품질 이슈, split 파일, `class_map.json`, `dataset_info.json`을 책임집니다.
- 모델 실험이나 데모 동작에 영향을 줄 수 있는 데이터 이슈를 기록합니다.

주요 산출물:

- `train.csv`
- `valid.csv`
- `test.csv`
- `class_map.json`
- `dataset_info.json`
- 데이터 이슈/품질 분석

## Experiment Lead

- 모델 후보를 선정하고 성능 개선 실험을 제안합니다.
- config 기반으로 실험을 실행하고 결과를 비교/기록합니다.
- 최종 모델 선정 근거, artifact 경로, 추론 입출력 스펙을 정리합니다.
- A안에서는 모델 구현과 실험 운영을 함께 담당합니다.

주요 산출물:

- 모델 코드
- 실험 config
- metrics/history
- 최종 모델 파일
- 실험 해석과 모델 선정 근거

## Application Engineer

- 모델 결과를 사용자가 확인할 수 있는 데모 흐름을 만듭니다.
- 기본 산출물은 Colab Demo Notebook입니다.
- 시간이 되면 Gradio, Streamlit, 간단한 웹앱, FastAPI 등 팀 역량에 맞는 방식을 선택합니다.
- 필수 범위는 아니므로, 담당자가 없으면 B안으로 전환합니다.

주요 산출물:

- Demo notebook 또는 demo application
- 입력/출력 예시
- 실행 가이드
- 화면 캡처
- 모델 연동 메모

## Model Engineer

- B안에서 사용하는 역할입니다.
- 모델 구조 구현, HuggingFace 모델 연결, 학습 코드 수정 등 모델 구현 자체를 더 집중해서 담당합니다.
- Experiment Lead와 협업해 config와 실험 결과를 맞춥니다.

주요 산출물:

- 모델 구현 코드
- 모델 registry 등록
- 모델 입력/출력 스펙
- 학습/추론 연결 메모

## Presentation Lead

- 최종 보고서와 발표 흐름을 구조화합니다.
- 각 역할 담당자가 작성한 근거와 산출물을 취합해 하나의 스토리로 편집합니다.
- 모든 문서를 혼자 작성하는 역할이 아닙니다.
- 각 담당자는 자기 파트 설명을 직접 남기고, Presentation Lead는 이를 정리합니다.

주요 산출물:

- 최종 보고서
- 발표자료
- 발표 대본
- 리허설 체크리스트
- 파트별 누락 자료 요청 목록

## 역할 간 연결 지점

```text
Data Engineer -> Experiment Lead:
processed data, dataset_info, class_map, known issues

Experiment Lead -> Application Engineer:
model artifact, inference function, input/output spec

Experiment Lead -> Presentation Lead:
experiment log, metrics, final model rationale

Application Engineer -> Presentation Lead:
demo flow, screenshots, usage guide

PM -> 전체:
schedule, GitHub rules, integration criteria, blockers
```

