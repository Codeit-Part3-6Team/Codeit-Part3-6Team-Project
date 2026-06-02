# 테스트

초기 테스트는 `pytest` 기반으로 진행합니다.

```bash
conda activate codeit-ml-pipeline
pytest
```

직접 smoke test를 확인하고 싶을 때는 아래 명령을 사용합니다.

```bash
python src/validate_data.py --data-dir data/processed
python src/train.py --config configs/smoke_test.yaml --project-root .
python src/predict.py --config configs/smoke_test.yaml --project-root . --input data/processed/images/red_000.ppm

python src/validate_data.py --data-dir data/text_processed
python src/train.py --config configs/smoke_test_text.yaml --project-root .
python src/predict.py --config configs/smoke_test_text.yaml --project-root . --input data/text_processed/sample_positive.txt
```
