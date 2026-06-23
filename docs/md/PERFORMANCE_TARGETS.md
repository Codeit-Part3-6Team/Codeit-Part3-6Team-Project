# RAG 서비스 성능 기준

## 측정 지표

| 지표 | 의미 | 계산 |
|------|------|------|
| `retrieval_hit_rate` | 검색된 top-k chunk 중 정답 chunk 포함 비율 | `expected_chunk_ids ∩ retrieved_ids ≠ ∅` |
| `answer_contains_expected_rate` | 답변에 기대 정답이 포함된 비율 | `expected_answer in answer` |
| `citation_correct_rate` | citation이 정답 chunk를 가리킨 비율 | `expected_chunk_ids ∩ citation_ids ≠ ∅` |

## 단계별 목표

| Phase | 임베더 | 답변기 | retrieval_hit | answer_contains | citation_correct |
|-------|--------|--------|---------------|-----------------|-----------------|
| **0 현재** | hashing-ngram | extractive | 측정불가 | ~23% | 측정불가 |
| **A 베이스라인** | nomic-embed-text | gpt-5-mini | **≥ 60%** | **≥ 50%** | **≥ 50%** |
| **B 튜닝 완료** | nomic-embed-text | gpt-5-mini | **≥ 75%** | **≥ 70%** | **≥ 65%** |
| **C 서비스 가능** | - | - | **≥ 80%** | **≥ 80%** | **≥ 75%** |

### Phase A — 베이스라인 진입 조건

EL이 먼저 할 것:

1. 임베더 교체: `hashing-char-ngram-v1` → `nomic-embed-text` (Ollama) 또는 `text-embedding-3-small` (OpenAI)
2. 답변기 교체: `provider: local` → `provider: openai, model_name: gpt-5-mini`
3. `expected_chunk_ids` 채우기 (ingest 후 chunk ID 매핑)

목표: retrieval ≥ 60%, answer ≥ 50%, citation ≥ 50%.
못 넘으면 → chunk_size, top_k 튜닝.

### Phase B — 튜닝

베이스라인 통과 후:

- chunk_size (300~1000), chunk_overlap (50~200), top_k (3~10) 그리드 탐색
- retriever_method 비교 (similarity → hybrid)
- reranker 도입 검토

목표: retrieval ≥ 75%, answer ≥ 70%, citation ≥ 65%.

### Phase C — 서비스 진입

Phase B 통과 후:

- 실험으로 검증된 최적 config 확정
- M(요약) / L(비교) 단계 진입 가능

목표: **retrieval ≥ 80%, answer ≥ 80%, citation ≥ 75%**
