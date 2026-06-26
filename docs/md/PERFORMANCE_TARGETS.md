# RAG 서비스 성능 기준

## 측정 지표

### 주 지표

| 지표 | 의미 | 계산 |
|------|------|------|
| `judge_correct_rate` | **전체 질문 중 LLM이 의미적으로 정답이라고 판단한 비율** | LLM-as-Judge binary / total |
| `retrieval_hit_rate` | 검색된 top-k chunk 중 정답 chunk 포함 비율 | `expected_chunk_ids ∩ retrieved_ids ≠ ∅` |
| `citation_correct_rate` | citation이 정답 chunk를 가리킨 비율 | `expected_chunk_ids ∩ citation_ids ≠ ∅` |
| `not_found_rate` | LLM이 "문서에서 확인하지 못했습니다"라고 응답한 비율 | `status == "not_found" / total` |

**실제 답변 품질은 `judge_correct_rate`로 판단**합니다.
Phase A/B/C 모든 단계의 통과 여부도 `judge_correct_rate`를 기준으로 합니다.
나머지 주 지표(`retrieval_hit`, `citation_correct`, `not_found`)는 보조 참고입니다.

### 진단 지표 (`diagnostic`)

`metrics.json`의 `diagnostic` 키 아래 제공. **Phase 목표에는 포함되지 않으며**, 원인 분석용으로만 사용합니다.

| 지표 | 의미 | 계산 |
|------|------|------|
| `answer_contains_expected_rate` | 답변에 기대 정답이 substring으로 포함된 비율. judge 도입 전 주 지표였으나 공백·표현 차이에 민감 | `expected_answer in answer` |
| `judge_on_answered_rate` | **답변 시도 건수 중** 정답률. answerer 단독 품질 | `judge_correct` / `answered_total` |
| `retrieval_failure_rate` | retriever가 정답 chunk를 아예 못 찾은 비율 | `retrieval_hit == false` / total |
| `answerer_gave_up_rate` | 정답 chunk를 찾았는데 LLM이 포기한 비율 | `retrieval_hit=true AND status=not_found` / total |
| `answerer_error_rate` | 정답 chunk를 찾았고 시도했는데 틀린 비율 | `retrieval_hit=true AND answered AND judge=false` / total |

**진단 지표 읽는 법**:

```
not_found_rate가 높다면 → retrieval_failure_rate vs answerer_gave_up_rate 중 어느 쪽이 큰가?
├── retrieval_failure_rate↑ → retriever 튜닝 (reranker, embedding, chunk_size)
└── answerer_gave_up_rate↑  → answerer 튜닝 (LLM 교체, top_k 축소, 프롬프트)

answerer_error_rate가 높다면 → judge_on_answered_rate 확인.
├── judge_on_answered_rate↓ → LLM이 정답을 못 읽음 (모델·프롬프트 문제)
└── judge_on_answered_rate↑ → answerer는 정상, 다른 요소 병목
```

`judge_correct_rate` 사용법: config에 아래 섹션 추가

```yaml
evaluation:
  llm_judge:
    enabled: true
    model_name: gpt-5-mini
```

## 단계별 목표

| Phase | 임베더 | answerer | retrieval_hit | judge_correct | citation_correct | not_found |
|-------|--------|----------|--------------|-------------|-----------------|-----------|
| **A 베이스라인** | text-embed-3 | gpt-5-mini | **≥ 60%** | **≥ 70%** | **≥ 50%** | **≤ 30%** |
| **B 튜닝 완료** | text-embed-3 | gpt-5-mini | **≥ 75%** | **≥ 85%** | **≥ 65%** | **≤ 15%** |
| **C 서비스 가능** | - | - | **≥ 80%** | **≥ 90%** | **≥ 75%** | **≤ 10%** |

`diagnostic` 지표들은 Phase 통과 여부와 무관하며, 원인 분석용으로만 참고합니다.

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
