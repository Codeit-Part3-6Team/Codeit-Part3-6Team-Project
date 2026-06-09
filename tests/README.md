# 테스트

초기 테스트는 `pytest` 기반으로 진행합니다.

```bash
conda activate codeit-ml-pipeline
pytest
```

직접 smoke test를 확인하고 싶을 때는 아래 명령을 사용합니다.

```bash
python scripts/run_validate.py --data-dir data/processed
python scripts/run_train.py --config configs/smoke_test.yaml --project-root .
python scripts/run_predict.py --config configs/smoke_test.yaml --project-root . --input data/processed/images/red_000.ppm

python scripts/run_validate.py --data-dir data/text_processed
python scripts/run_train.py --config configs/smoke_test_text.yaml --project-root .
python scripts/run_predict.py --config configs/smoke_test_text.yaml --project-root . --input data/text_processed/sample_positive.txt
```

RAG 문서 loader 테스트는 외부 파일 없이 zip/xml 기반 DOCX/HWPX 샘플을 즉석에서 만들어 검증합니다.
