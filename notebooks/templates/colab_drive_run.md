# Colab / Drive RAG 실행 템플릿

Colab에서 RAG 실험을 돌릴 때 아래 순서를 셀 단위로 옮겨 사용합니다.
자세한 설명은 `docs/md/experiments/COLAB_GUIDE.md`를 기준으로 합니다.

## 언제 Colab으로 돌리는가

- Drive에 원본 문서와 실험 결과를 함께 관리할 때
- 로컬 환경이 불안정해서 Colab에서 재현하고 싶을 때
- HuggingFace embedding, reranker, LLM answerer처럼 다운로드와 추론 자원이 더 필요한 옵션을 확인할 때
- 팀원에게 동일한 실행 환경을 빠르게 공유하고 싶을 때

작은 샘플 문서와 local provider 검증은 로컬 Jupyter로도 충분하지만, Colab에서 돌릴 사람은 이 템플릿을 그대로 사용하면 됩니다.

## 1. Drive 연결

```python
from google.colab import drive

drive.mount("/content/drive")
```

## 2. 저장소 준비

```bash
REPO_URL="<repo-url>"
git clone "$REPO_URL" /content/codeit-rag-project
cd /content/codeit-rag-project
pip install -r requirements.txt
```

## 3. 작업 경로 만들기

```python
from pathlib import Path

DRIVE_ROOT = Path("/content/drive/MyDrive/codeit_rag_project")
for name in ["data/raw", "experiments", "reports", "backups"]:
    (DRIVE_ROOT / name).mkdir(parents=True, exist_ok=True)

print(DRIVE_ROOT)
```

## 4. RAG config 선택

처음에는 repo 안의 기본 config를 사용합니다.

```bash
python scripts/check_rag_pipeline.py \
  --project-root . \
  --config configs/experiments/rag/rag_semantic.yaml
```

Drive 문서로 실험할 때는 아래 값이 들어간 별도 config를 만들어 사용합니다.

- `paths.input_dir`: `/content/drive/MyDrive/codeit_rag_project/data/raw`
- `paths.output_dir`: `/content/drive/MyDrive/codeit_rag_project/experiments/<run-name>`
- `artifact_policy.backup_dir`: `/content/drive/MyDrive/codeit_rag_project/backups/<run-name>`
- `rag.evaluation.questions_path`: 평가 질문 CSV 경로

## 5. 문서 적재

```bash
python scripts/run_rag_ingest.py \
  --project-root . \
  --config configs/experiments/rag/rag_semantic.yaml
```

확인할 것:

- chunk 개수
- 문서별 chunk 분포
- 실패한 문서가 있다면 failure artifact

## 6. 검색 품질 확인

```bash
python scripts/run_rag_retrieve.py \
  --project-root . \
  --config configs/experiments/rag/rag_semantic.yaml \
  --query "제안 마감일은 언제인가?"
```

확인할 것:

- 질문과 관련 있는 chunk가 상위에 나오는지
- `top_k`를 바꿨을 때 근거가 충분해지는지
- citation에 문서명과 chunk 정보가 남는지

## 7. 답변과 평가 실행

```bash
python scripts/run_rag_chat.py \
  --project-root . \
  --config configs/experiments/rag/rag_semantic.yaml \
  --question "입찰 참가 자격은 무엇인가?"
```

```bash
python scripts/run_rag_chat.py \
  --project-root . \
  --config configs/experiments/rag/rag_semantic.yaml \
  --evaluate
```

확인할 것:

- 답변이 근거 문서의 내용에서 벗어나지 않는지
- citation이 함께 남는지
- evaluation 결과 CSV/JSON이 저장되는지

## 8. 실험 비교

```bash
python scripts/compare_rag_retrievers.py \
  --project-root . \
  --configs \
    configs/experiments/rag/rag_keyword.yaml \
    configs/experiments/rag/rag_semantic.yaml \
    configs/experiments/rag/rag_hybrid.yaml
```

비교할 때는 chunk 설정, 검색 방식, `top_k`, answerer provider 중 하나씩만 바꾸는 것이 좋습니다.

## 체크리스트

- Drive에 원본 문서가 있고 Git에는 올라가지 않는가?
- config의 입력/출력/백업 경로가 Drive 기준으로 맞는가?
- ingest, retrieve, chat, evaluate가 모두 실행되는가?
- retrieval 결과와 citation을 사람이 직접 확인했는가?
- 실험 README나 report에 결론과 다음 액션을 적었는가?
