# Agent / 챗봇 파이프라인 개요

> 기존 RAG 파이프라인 위에 Agent Loop + 챗봇 모드를 추가한 확장입니다.
> config 하나만 바꾸면 RAG / Agent / 챗봇 전환이 가능합니다.

---

## 한 장 요약

```
config.yaml
    │
    ├── agent.enabled: false  ──→  기존 RAG (ingest → retrieve → answer → evaluate)
    │
    └── agent.enabled: true
        ├── Phase DAG 모드  ──→  extract → scan → decide (순차/병렬)
        └── 챗봇 모드       ──→  LLM이 Tool 동적 선택, 대화형
```

---

## 언제 어떤 모드를 쓰나?

| 하려는 일 | 모드 | 실행 |
|----------|------|------|
| 단일 문서에서 답변 찾기 | RAG (기본) | run_rag_chat.py |
| 여러 관점에서 문서 분석 후 종합 판단 | Agent Phase DAG | run_rag_agent.py --question "..." |
| 대화하면서 문서 분석 | 챗봇 | run_rag_agent.py (질문 없이) |
| 검색 품질 평가 | RAG 평가 | run_rag_evaluation |
| Agent 종합 평가 | Agent 평가 | run_rag_agent_evaluation |

---

## 현재 Streamlit 시연 기준

현재 Streamlit 앱은 `agent_lplus.yaml`의 Tool 정의를 상속하지만, 화면 기본 동선은 Phase DAG 전체를 자동 실행하는 방식이 아닙니다.

- 문서 분석 화면: 단일 공고의 핵심 요약, 핵심 요구사항, 확인된 사업 정보를 표시합니다.
- 대화형 탐색 화면: 사용자의 질문 유형에 맞춰 ChatbotRunner가 필요한 Tool을 선택합니다.
- `decide_participation`: 참여 가능성, 리스크, 적합도 등을 물었을 때 호출 가능한 Tool입니다. 현재 기본 분석 카드에서 자동으로 입찰 참여 여부를 산출하지는 않습니다.
- `compare_rfps`: 다중 문서 비교 Tool 계약은 남아 있지만, 현재 시연 UI에서는 비교 화면을 숨겼습니다.

따라서 발표에서는 “Agent Tool로 참여 판단을 확장할 수 있다” 또는 “참여 가능성 질문 시 판단 Tool을 호출할 수 있다”라고 설명하는 것이 정확합니다.

---

## Agent 모드 실행 예시

```bash
# Phase DAG 모드 — extract → decide 순차 실행
python scripts/run_rag_agent.py \
  --config configs/experiments/rag/agent/agent_lplus.yaml \
  --question "이 사업에 참여해도 될까?"

# 챗봇 모드 — 대화형
python scripts/run_rag_agent.py \
  --config configs/experiments/rag/agent/agent_lplus.yaml
```

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
| 검색 방식 | rag.retriever.method | keyword / semantic / hybrid |
| LLM 종류 | rag.answerer.provider | openai / ollama / huggingface |
| Phase 구성 | agent.phases | extract → decide |
| Tool별 검색 개수 | tools.*.retriever.top_k | 10 |
| Tool별 프롬프트 | tools.*.answerer.prompt_template | 커스텀 템플릿 |
| Structured Output 형식 | tools.*.answerer.output_schema | facts_schema / decision_schema |
| 실패 시 동작 | tools.*.on_failure | skip / abort_phase / abort_agent |
| Tool 간 데이터 전달 | tools.*.input_from | [extract_facts] |
| 병렬 실행 여부 | phases[*].parallel | true / false |

---

## 산출물

| 모드 | 산출물 | 내용 |
|------|--------|------|
| RAG | answers.jsonl | 질문별 답변 + citation |
| RAG | metrics.json | retrieval_hit_rate 등 |
| Agent | agent_state.jsonl | Phase별 Tool 실행 결과 (answer + structured_output) |
| Agent | agent_metrics.json | tool_success_rate 등 7종 지표 |
| Agent | agent_evaluation.csv | 질문별 Agent 평가 결과 |

---

## Streamlit App 연동

`app/services/rag_service.py`가 UI ↔ RAG 서비스 어댑터 역할을 합니다.
UI는 `src.rag`를 직접 import하지 않고 아래 함수만 호출합니다.

| 서비스 함수 | 내부 호출 | 용도 |
|-----------|----------|------|
| `create_and_ingest()` | `run_rag_ingest()` | 업로드 문서 → run 생성 |
| `summarize()` | `run_tool("extract_facts")` | 핵심 요약 |
| `extract_requirements()` | `run_tool("extract_requirements")` | 참가자격/제출서류 |
| `compare()` | `run_tool("compare_rfps")` | 다중 문서 비교. 현재 시연 UI 기본 노출 없음 |
| `ask_with_document_filter()` | `ChatbotRunner.chat()` | 선택 문서 챗봇 질의 |

UI 계약은 `docs/team/rag_frontend_contract.md`를 봅니다.
