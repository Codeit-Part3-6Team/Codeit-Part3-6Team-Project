# Experiment Lead — 실험 가이드

이 문서는 Experiment Lead가 config를 바꿔가며 RAG 검색/답변 품질을 실험하고 최적 조합을 찾는 방법을 설명합니다.

## 실험 기본 흐름

```
1. base config 복사 → 2. 파라미터 변경 → 3. ingest → 4. chat/evaluate → 5. metrics 확인 → 6. 비교/반복
```

## VM 전용 production config 만들기

```bash
cp configs/experiments/rag/rag_langchain.yaml \
   configs/experiments/rag/rag_production.yaml
```

`rag_production.yaml`을 열고 수정:

```yaml
experiment:
  name: rag_production

paths:
  raw_docs_dir: /shared/data/raw_docs             # 실제 데이터 경로
  output_dir: /shared/experiments/rag_production   # 실험 산출물 (공유)

evaluation:
  questions_path: /shared/data/eval_questions.csv   # DE가 만든 평가셋

rag:
  engine: langchain

  embedding:
    provider: ollama               # 시작은 ollama로
    model_name: nomic-embed-text   # ollama pull nomic-embed-text 필요

  splitter:
    chunk_size: 500                # ← 실험할 핵심 파라미터
    chunk_overlap: 80              # chunk_size의 15~20%

  retriever:
    method: similarity             # keyword / similarity / hybrid
    top_k: 5                       # ← 실험할 핵심 파라미터

  answerer:
    mode: llm
    provider: ollama
    model_name: gemma4:e2b         # ollama pull gemma4:e2b
    temperature: 0.2
    require_citations: true
    fallback_message: 문서에서 확인하지 못했습니다.
```

## 실험 조합별 config 관리

각 조합마다 `output_dir`만 바꿔서 config를 복사/수정합니다:

```bash
# 조합 1: chunk=300, top_k=3
cp configs/experiments/rag/rag_production.yaml \
   configs/experiments/rag/rag_prod_chunk300_top3.yaml
# → output_dir: /shared/experiments/rag_prod_chunk300_top3

# 조합 2: chunk=500, top_k=5
cp configs/experiments/rag/rag_production.yaml \
   configs/experiments/rag/rag_prod_chunk500_top5.yaml
# → output_dir: /shared/experiments/rag_prod_chunk500_top5

# 조합 3: chunk=800, top_k=7, retriever=hybrid
# → output_dir: /shared/experiments/rag_prod_chunk800_hybrid
```

## 실험 파라미터 조합표

| 파라미터 | 추천 값 | 영향 |
|---|---|---|
| `chunk_size` | 300, 500, 800 | 너무 작으면 문맥 부족, 너무 크면 검색 정밀도 저하 |
| `chunk_overlap` | chunk_size의 15~20% | 보통 chunk_size 변경 시 비율 유지 |
| `retriever.method` | keyword → similarity → hybrid | keyword가 가장 빠르고 단순 |
| `top_k` | 3, 5, 7 | 많을수록 hit 확률 증가, 너무 많으면 노이즈 |
| `embedding.provider` | local → ollama → openai | local은 가볍고 무료, ollama/opena는 정확도 ↑ |

## 실행 방법 — 2가지

### 방법 1: CLI (빠른 자동화용)

```bash
cd ~/project
conda activate codeit-ml-pipeline

# 1. config 검증 (한 번만)
python scripts/check_rag_pipeline.py \
  --config configs/experiments/rag/rag_production.yaml \
  --project-root .

# 2. 문서 ingest + chunking + embedding
python scripts/run_rag_ingest.py \
  --config configs/experiments/rag/rag_production.yaml \
  --project-root .

# 3. 단일 질문으로 디버깅
python scripts/run_rag_chat.py \
  --config configs/experiments/rag/rag_production.yaml \
  --project-root . \
  --question "이 사업의 예산은 얼마인가?"

# 4. 평가셋 전체 평가 (metrics 생성)
python scripts/run_rag_chat.py \
  --config configs/experiments/rag/rag_production.yaml \
  --project-root . \
  --evaluate
```

