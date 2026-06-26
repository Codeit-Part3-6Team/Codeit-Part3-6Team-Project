# RAG + Agent 파이프라인 흐름 정리

> 2026-06-26 | eature/agent-polish 기준

---

## 1. 전체 구조

`
config.yaml
    │
    ├── agent.enabled: false  ──→  기존 RAG 파이프라인
    │
    └── agent.enabled: true
        ├── chatbot.enabled: false  ──→  Agent 모드 (Phase DAG)
        └── chatbot.enabled: true   ──→  챗봇 모드 (LLM 동적 Tool 선택)
`

---

## 2. 기존 RAG 파이프라인 (agent.enabled: false)

`
configs/experiments/rag/rag-baseline.yaml

ingest → retrieve → answer → evaluate

ingest:   원본문서 → chunk → embedding → chunks.csv + embeddings.jsonl
retrieve: 질문 → embedding/search → top-k chunk
answer:   retrieved_chunks → LLM/extractive → 답변 + citation
evaluate: 평가질문셋 순회 → retrieval_hit_rate, judge_correct_rate
`

## 3. Agent 모드 (agent.enabled: true, chatbot.enabled: false)

`
question → AgentRunner
  _load_document_context() ← chunks.csv, embeddings.jsonl
  _resolve_dag() → Phase 순서 결정

  Phase: extract
    Tool: extract_facts
      retriever → answerer → structured_output
    → state["extract_facts"]

  Phase: decide (depends_on: [extract])
    Tool: decide_participation
      input_from: [extract_facts] → 이전 결과를 프롬프트 context로 주입
    → state["decide_participation"]

  _build_summary() → agent_state.jsonl
`

## 4. 챗봇 모드 (agent.enabled: true, chatbot.enabled: true)

`
user_input → ChatbotRunner
  _select_tool() → LLM이 Tool 선택
  _run_tool_with_retry() → 실패 시 최대 2회 재시도
  응답 → history 저장 → 다음 질문 context
`

## 5. Streamlit App 연동 포인트

`
file_uploader → run_rag_ingest → chunks.csv, embeddings.jsonl
"분석 시작" → AgentRunner.run() → structured_output → UI
채팅 입력 → ChatbotRunner.chat() → (answer, citations) → UI
`

**갈아끼울 파일:** app/utils/mock_data.py (2개 함수만 교체)
