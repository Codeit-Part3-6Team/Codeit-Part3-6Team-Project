# Smoke Test Configs

`configs/smoke/`는 파이프라인이 빠르게 도는지 확인하는 작은 실험 config를 둡니다.

- `smoke_test.yaml`: 이미지 분류 smoke test
- `smoke_test_text.yaml`: 텍스트 분류 smoke test
- `smoke_test_hf_tiny.yaml`: HuggingFace tiny 모델 smoke test

성능을 보기 위한 config가 아니라, 데이터 로딩부터 산출물 저장까지 전체 흐름이 깨지지 않는지 확인하는 용도입니다.
