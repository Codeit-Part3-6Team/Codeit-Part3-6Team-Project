# 실험 가이드

모든 실험은 config 기반으로 실행하고, 재현 가능한 산출물을 남깁니다.

## 기본 실행 흐름

1. 데이터가 Data Contract를 만족하는지 확인합니다.
2. smoke test config로 파이프라인이 정상 동작하는지 확인합니다.
3. 실제 실험 config를 만들어 train/predict를 실행합니다.
4. metrics, history, README를 보고 다음 실험 방향을 기록합니다.

```bash
python scripts/run_validate.py --data-dir data/text_processed
python scripts/run_train.py --config configs/smoke_test_text.yaml --project-root .
python scripts/run_predict.py --config configs/smoke_test_text.yaml --project-root . --input data/text_processed/sample_positive.txt
```

## HuggingFace 실험

HuggingFace 모델은 `configs/exp002_hf_text_finetune.yaml`을 시작점으로 사용합니다.

```bash
python scripts/run_train.py --config configs/exp002_hf_text_finetune.yaml --project-root .
```

처음 실행할 때는 base model 다운로드가 필요합니다. 로컬 CPU에서도 동작은 가능하지만, 실제 데이터셋에서는 Colab/GPU 환경을 권장합니다.

## 필수 산출물

```text
experiments/{experiment_name}/
|-- config.yaml
|-- metrics.json
|-- history.csv
|-- run_info.json
|-- README.md
`-- best_model.json
```

HuggingFace 실험은 추가로 다음 폴더를 생성합니다.

```text
experiments/{experiment_name}/hf_model/
```

## 실험 로그 컬럼

```text
exp_id, owner, date, config, model, data_version, metric, result_path, notes
```

## 규칙

- 학습 전에 data validation을 통과시킵니다.
- 큰 실험 전에 smoke test를 먼저 통과시킵니다.
- 가능하면 한 실험에서는 주요 변경점을 하나만 둡니다.
- 성공한 실험과 실패한 실험을 모두 기록합니다.
- validation/test/predict transform은 결정적으로 동작해야 합니다.
- HuggingFace base model, max length, batch size, learning rate는 config에 남깁니다.
