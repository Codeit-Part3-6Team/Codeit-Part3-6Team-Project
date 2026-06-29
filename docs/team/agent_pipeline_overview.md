# Agent / 챗봇 파이프라인 개요

> 기존 RAG 파이프라인 위에 Agent Loop + 챗봇 모드를 추가한 확장입니다.
> config 하나만 바꾸면 RAG / Agent / 챗봇 전환이 가능합니다.

---

## 한 장 요약

`
config.yaml
    │
    ├── agent.enabled: false  ──→  기존 RAG (ingest → retrieve → answer → evaluate)
    │
    └── agent.enabled: true
        ├── Phase DAG 모드  ──→  extract → scan → decide (순차/병렬)
        └── 챗봇 모드       ──→  LLM이 Tool 동적 선택, 대화형
`

---

## 언제 어떤 모드를 쓰나?

| 하려는 일 | 모드 | 실행 |
|----------|------|------|
| 단일 문서에서 답변 찾기 | RAG (기본) | un_rag_chat.py |
| 여러 관점에서 문서 분석 후 종합 판단 | Agent Phase DAG | un_rag_agent.py --question "..." |
| 대화하면서 문서 분석 | 챗봇 | un_rag_agent.py (질문 없이) |
| 검색 품질 평가 | RAG 평가 | un_rag_evaluation |
| Agent 종합 평가 | Agent 평가 | un_rag_agent_evaluation |

---

## Agent 모드 실행 예시

`ash
# Phase DAG 모드 — extract → decide 순차 실행
python scripts/run_rag_agent.py \
  --config configs/experiments/rag/agent/agent_lplus.yaml \
  --question "이 사업에 참여해도 될까?"

# 챗봇 모드 — 대화형
python scripts/run_rag_agent.py \
  --config configs/experiments/rag/agent/agent_lplus.yaml
`

---

## Agent Loop 모드 (챗봇 내부 반복 실행)

챗봇 모드에서 복잡한 질문이 들어오면 `AgentLoopRunner`가 여러 Tool을 순차적으로 실행합니다:

- `agent.loop.enabled: true` — 반복 Tool 실행 활성화
- config의 `loop.max_iterations` 값으로 최대 반복 횟수 제한
- 활용 예: 단일 질문에 여러 Tool을 순차 적용해야 하는 복합 분석

---

## Config만 바꾸면 동작이 달라진다

| 바꾸는 것 | config 키 | 예시 |
|----------|----------|------|
| 검색 방식 | ag.retriever.method | keyword / semantic / hybrid |
| LLM 종류 | ag.answerer.provider | openai / ollama / huggingface |
| Phase 구성 | gent.phases | extract → decide |
| Tool별 검색 개수 | 	ools.*.retriever.top_k | 10 |
| Tool별 프롬프트 | 	ools.*.answerer.prompt_template | 커스텀 템플릿 |
| Structured Output 형식 | 	ools.*.answerer.output_schema | facts_schema / decision_schema |
| 실패 시 동작 | 	ools.*.on_failure | skip / abort_phase / abort_agent |
| Tool 간 데이터 전달 | 	ools.*.input_from | [extract_facts] |
| 병렬 실행 여부 | phases[*].parallel | true / false |

---

## 산출물

| 모드 | 산출물 | 내용 |
|------|--------|------|
| RAG | nswers.jsonl | 질문별 답변 + citation |
| RAG | metrics.json | retrieval_hit_rate 등 |
| Agent | gent_state.jsonl | Phase별 Tool 실행 결과 (answer + structured_output) |
| Agent | gent_metrics.json | tool_success_rate 등 7종 지표 |
| Agent | gent_evaluation.csv | 질문별 Agent 평가 결과 |

---

## Streamlit App 연동

pp/utils/mock_data.py의 2개 함수만 실제 파이프라인 호출로 교체:

`
mock_analyze()  →  run_rag_ingest + AgentRunner.run()
mock_chat()     →  ChatbotRunner.chat()
`

UI 코드는 0줄 수정.
