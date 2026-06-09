# 실험 가이드

모든 실험은 config 기반으로 실행하고, 재현 가능한 산출물을 남깁니다.
전체 파이프라인의 큰 그림은 `docs/PIPELINE_OVERVIEW.md`를 먼저 참고합니다.

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
Colab에서 Drive 경로를 사용하려면 `docs/COLAB_GUIDE.md`와 `configs/exp002_hf_text_finetune_colab.yaml`을 참고합니다.

## 실험 결과 요약

여러 실험 결과를 한 번에 비교하려면 요약 스크립트를 실행합니다.

```bash
python scripts/summarize_experiments.py --project-root .
```

기본적으로 다음 파일이 생성됩니다.

```text
reports/experiment_summary.csv
reports/experiment_summary.json
```

## 필수 산출물

```text
experiments/{experiment_name}/
|-- config.yaml
|-- metrics.json
|-- history.csv
|-- run_info.json
|-- run_status.json
|-- README.md
`-- best_model.json
```

HuggingFace 실험은 추가로 다음 폴더를 생성합니다.

```text
experiments/{experiment_name}/hf_model/
```

실패한 학습/예측 실행은 같은 폴더에 `failure.log`를 남깁니다.
`run_status.json`의 `status`가 `failed`이면 이 파일에서 에러 타입, 메시지, traceback을 확인합니다.

## 실험 로그 컬럼

```text
exp_id, owner, date, config, model, data_version, metric, result_path, notes
```

## 실험 이름 규칙

실험명은 `exp번호_대상_핵심변경` 형태를 권장합니다.

```text
exp001_text_baseline
exp002_hf_text_finetune
exp003_hf_lr2e-5_max128
exp004_hf_roberta_max256
```

좋은 실험명은 이름만 봐도 무엇을 바꿨는지 대략 알 수 있어야 합니다.

## Artifact 정책

같은 실험명을 여러 번 실행해야 할 때는 config에서 `artifact_policy.run_id`를 지정합니다.

```yaml
artifact_policy:
  run_id: run_001
  on_existing: overwrite
```

이 경우 산출물은 아래처럼 저장됩니다.

```text
experiments/{experiment_name}/{run_id}/
```

기존 산출물을 실수로 덮어쓰고 싶지 않으면 `on_existing: fail`을 사용합니다.
이미 파일이 있는 output directory에 다시 실행하면 실행 전에 실패합니다.

## 규칙

- 학습 전에 data validation을 통과시킵니다.
- 큰 실험 전에 smoke test를 먼저 통과시킵니다.
- 가능하면 한 실험에서는 주요 변경점을 하나만 둡니다.
- 성공한 실험과 실패한 실험을 모두 기록합니다.
- validation/test/predict transform은 결정적으로 동작해야 합니다.
- HuggingFace base model, max length, batch size, learning rate는 config에 남깁니다.
- 실험 README의 결론, 다음 액션, 실패/주의 사항을 실험 직후에 적습니다.
## 백업 정책

실험 백업은 config의 `backup` 블록에서 조정합니다.

```yaml
backup:
  enabled: true
  on_finish: true
  on_failure: true
  include_logs: true
  include_checkpoints: true
```

- `on_finish`: 학습이 성공한 뒤 `backup_dir`로 산출물을 복사합니다.
- `on_failure`: 학습이 실패해도 `failure.log`, `run_status.json` 같은 원인 분석 파일을 복사합니다.
- `include_logs`: `false`면 `*.log` 파일을 백업에서 제외합니다.
- `include_checkpoints`: `false`면 `hf_model/`, `checkpoints/`, `*.pt`, `*.ckpt` 같은 큰 모델 산출물을 제외합니다.

`backup.on_best`는 백업 시점 정책이고, 모델 저장 기준은 아래 `checkpoint.save_best`에서 제어합니다.
현재 HuggingFace 학습 루프는 monitor metric이 개선될 때 `checkpoints/best`를 저장합니다.

## 학습 제어 정책

HuggingFace fine-tuning은 아래 config 블록을 실제 학습 루프에 반영합니다.
일반 smoke 모델은 같은 config 계약을 갖지만, 현재는 빠른 파이프라인 검증용이라 checkpoint/scheduler를 적용하지 않습니다.

```yaml
checkpoint:
  enabled: true
  dir: checkpoints
  save_best: true
  save_last: true
  save_every_epoch: false
  resume_from:

early_stopping:
  enabled: true
  patience: 3
  min_delta: 0.0

scheduler:
  enabled: true
  name: linear
  warmup_ratio: 0.1
  warmup_steps:
```

- `checkpoint.save_best`: monitor metric이 개선될 때 `checkpoints/best`를 저장합니다.
- `checkpoint.save_last`: 매 epoch 후 `checkpoints/last`를 저장합니다.
- `checkpoint.resume_from`: 이전 checkpoint 디렉터리를 지정해 optimizer/scheduler 상태까지 복원합니다.
- `early_stopping`: monitor metric 개선이 `patience`만큼 멈추면 학습을 종료합니다.
- `scheduler`: HuggingFace `get_scheduler`를 사용해 learning rate schedule을 적용합니다.
