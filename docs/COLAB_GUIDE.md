# Colab / Drive 실행 가이드

이 문서는 팀원이 로컬 환경 세팅에 막혔을 때 Colab에서 같은 파이프라인을 실행하기 위한 가이드입니다.

## 권장 Drive 구조

```text
MyDrive/codeit_ml_project/
|-- data/
|   `-- text_processed/
|       |-- train.csv
|       |-- valid.csv
|       |-- test.csv
|       |-- class_map.json
|       `-- dataset_info.json
|-- experiments/
`-- backups/
```

## Colab 시작 셀

```python
from google.colab import drive
drive.mount("/content/drive")
```

```bash
git clone <repo-url>
cd <repo-name>
pip install -r requirements.txt
```

## 가벼운 환경 확인

GPU가 잡혔는지 먼저 확인합니다.

```python
import torch

print(torch.__version__)
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU")
```

HuggingFace까지 실제로 실행 가능한지 확인합니다.

```bash
python scripts/run_train.py --config configs/smoke_test_hf_tiny.yaml --project-root .
python scripts/run_predict.py --config configs/smoke_test_hf_tiny.yaml --project-root . --input data/text_processed/sample_positive.txt
```

## Drive 데이터로 학습하기

Drive에 `text_processed` 데이터를 올려둔 뒤 Colab 전용 config를 사용합니다.

```bash
python scripts/run_validate.py \
  --project-root . \
  --data-dir /content/drive/MyDrive/codeit_ml_project/data/text_processed

python scripts/run_train.py \
  --project-root . \
  --config configs/exp002_hf_text_finetune_colab.yaml
```

이 config는 결과를 Drive에 바로 저장합니다.

```text
/content/drive/MyDrive/codeit_ml_project/experiments/exp002_hf_text_finetune_colab
```

`backup.enabled: true`이므로 학습 종료 후 backup 경로에도 산출물이 복사됩니다.

```text
/content/drive/MyDrive/codeit_ml_project/backups/exp002_hf_text_finetune_colab
```

## 실험 요약

로컬 repo 안의 `experiments/`를 요약하려면:

```bash
python scripts/summarize_experiments.py --project-root .
```

Drive 경로에 저장한 실험을 요약하려면:

```bash
python scripts/summarize_experiments.py \
  --project-root . \
  --experiments-dir /content/drive/MyDrive/codeit_ml_project/experiments \
  --output /content/drive/MyDrive/codeit_ml_project/reports/experiment_summary.csv
```

## 운영 팁

- Colab 런타임이 끊길 수 있으니 실험 결과는 Drive 경로에 저장합니다.
- smoke test는 `smoke_test_hf_tiny.yaml`로 먼저 확인합니다.
- 실제 실험은 config를 복사해서 `experiment.name`, `output_dir`, `backup_dir`를 바꾼 뒤 실행합니다.
- 팀 공유 전에는 `reports/experiment_summary.csv`와 각 실험 README의 결론/다음 액션을 확인합니다.
## 백업 옵션

`backup.on_failure: true`를 켜두면 학습이 실패해도 `failure.log`와 `run_status.json`을
Drive에 남길 수 있어서 Colab 런타임이 끊기거나 에러가 났을 때 원인 확인이 쉽습니다.

용량을 줄이고 싶으면 config에서 `include_checkpoints: false`로 두어 모델 weight 계열 산출물을
백업에서 제외할 수 있습니다. 로그가 필요 없으면 `include_logs: false`도 사용할 수 있습니다.
