# 실행 스크립트

팀원이 직접 실행하는 공식 진입점입니다.
`src/`는 재사용 가능한 파이프라인 로직이고, `scripts/`는 사람이 실행하는 명령이라고 보면 됩니다.

## 가벼운 텍스트 smoke test

```bash
python scripts/run_validate.py --data-dir data/text_processed
python scripts/run_train.py --config configs/smoke_test_text.yaml --project-root .
python scripts/run_predict.py --config configs/smoke_test_text.yaml --project-root . --input data/text_processed/sample_positive.txt
```

## HuggingFace fine-tuning 예시

처음 실행할 때는 base model을 내려받기 때문에 인터넷 연결이 필요합니다. CPU에서도 실행은 가능하지만, 실제 프로젝트 데이터에서는 GPU/Colab 사용을 권장합니다.

```bash
python scripts/run_train.py --config configs/exp002_hf_text_finetune.yaml --project-root .
python scripts/run_predict.py --config configs/exp002_hf_text_finetune.yaml --project-root . --input data/text_processed/sample_positive.txt
```

실험 결과는 config의 `paths.output_dir`에 따라 `experiments/{experiment_name}/` 아래에 저장됩니다.
