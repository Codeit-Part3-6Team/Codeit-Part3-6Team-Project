# Experiment Configs

`configs/experiments/`는 실제 실험 후보 config를 둡니다.

- `exp001_baseline.yaml`: 이미지 baseline 후보
- `exp001_text_baseline.yaml`: 텍스트 baseline 후보
- `exp002_hf_text_finetune.yaml`: HuggingFace fine-tuning 후보
- `exp002_hf_text_finetune_colab.yaml`: Colab/Drive 실행용 HuggingFace 후보

새 실험을 만들 때는 기존 config를 복사하고 `experiment.name`, `paths.output_dir`, `artifact_policy.run_id`를 먼저 바꿉니다.
