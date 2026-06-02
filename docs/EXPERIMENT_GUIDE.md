# 실험 가이드

모든 실험은 config 기반으로 실행하고, 재현 가능한 산출물을 남깁니다.

## 필수 산출물

```text
experiments/{experiment_name}/
|-- config.yaml
|-- metrics.json
|-- history.csv
|-- run_info.json
|-- README.md
`-- best_model.*
```

## 실험 로그 컬럼

```text
exp_id, owner, date, config, model, data_version, metric, result_path, notes
```

## 규칙

- 학습 전에 data validation을 통과한다.
- 긴 실험 전에 smoke test를 먼저 통과한다.
- 가능하면 한 실험에서 주요 변경점은 하나만 둔다.
- 성공한 실험과 실패한 실험을 모두 기록한다.
- validation/test/predict transform은 결정적으로 동작해야 한다.
