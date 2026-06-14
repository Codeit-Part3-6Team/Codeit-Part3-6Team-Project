# Classification Example Configs

`configs/examples/classification/`는 분류 모델, HuggingFace fine-tuning, 예전 smoke/preprocess 예제 config를 둡니다.

- `exp001_baseline.yaml`: 이미지 분류 baseline 예시
- `exp001_text_baseline.yaml`: 텍스트 분류 baseline 예시
- `exp002_hf_text_finetune.yaml`: HuggingFace text classification fine-tuning 예시
- `exp002_hf_text_finetune_colab.yaml`: Colab/Drive 경로를 사용하는 HuggingFace 예시
- `smoke_test.yaml`: 이미지 분류 smoke test 예시
- `smoke_test_text.yaml`: 텍스트 분류 smoke test 예시
- `smoke_test_hf_tiny.yaml`: tiny HuggingFace smoke test 예시
- `preprocess_v1.yaml`: 예전 분류 데이터 전처리 규칙 예시

이 파일들은 RAG 프로젝트의 메인 실험 config가 아니라, 모델 학습 파이프라인을 설명하거나 테스트할 때 사용하는 참고 자료입니다.
