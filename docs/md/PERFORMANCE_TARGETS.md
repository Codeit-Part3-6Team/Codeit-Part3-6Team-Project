# RAG 서비스 성능 기준

## 측정 지표

| 지표 | 의미 | 계산 |
|------|------|------|
| `retrieval_hit_rate` | 검색된 top-k chunk 중 정답 chunk 포함 비율 | `expected_chunk_ids ∩ retrieved_ids ≠ ∅` |
| `citation_correct_rate` | citation이 정답 chunk를 가리킨 비율 | `expected_chunk_ids ∩ citation_ids ≠ ∅` |
| `answer_contains_expected_rate` | 답변에 기대 정답이 포함된 비율 (substring, 보조) | `expected_answer in answer` |
| `judge_correct_rate` | LLM이 의미적으로 정답이라고 판단한 비율 (주 지표) | LLM-as-Judge binary |

`answer_contains_expected`는 쉼표·공백·표현 차이에 민감하므로 보조 지표로만 참고하고,
**실제 답변 품질은 `judge_correct_rate`로 판단**합니다.

`judge_correct_rate` 사용법: config에 아래 섹션 추가

```yaml
evaluation:
  llm_judge:
    enabled: true
    model_name: gpt-5-mini
```

## 단계별 목표

| Phase | 임베더 | answerer | retrieval_hit | judge_correct | citation_correct |
|-------|--------|----------|--------------|-------------|-----------------|
| **A 베이스라인** | text-embed-3 | gpt-5-mini | **≥ 60%** | **≥ 70%** | **≥ 50%** |
| **B 튜닝 완료** | text-embed-3 | gpt-5-mini | **≥ 75%** | **≥ 85%** | **≥ 65%** |
| **C 서비스 가능** | - | - | **≥ 80%** | **≥ 90%** | **≥ 75%** |

`answer_contains_expected_rate`(substring)는 보조 지표. Phase 통과 여부와 무관하게 참고만.

### Phase A — 베이스라인 진입 조건

EL이 먼저 할 것:

1. 임베더 교체: `hashing-char-ngram-v1` → `text-embedding-3-small` (OpenAI)
2. 답변기 교체: `provider: local` → `provider: openai, model_name: gpt-5-mini`
3. `expected_chunk_ids` 채우기 (ingest 후 chunk ID 매핑)
4. LLM-judge 활성화 (`evaluation.llm_judge.enabled: true`)

목표: retrieval ≥ 60%, judge ≥ 70%, citation ≥ 50%.
못 넘으면 → chunk_size, top_k 튜닝.

### Phase B — 튜닝

베이스라인 통과 후:

- chunk_size (300~1000), chunk_overlap (50~200), top_k (3~10) 그리드 탐색
- retriever_method 비교 (similarity → hybrid)
- reranker 도입 검토

목표: retrieval ≥ 75%, judge ≥ 85%, citation ≥ 65%.

### Phase C — 서비스 진입

Phase B 통과 후:

- 실험으로 검증된 최적 config 확정
- M(요약) / L(비교) 단계 진입 가능

목표: **retrieval ≥ 80%, judge ≥ 90%, citation ≥ 75%**
