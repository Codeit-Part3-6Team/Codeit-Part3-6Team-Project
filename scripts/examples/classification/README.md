# Classification Scripts

이 디렉터리는 기존 분류/HuggingFace 파이프라인을 검증하기 위한 참고용 script를 둡니다.

현재 RAG 프로젝트의 공식 실행 경로는 아닙니다.

```bash
python scripts/examples/classification/run_validate.py --data-dir data/examples/classification/text_processed
python scripts/examples/classification/run_train.py --config configs/examples/classification/smoke_test_text.yaml --project-root .
python scripts/examples/classification/run_predict.py --config configs/examples/classification/smoke_test_text.yaml --project-root . --input data/examples/classification/text_processed/sample_positive.txt
```
