# Colab 실험 템플릿

실제 `.ipynb` 노트북을 만들 때 아래 흐름을 체크리스트로 사용합니다.

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

## 3. Smoke test

```bash
python scripts/run_validate.py --data-dir data/text_processed
python scripts/run_train.py --config configs/smoke_test_text.yaml --project-root .
```

## 4. HuggingFace fine-tuning

```bash
python scripts/run_train.py --config configs/exp002_hf_text_finetune.yaml --project-root .
python scripts/run_predict.py --config configs/exp002_hf_text_finetune.yaml --project-root . --input data/text_processed/sample_positive.txt
```

## 권장 흐름

1. Drive mount
2. GitHub repo clone 또는 pull
3. Drive의 processed data를 repo의 `data/processed` 또는 `data/text_processed`로 복사
4. config 선택 또는 복사 후 실험명 수정
5. `scripts/run_validate.py` 실행
6. `scripts/run_train.py` 실행
7. `experiments/{experiment_name}` 결과를 Drive에 백업
