# Colab 실험 템플릿

실제 `.ipynb` 노트북을 만들 때 아래 순서를 셀 단위로 옮겨 사용합니다.
자세한 설명은 `docs/COLAB_GUIDE.md`를 기준으로 합니다.

## 1. Drive 연결

```python
from google.colab import drive
drive.mount("/content/drive")
```

## 2. 저장소 준비

```bash
git clone <repo-url>
cd <repo-name>
pip install -r requirements.txt
```

## 3. GPU 확인

```python
import torch

print(torch.__version__)
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU")
```

## 4. Smoke test

```bash
python scripts/run_validate.py --data-dir data/text_processed --project-root .
python scripts/run_train.py --config configs/smoke_test_text.yaml --project-root .
python scripts/run_train.py --config configs/smoke_test_hf_tiny.yaml --project-root .
```

## 5. Drive 데이터 학습

```bash
python scripts/run_validate.py \
  --project-root . \
  --data-dir /content/drive/MyDrive/codeit_ml_project/data/text_processed

python scripts/run_train.py \
  --project-root . \
  --config configs/exp002_hf_text_finetune_colab.yaml
```

## 6. 예측 확인

```bash
python scripts/run_predict.py \
  --project-root . \
  --config configs/exp002_hf_text_finetune_colab.yaml \
  --input /content/drive/MyDrive/codeit_ml_project/data/text_processed/sample_positive.txt
```

## 7. 실험 요약

```bash
python scripts/summarize_experiments.py \
  --project-root . \
  --experiments-dir /content/drive/MyDrive/codeit_ml_project/experiments \
  --output /content/drive/MyDrive/codeit_ml_project/reports/experiment_summary.csv
```

## 체크리스트

- Drive에 데이터가 올라가 있는지 확인
- config의 `experiment.name`, `output_dir`, `backup_dir` 확인
- smoke test 통과 확인
- 학습 후 `metrics.json`, `history.csv`, `README.md`, `hf_model/` 확인
- 실험 README에 결론과 다음 액션 작성
