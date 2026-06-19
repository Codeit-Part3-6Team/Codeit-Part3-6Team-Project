# Experiment Lead — 실험 가이드

실험 Lead는 검색/답변 품질을 config만 바꿔가며 비교하는 역할입니다.

## 기본 흐름

```
1. base config 복사 → 2. 파라미터 변경 → 3. 실행 → 4. metrics.json 확인 → 5. 비교/반복
```

## 템플릿 config

VM 전용 실험 config를 만듭니다:

```bash
cp configs/experiments/rag/rag_langchain.yaml \
   configs/experiments/rag/rag_production.yaml
```

`rag_production.yaml`을 열고 경로/모델을 수정합니다:

```yaml
paths:
  raw_docs_dir: /shared/data/raw_docs          # 실제 데이터
  output_dir: /shared/experiments/rag_production_chunk500_top5
  # ※ 조합명을 output_dir에 포함시켜 구분

evaluation:
  questions_path: /shared/data/eval_questions.csv   # DE가 만든 평가셋

rag:
  embedding:
    provider: ollama               # or local (가볍게 시작)
    model_name: nomic-embed-text   # ollama pull 필요

  splitter:
    chunk_size: 500                # 실험할 파라미터 1
    chunk_overlap: 80

  retriever:
    method: similarity             # keyword/semantic/hybrid
    top_k: 5                       # 실험할 파라미터 2

  answerer:
    provider: ollama               # or local
    model_name: gemma4:e2b
```

## 실험할 파라미터 조합

| 파라미터 | 추천 값 |
|---|---|
| `chunk_size` | 300, 500, 800 |
| `chunk_overlap` | 50, 80, 120 |
| `retriever.method` | keyword, similarity, hybrid |
| `top_k` | 3, 5, 7 |
| `embedding.provider` | local → ollama → openai |

조합별로 `output_dir`만 다르게 해서 복사본을 만드세요. 예:
```
/shared/experiments/rag_chunk300_top3/
/shared/experiments/rag_chunk500_top5/
/shared/experiments/rag_chunk800_kw/
```

## 실행 명령어

```bash
cd ~/project
conda activate codeit-ml-pipeline

# ingest + 검색 + 답변 + 평가 한 번에
python scripts/run_rag_chat.py \
  --config configs/experiments/rag/rag_production.yaml \
  --project-root . \
  --evaluate

# 또는 retriever만 비교
python scripts/compare_rag_retrievers.py --project-root .
```

## 결과 확인

| 파일 | 설명 |
|---|---|
| `/shared/experiments/<name>/metrics.json` | 정량 지표 (retrieval_hit_rate 등) |
| `/shared/experiments/<name>/evaluation_results.csv` | 질문별 결과 |
| `/shared/experiments/<name>/bad_retrievals.csv` | 검색 실패 상세 |
| `/shared/experiments/<name>/unsupported_answers.csv` | 답변 근거 실패 |

## 확인할 지표

- **retrieval_hit_rate** 높을수록 검색 품질 좋음 → chunk_size, top_k 튜닝
- **answer_contains_expected_rate** 높을수록 답변 정확 → answerer 모델 변경 검토
- **not_found_rate** 낮을수록 좋음 → fallback_message 조정

## 의사결정 가이드

| 증상 | 원인 | 조치 |
|---|---|---|
| hit_rate 낮음 | chunk_size 너무 큼/작음 or retriever 부적합 | chunk_size 조정 or method 변경 |
| answer 품질 나쁨 | local answerer 한계 | ollama or openai로 업그레이드 |
| not_found 많음 | 문서 커버리지 부족 | DE에게 추가 질문 요청 or chunk_overlap 증가 |
