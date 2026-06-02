# Colab 실험 템플릿

실제 `.ipynb` 노트북을 만들 때 아래 흐름을 체크리스트로 사용합니다.

```python
from google.colab import drive
drive.mount("/content/drive")
```

```bash
git clone <repo-url>
cd <repo-name>
python scripts/run_validate.py --data-dir data/processed
python scripts/run_train.py --config configs/smoke_test.yaml --project-root .
```

권장 흐름:

```text
1. Drive mount
2. GitHub repo clone 또는 pull
3. Drive의 processed data를 /content로 복사
4. config 선택
5. scripts/run_validate.py 실행
6. scripts/run_train.py 실행
7. best artifact를 Drive에 백업
```