### 방법 2: 노트북 (분석/시각화용)

`notebooks/rag/rag_config_run.ipynb`를 열고:

1. `EXP_NAME = "rag_production"` 설정
2. `RUN_CHECK`, `RUN_INGEST`, `RUN_RETRIEVE`, `RUN_EVALUATE` 플래그 조정
3. 셀 순서대로 실행 (Shift+Enter)

**추천 플래그:**
```python
EXP_NAME = "rag_production"
RUN_CHECK = True      # 첫 실행 시 config 검증
RUN_INGEST = True     # 문서 재로딩 시만 True
RUN_RETRIEVE = True   # 단일 질문 결과 확인
RUN_EVALUATE = True   # 평가셋 전체 실행
```

두 번째 실험부터는 ingest 결과를 재사용하려면 `RUN_INGEST = False`.

## 실험 결과 확인

`/shared/experiments/<name>/` 아래 파일들:

| 파일 | 용도 | 확인 시점 |
|---|---|---|
| `metrics.json` | 정량 지표 4개 | 실험 직후 |
| `evaluation_results.csv` | 질문별 결과 | 세부 분석 시 |
| `bad_retrievals.csv` | 검색 실패한 질문 목록 | hit_rate 낮을 때 |
| `unsupported_answers.csv` | 답변 근거 부족 | answer 품질 나쁠 때 |
| `failed_questions.csv` | 실행 자체가 실패한 질문 | 예외 발생 시 |
| `answers.jsonl` | 모든 답변과 citation | 발표 예시 고를 때 |

```bash
# metrics 한눈에 보기
cat /shared/experiments/rag_production/metrics.json
# {"retrieval_hit_rate": 0.72, "answer_contains_expected_rate": 0.58, ...}
```

## 여러 실험 비교

`notebooks/rag/rag_compare_results.ipynb`를 열고 실행하면 (Shift+Enter):

- **Grouped Bar Chart**: 실험별 4개 지표를 한 번에 비교
- **Config Diff**: 실험 간 config 차이를 표로 비교
- **Heatmap**: 어떤 질문이 모든 실험에서 실패했는지 시각화
- **Answer Side-by-Side**: 동일 질문에 대한 각 실험의 답변 비교

`reports/rag_retriever_comparison.csv`도 참고 (retriever.method 비교).

## 실험 로그 수동 기록

`reports/experiment_log.csv`에 수동으로 기록:

```csv
exp_name,date,author,config_path,eval_questions,retrieval_hit_rate,answer_contains_expected_rate,citation_correct_rate,not_found_rate,changed_from_baseline,notes
rag_prod_chunk300,2026-06-19,EL,rag_prod_chunk300_top3.yaml,/shared/data/eval_questions.csv,0.72,0.58,0.50,0.10,chunk=300 top_k=3,chunk 크기 줄이니 hit_rate 개선
```

## 트러블슈팅

| 증상 | 확인/조치 |
|---|---|
| document count = 0 | `raw_docs_dir` 경로, `file_types`에 csv/hwp 포함됐는지 |
| metrics 전부 0 | 평가셋 `questions_path`가 올바른지, 문서가 비어있지 않은지 |
| hit_rate 낮음 | `chunk_size` 너무 크거나 작음, `retriever.method` 변경 검토, `bad_retrievals.csv` 확인 |
| answer 품질 나쁨 | local answerer를 ollama로 업그레이드, `unsupported_answers.csv` 확인 |
| not_found 많음 | 문서 커버리지 부족 → DE에게 질문 검토 요청 or `chunk_overlap` 증가 |
| ingest 느림 | checkpoint 기능 활용: `RAG_CHECKPOINT=true` 설정하면 기존 결과 재사용 |

## 발표 전 체크리스트

`docs/team/rehearsal.md` 참고. 핵심만:

- [ ] `metrics.json`이 생성되었고 0이 아님
- [ ] 질문별로 검색된 chunk와 답변이 함께 존재
- [ ] 실패한 질문이 어떤 유형인지 구분 가능 (retrieval vs answer vs exception)
- [ ] 발표 예시로 쓸 질문-검색-답변 2~3개를 미리 선정
