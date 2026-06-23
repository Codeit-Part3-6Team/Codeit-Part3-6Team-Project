# RAG 서비스 성능 기준

발표·서비스 전 단계 통과 기준 (Phase C).

## 측정 지표

| 지표 | 의미 | 계산 |
|------|------|------|
| `retrieval_hit_rate` | 검색된 top-k chunk 중 정답 chunk 포함 비율 | `expected_chunk_ids ∩ retrieved_ids ≠ ∅` |
| `answer_contains_expected_rate` | 답변에 기대 정답이 포함된 비율 | `expected_answer in answer` |
| `citation_correct_rate` | citation이 정답 chunk를 가리킨 비율 | `expected_chunk_ids ∩ citation_ids ≠ ∅` |

## 목표치

| 지표 | Phase C 목표 |
|------|------------|
| `retrieval_hit_rate` | **≥ 80%** |
| `answer_contains_expected_rate` | **≥ 80%** |
| `citation_correct_rate` | **≥ 75%** |

## 각 지표가 의존하는 요소

| 지표 | 핵심 의존 |
|------|----------|
| `retrieval_hit` | embedder (nomic-embed-text / text-embedding-3-small), chunk_size, top_k |
| `answer_contains` | answerer (gpt-5-mini), retrieval 품질, 프롬프트 |
| `citation_correct` | retrieval 품질, citation 매핑 정확도 |

retrieval_hit이 낮으면 answer_contains와 citation_correct도 같이 떨어진다. retrieval_hit이 가장 먼저 잡아야 할 지표.

## 실행

```bash
python scripts/run_rag_chat.py \
  --config configs/experiments/rag/rag_langchain.yaml \
  --project-root . \
  --evaluate
```

결과: `experiments/rag_langchain/metrics.json`

## 전제 조건

- `eval_questions.csv`의 `expected_chunk_ids`가 채워져 있어야 함 (ingest 완료 후)
- 그렇지 않으면 retrieval_hit, citation_correct는 0으로 나옴
