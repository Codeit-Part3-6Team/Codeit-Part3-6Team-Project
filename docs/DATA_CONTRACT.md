# Data Contract v1.0

processed dataset은 공통 학습/예측 파이프라인이 바로 읽을 수 있어야 합니다.

## 필수 구조

```text
data/processed/
|-- train.csv
|-- valid.csv
|-- test.csv
|-- class_map.json
|-- dataset_info.json
`-- images/
```

## CSV 컬럼

이미지 분류:

```csv
image_path,label
images/img_000001.jpg,cat
images/img_000002.jpg,dog
```

텍스트 분류:

```csv
text,label
이 영화는 재미있다,positive
이 앱은 자주 멈춘다,negative
```

## 검증 규칙

- `train.csv`, `valid.csv`, `test.csv`가 존재한다.
- 이미지 분류는 `image_path`, `label` 컬럼이 존재한다.
- 텍스트 분류는 `text`, `label` 컬럼이 존재한다.
- 이미지 분류에서는 CSV가 참조하는 파일이 실제로 존재한다.
- 모든 label은 `class_map.json`에 정의되어 있다.
- 같은 sample path가 여러 split에 동시에 들어가지 않는다.
- `dataset_info.json`에 dataset version과 contract version을 기록한다.

실행:

```bash
python scripts/run_validate.py --data-dir data/processed
```

## 변경 규칙

Data Contract를 바꿀 때는 아래 내용을 기록합니다.

- 무엇이 바뀌었는가
- 왜 바뀌었는가
- 어떤 역할이 영향을 받는가
- 기존 실험과 비교 가능한가
