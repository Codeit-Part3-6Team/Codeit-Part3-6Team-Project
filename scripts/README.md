# 실행 스크립트

팀원이 직접 실행하는 공식 진입점입니다.
`src/`는 재사용 가능한 내부 로직이고, `scripts/`는 사람이 실행하는 명령어라고 생각하면 됩니다.

```bash
python scripts/run_validate.py --data-dir data/text_processed
python scripts/run_train.py --config configs/smoke_test_text.yaml --project-root .
python scripts/run_predict.py --config configs/smoke_test_text.yaml --project-root . --input data/text_processed/sample_positive.txt
```

실험 결과는 config의 `paths.output_dir`에 따라 `experiments/{experiment_name}/` 아래에 저장됩니다.

