# Agent Loop 구현 계획

> 2026-06-24 세션 산출물. `fix/answer-quality` 브랜치 완성 직후, Config → 코드 갭을 전수 분석하고 Agent Loop + Tool I/F + Structured Output 구현 계획을 수립한 문서.

## 0. 현재 파이프라인 상태 (baseline)

```
ingest → retrieve → answer → evaluate
```
단일 문서, 단일 질문, 단일 턴. Phase 체이닝 없음. `agent.enabled: true`는 config에만 존재.

### 추상화 수준

| 차원 | 점수 | 근거 |
|------|------|------|
| 컴포넌트 Protocol/Factory | 8/10 | `RagEngine`, `RagEmbeddingAdapter` 등 잘 설계 |
| Config 기반 교체 (단일 파이프라인) | 7/10 | embedder, retriever, answerer, reranker 교체 가능 |
| Phase 분리 | 4/10 | 함수 단위로 나뉘었으나 하드코딩 결합 |
| Answerer 분리도 | 6/10 | 함수 단위 분리, but output_schema 미지원 |
| Agent Loop | 0/10 | 전무 |
| Tool I/F | 0/10 | Protocol은 있으나 Tool로 오케스트레이션 불가 |

---

## 1. Config → 코드 갭: 7개 하드코딩 지점

아래는 `configs/experiments/rag/rag_agent.yaml`(194줄)의 각 키와 실제 `src/` 코드를 1:1로 대조한 결과이다.

| # | Config 키 | 파일:라인 | 현재 코드 상태 | 문제 |
|---|---|---|---|---|
| 1 | `agent.enabled` | `pipeline.py` 전체 | 미참조 | 실행기 부재. `true`로 바꿔도 아무 일도 안 일어남 |
| 2 | `agent.phases[].depends_on` | 미구현 | 코드 없음 | Phase DAG 해석, 순서 제어 로직 없음 |
| 3 | `agent.tools` | 미구현 | 코드 없음 | Tool = retriever+answerer+schema 감싸는 wrapper 없음 |
| 4 | `tools.*.answerer.output_schema` | 미구현 | src/ 전체 0회 등장 | `with_structured_output()` 호출 코드 없음 |
| 5 | `tools.*.retriever.top_k` 오버라이드 | 미구현 | 코드 없음 | Tool별 retriever 설정 오버라이드 불가 |
| 6 | `tools.*.answerer.provider: openai` | `adapters.py:316-320` | `NotImplementedError` | adapter 경로로 openai/ollama answerer 사용 불가 |
| 7 | `tools.*.rules.patterns` | 미구현 | 코드 없음 | Rule 엔진 부재 (XL 서비스 필요) |

### 추가: Config에는 없지만 하드코딩된 결합

| # | 하드코딩 위치 | 문제 |
|---|---|---|
| 8 | `pipeline.py:163` — `run_rag_chat()` 내 `run_rag_retrieve()` 강제 호출 | Phase 독립 실행 불가 |
| 9 | `pipeline.py:243-244` — evaluate도 retrieve→answer 하드코딩 | Agent 경로와 혼재 |
| 10 | `langchain.py:153-180` — engine별 answerer 경로 이원화 | langchain engine은 자체 answer(), local engine은 adapter → Tool 통합 시 문제 |

---

## 2. 구현 항목 (신규 3파일, 수정 5파일)

### 2.1 `src/rag/agent.py` — 신규 (~200L)

**책임**: Phase DAG 해석 + Tool dispatch + State 전파

```
AgentRunner
├── load(config) → phases[], tools{}
├── resolve_dag(phases) → 실행 순서 (topological sort, depends_on)
├── run() → Phase 순회 → Tool 병렬 실행 → State 누적
└── State dict  → Phase 간 context 전달 (이전 Tool 결과)
```

**핵심 로직**:
- `agent.enabled: false` → 실행 안 함 (pipeline이 기존 경로로)
- `agent.enabled: true` → phases 순회, depends_on 체크, Tool dispatch
- 각 Tool은 `tool.py`의 `Tool.run(question, context)` 호출
- State dict: `{tool_name: {answer, citations, ...}}` 로 누적 → 다음 Phase 입력으로

### 2.2 `src/rag/tool.py` — 신규 (~150L)

**책임**: retriever + answerer + output_schema + rules 를 하나의 실행 단위로 감쌈

```python
@dataclass
class Tool:
    name: str
    description: str
    retriever_cfg: dict   # rag.retriever 기본값 + 툴별 오버라이드
    answerer_cfg: dict    # rag.answerer 기본값 + 툴별 오버라이드
    output_schema: PydanticModel | None
    rules: list[Rule] | None
    prompt_template: str | None       # 툴별 프롬프트 오버라이드
    on_failure: str                   # skip | abort_phase | abort_agent

    def run(self, question: str, context: State) -> ToolResult:
        # 1. retriever 실행 (adapter.build_retriever_adapter(cfg))
        # 2. rule 매칭 (있으면 1차 필터링)
        # 3. answerer 실행 (adapter.build_answerer_adapter(cfg))
        # 4. output_schema 검증 (있으면 with_structured_output)
        # 5. ToolResult 반환
```

**설계 결정**:
- Tool은 engine 종류(`langchain`/`local`)와 무관하게 adapter 경로로 동작 → 이원화 해소가 선행 조건
- Rule 엔진은 XL용. 지금은 `PatternRule` stub만 (패턴 리스트 매칭). XL 진입 시 `src/rag/rules.py`로 분리
- `prompt_template`이 있으면 해당 템플릿을 사용, 없으면 `rag.answerer` 기본 템플릿 사용

### 2.3 `src/rag/schema_parser.py` — 신규 (~60L)

**책임**: config의 `output_schema` 이름 → Pydantic model 동적 생성

```python
# config 예시
# output_schema: facts_schema → {"예산": str, "일정": str, "자격요건": str}

BUILTIN_SCHEMAS = {
    "facts_schema":   {"예산": str, "일정": str, "자격요건": list[str]},
    "decision_schema": {"참여여부": bool, "근거": str, "리스크": list[str]},
}

def build_output_schema(schema_name: str) -> type[BaseModel]:
    return create_model(schema_name, **BUILTIN_SCHEMAS[schema_name])
```

**확장**: 추후 config에 inline schema 정의도 지원 가능 (`output_schema: {fields: {...}}`)

### 2.4 `src/rag/adapters.py` — 수정 (+120L)

**변경**: `build_answerer_adapter()`에 openai/ollama 구현체 추가

```python
# 현재 (L316-320)
if mode == "llm" and provider in {"openai", "ollama"}:
    raise NotImplementedError(...)

# → 변경
if mode == "llm" and provider == "openai":
    return OpenAIChatAnswererAdapter(...)
if mode == "llm" and provider == "ollama":
    return OllamaChatAnswererAdapter(...)
```

**신규 클래스**:
- `OpenAIChatAnswererAdapter` — `langchain.chat_models.ChatOpenAI` 기반, `output_schema` 있으면 `with_structured_output()` 호출
- `OllamaChatAnswererAdapter` — `langchain_ollama.ChatOllama` 기반, 동일한 구조
- 두 클래스 모두 `RagAnswererAdapter` Protocol 구현

**호환성**: 기존 `extractive`/`huggingface` 경로 변경 없음.

**추가**: `describe_rag_implementations()`에서 openai/ollama를 `"contract_only"`로 정정 (현재 `"implemented"`로 잘못 표기, `adapters.py:342-343`).

### 2.5 `src/rag/engines/langchain.py` — 수정 (+60L)

**변경**:
1. `answer()` 메서드가 adapter 경로로 통합 (현재 `model.invoke(prompt)` 직통 → adapter 경유)
2. `_build_prompt()` 에 template 파라미터 추가 (fix/answer-quality에서 이미 구현됨)
3. `output_schema`가 config에 있으면 `with_structured_output(schema).invoke(prompt)` 경로로 분기

```python
# langchain.py answer() 변경 (개략)
def answer(self, question, retrieved_chunks):
    adapter = build_answerer_adapter(self.rag_config["answerer"])
    answer = adapter.answer(question, retrieved_chunks)
    # fallback, not_found, citation 처리 유지
    return answer
```

**참고**: 기존 `_build_prompt()` (L375-384), `_citations_from_chunks()` (L387-404), `_parse_used_chunks()` (fix/answer-quality L422-428) 는 재사용.

### 2.6 `src/rag/pipeline.py` — 수정 (+50L)

**변경**: `agent.enabled` 분기만 추가. 기존 경로 **전혀 변경 없음**.

```python
# pipeline.py 신규 함수
def run_rag_agent(config_path, project_root, question=None):
    config = load_config(config_path)
    agent_cfg = config.get("agent", {})
    if not agent_cfg.get("enabled", False):
        return run_rag_chat(config_path, project_root, question)
    
    from src.rag.agent import AgentRunner
    runner = AgentRunner(config, project_root)
    return runner.run(question)
```

**기존 함수 무변경**:
- `run_rag_chat()` — 그대로
- `run_rag_chat_with_history()` — 그대로
- `run_rag_evaluation()` — 그대로 (Agent 모드 evaluation은 별도 구현, XL 진입 시)

**추가 리팩토링**: `_CHAT_HISTORY` 모듈 레벨 글로벌 dict 제거 → `AgentRunner` 인스턴스에 캡슐화하거나 State dict의 `history` 필드로 이관. (병렬 Tool 실행 시 dict 충돌 방지)

### 2.7 `src/rag/validation.py` — 수정 (+40L)

**변경**: `agent:` 섹션 스키마 검증 추가

검증 항목:
- `agent.phases[].name` 필수
- `agent.phases[].depends_on` → 존재하는 phase 이름인지
- `agent.tools.*.description` 필수
- `agent.tools.*.answerer.output_schema` → `BUILTIN_SCHEMAS`에 등록된 이름인지 (또는 inline schema 정의 검증)
- 순환 의존성 체크 (`depends_on` 그래프에 cycle 없는지)
- Phase 간 `input_from` → 존재하는 tool 이름인지
- `tools.*.on_failure` → `skip | abort_phase | abort_agent` 중 하나인지
- `tools.*.answerer.provider`가 명시되지 않은 Tool은 `rag.answerer.provider` 상속 → 상속값이 `local`이면 경고

### 2.8 `src/rag/__init__.py` — 수정 (+5L)

```python
from src.rag.agent import AgentRunner
from src.rag.tool import Tool, ToolResult
```

### 2.9 추가: 한국어 도메인 키워드 Config화

**현재 상태**: `retriever.py:_score()` (L49-54) 와 `answerer.py:_sentence_score()` (L77-82) 에 동일한 한국어 키워드 가중치 로직이 **다른 보너스 값**(1.0 vs 2.0)으로 중복 구현되어 있다.

**변경**:
- `configs/experiments/rag/rag_agent.yaml` 및 모든 RAG config에 `rag.scoring.keyword_weights` 키 추가 (선택적)
- 없으면 기존 하드코딩 가중치 사용 (하위 호환)
- 있으면 config 값으로 오버라이드
- `retriever.py`와 `answerer.py`의 중복 로직을 `src/rag/scoring.py`로 통합

```yaml
rag:
  scoring:
    keyword_weights:
      "예산": 1.0
      "일정": 1.0
      "자격": 1.0
    co_occurrence_bonus: 1.0   # "얼마"+"예산" 동시 등장 시 추가 가중치
```

### 2.10 추가: Judge provider 확장

**현재 상태**: `judge.py:39`가 `langchain_openai.ChatOpenAI`를 하드임포트. Ollama 등 다른 judge backend 사용 불가.

**변경**:
- `judge.py`가 `build_answerer_adapter()`와 동일한 패턴으로 judge backend 선택
- config `evaluation.llm_judge.provider: ollama` 지원

### 2.11 `src/rag/agent_loop_runner.py` — 신규 (~120L)

**책임**: Planner Tool + Executor + Evaluator 를 반복 루프로 수행하는 config 기반 반복 실행 모드

```
AgentLoopRunner
├── agent.enabled: true + agent.loop.enabled: true → loop 진입
├── Planner: agent.tools[].description 기준으로 적절한 Tool 선택 (LLM 기반)
├── Executor: 선택된 Tool 실행 (retrieve → answer → output_schema 검증)
├── Evaluator: ToolResult 평가, 부족하면 다른 Tool 재선택 → max_iterations까지 반복
└── 한 iteration마다 answer + citations + errors 누적 → State에 기록
```

**핵심 로직**:
- `agent.loop.enabled: false` → 기존 AgentRunner Phase DAG 모드로 진행
- `agent.loop.enabled: true` → Plan→Execute→Evaluate 반복 루프 진입
- `agent.loop.max_iterations`로 무한 루프 방지 (기본값 5)
- 각 iteration에서 Planner가 `agent.tools` 중 적절한 Tool을 LLM으로 선택
- Evaluator가 결과 품질을 판단하여 만족 시 early stop, 불충족 시 다른 Tool로 재시도
- State dict에 iteration별 ToolResult를 history로 누적 → 다음 iteration의 context로 활용

**설계 결정**:
- Tool 선택은 `agent.chatbot.tool_selection_model`과 동일한 LLM 사용 → config 일관성
- Evaluator 판정 로직은 기본적으로 `not_found` 감지 + answer 길이 체크 → 필요 시 LLM judge 연동
- `on_failure` 정책과 연계: 한 Tool이 `abort_agent`면 loop 즉시 종료

---

## 3. 호환성 계약

### 3.1 기본 전략

```
config.agent.enabled?
├─ False (기존 config 전부) → 기존 코드 경로 그대로
│   ├─ run_rag_chat()       → pipeline.py 분기만 추가, 내부 로직 무변경
│   ├─ run_rag_evaluation() → pipeline.py 분기만 추가, 내부 로직 무변경
│   └─ build_rag_engine()   → engines/base.py 무변경
│
└─ True (신규 agent config) → AgentRunner 경로
    ├─ agent.py    → Phase DAG 해석
    ├─ tool.py     → Tool 별 retriever+answerer+output_schema
    └─ adapters.py → OpenAI/Ollama answerer (NotImplementedError 해소)
```

**핵심 원칙**: 기존 config 파일을 한 글자도 안 바꾸고, 같은 질문에 같은 답변이 나와야 한다. 검색 결과(`retrieved_chunks`)와 답변(`answer`), citation까지 비트 단위 동일이 목표.

### 3.2 단계별 호환성 위험 추적 (재측정)

**기본값 정책**: 모든 신규 코드는 기존 langchain.py의 동작을 기본값으로 삼는다. 프롬프트 템플릿, context 포맷, scoring 로직 모두 현재 값 그대로 → `agent.enabled: false`인 config는 비트 단위로 동일한 답변을 받는다.

| 구현 단계 | 교차 지점 | 위험 | 근거 |
|----------|----------|:---:|------|
| 1. adapter answerer 추가 | **없음** — 신규 provider만 추가 | 없음 | 기존 extractive/huggingface 분기 앞에 elif 추가 |
| 2. schema_parser | **없음** — agent 모드 전용 | 없음 | |
| 3. scoring.py 통합 | `retriever.py` 등 → import 경로 변경 | **낮음** | 코드 복사 없이 import만 이동. byte-test로 검증 |
| 4. tool.py | **없음** — agent 모드 전용 | 없음 | |
| 5. langchain answerer 통합 | `langchain.py` → adapter 경로 | **낮음** | 기본값 정책으로 해결. `prompt.py`에서 두 곳의 프롬프트를 langchain 현재값으로 통일 → adapter 경로가 기존과 동일한 프롬프트 사용 |
| 6. agent.py | **없음** — agent 모드 전용 | 없음 | |
| 7. pipeline 분기 | `pipeline.py` → `if agent.enabled:` 한 줄 | **없음** | else 경로는 기존 코드 그대로. `_CHAT_HISTORY`는 제거하지 않고 agent 모드에서만 AgentRunner 인스턴스 사용 |
| 8~13 | validation, judge, 문서 | **없음** | 신규 추가 또는 정리 |

### 3.3 진짜 위험: 프롬프트 불일치 → 기본값 정책으로 해결

문제의 본질은 `langchain.py:_build_prompt()`와 `adapters.py:_build_rag_prompt()`의 **프롬프트 내용 차이**였다.

```diff
- adapters.py: "한국어로 짧게 답하라" + "답변:" + context에 source/page/section 포함
+ langchain.py: "한국어로 답하라" + context에 chunk_id + text만
```

**해결책: 1번 브랜치에서 `prompt.py`로 통일, 기본값 = langchain 현재값**

```python
# src/rag/prompt.py (신규)
DEFAULT_PROMPT = """너는 RFP 문서 분석 도우미다. 아래 근거에 있는 내용만 사용해서 한국어로 답하라.
근거에 없는 내용은 추측하지 말고 '문서에서 확인하지 못했습니다.'라고 답하라.

{context}

질문: {question}"""

def build_prompt(question, chunks, template=None):
    template = template or DEFAULT_PROMPT
    context = "\n\n".join(
        f"[근거 {i}]\nchunk_id: {c.get('chunk_id', '')}\n{c.get('text', '')}"
        for i, c in enumerate(chunks, start=1)
    )
    return template.format(context=context, question=question)
```

- `langchain.py` → `prompt.build_prompt()` 사용
- `adapters.py` → `prompt.build_prompt()` 사용 (기존 `_build_rag_prompt` 대체)
- config `rag.answerer.prompt` 있으면 오버라이드 (fix/answer-quality에서 이미 구현)
- Tool별 `prompt_template` → agent 모드에서만 오버라이드

**결과**: 2번 브랜치(`feature/agent-answerer-unification`)는 더 이상 위험 지점이 아니다. 프롬프트가 이미 통일된 상태에서 answer() 라우팅만 adapter로 변경. 동일 입력 → 동일 출력.

### 3.4 호환성 검증 테스트

```
# 1. 기존 테스트 전수 통과 (gate)
python -m pytest tests/ -x

# 2. 동일 config, 동일 질문 → 동일 답변 (regression)
python scripts/run_rag_chat.py \
  --config configs/experiments/rag/rag-baseline.yaml \
  --question "이 사업의 총 예산은 얼마인가?"
# → 통합 전후 answer hash 비교

# 3. 동일 config → 동일 평가 지표 (metric regression)
python -m pytest tests/test_rag_pipeline.py -k "baseline" --regression-baseline
# → retrieval_hit_rate, judge_correct_rate 차이 0.5% 이내

# 4. agent.enabled: false config → pipeline + AgentRunner 경로 모두 답변 일치
# → run_rag_chat() vs run_rag_agent() 결과 answer 필드 동일
```

**기존 테스트 전부 통과가 최소 조건.** Agent 모드 테스트는 별도 추가.

---

## 4. M → L → L+ → XL 서비스 연동

| Tier | 필요 조건 | 제공 방식 |
|------|----------|----------|
| **M** 요약 | `output_schema`, Tool 1개 | `rag_agent.yaml`에서 extract_facts만 Phase 1로 |
| **L** 비교 | 다중 문서, 병렬 Tool | Multi-doc loader + `documents: [...]` config |
| **L+** 추천 | `company_profile.json`, 출력 schema | `check_qualification_gap` + `decide_participation` Phase |
| **XL** 컨설턴트 | Rule 엔진, 외부DB | `scan_unfair_clauses` + `search_similar_bids` Phase |

**Config만으로 전환 목표**: 각 Tier별 config 파일 하나만 선택하면 Agent Loop가 나머지를 해석.

**M ~ L+**: Config만으로 도달 가능. Phase DAG + Tool + Structured Output + company_profile 주입으로 충분.
**XL**: Config + Tool plugin 2~3개 추가 구현 필요 (`RegulatoryCheckTool`, `SimilarBidSearchTool`, `RiskScoringTool`). Phase 체이닝과 State 전파는 Agent Loop가 이미 제공.

---

## 5. 구현 순서 (보정판 — 기본값 정책 반영)

4개 브랜치로 나눠서 진행. `main`에 순차 머지. 각 브랜치 머지 시 기존 테스트 통과 + `rag-baseline.yaml` 지표 변동 ±0.5% 이내가 gate.

### 브랜치 ①: `feature/agent-foundation` (밑작업)

| 순서 | 파일 | 내용 | 위험 |
|------|------|------|:---:|
| 1.1 | `adapters.py` (+120L) | OpenAI/Ollama answerer adapter 추가. 기존 분기 무변경 | 없음 |
| 1.2 | `prompt.py` (+80L, 신규) | `build_prompt()` 통일. `langchain.py`와 `adapters.py`가 같은 함수 사용. 기본값 = langchain 현재 프롬프트 | 없음 |
| 1.3 | `schema_parser.py` (+60L, 신규) | Pydantic 동적 생성. agent 모드 전용 | 없음 |
| 1.4 | `scoring.py` (+80L, 신규) | `_tokenize`/`_score` 이관 + public 전환. `retriever.py`/`answerer.py`/`adapters.py` import 경로만 변경 | 낮음 |
| 1.5 | `tool.py` (+150L, 신규) | Tool wrapper + `on_failure` 로직 | 없음 |

### 브랜치 ②: `feature/agent-answerer-unification` (라우팅 통합)

| 순서 | 파일 | 내용 | 위험 |
|------|------|------|:---:|
| 2.1 | `langchain.py` (+30L) | `answer()` → adapter 경로. 프롬프트는 1.2에서 이미 통일됨 | 낮음 |

### 브랜치 ③: `feature/agent-loop` (에이전트 심장)

| 순서 | 파일 | 내용 | 위험 |
|------|------|------|:---:|
| 3.1 | `agent.py` (+200L, 신규) | Phase DAG + Tool dispatch + State dict (부록 D) | 없음 |
| 3.2 | `pipeline.py` (+30L) | `if agent.enabled:` 한 줄 분기. else는 기존 코드 그대로 | 없음 |

### 브랜치 ④: `feature/agent-polish` (마무리)

| 순서 | 파일 | 내용 | 위험 |
|------|------|------|:---:|
| 4.1 | `validation.py` (+40L) | agent config 검증 + `rag.chunk` deprecation warning | 없음 |
| 4.2 | `judge.py` (+30L) | provider 확장 + try/except | 없음 |
| 4.3 | `scripts/run_rag_agent.py` (+50L, 신규) | Agent CLI | 없음 |
| 4.4 | `langchain.py` (-3L) | `rag.llm` deprecation warning | 없음 |
| 4.5 | `configs/README.md` (+50L) | agent 섹션 문서화 + `rag.chunk`→`rag.splitter` 단일화 안내 | 없음 |
| 4.6 | Dead config 정리 | `backup.*`, `metric.*`, `rag.chunk.unit`, `rag.embedding.normalize` | 없음 |

**체크포인트**:
- ① 완료 → 단일 Tool 실행 가능 (M 서비스)
- ②~③ 완료 → Agent Loop 동작 (L, L+ 서비스)
- ④ 완료 → 전체 통합 + 검증 + 문서화 (XL 진입 가능)

---

## 6. 테스트 전략

| 테스트 대상 | 파일 | 내용 |
|------------|------|------|
| answerer adapter | `tests/test_rag_adapters.py` | OpenAI/Ollama adapter가 기존 contract 만족하는지 |
| output_schema | `tests/test_rag_pipeline.py` (추가) | schema_parser → with_structured_output 호출 검증 |
| Tool | `tests/test_rag_pipeline.py` (추가) | 단일 Tool 실행, config 오버라이드 작동 |
| Agent Loop | 신규 `tests/test_rag_agent.py` | Phase DAG 순서, depends_on, State 전파 |
| 호환성 | `tests/test_rag_pipeline.py` (기존) | `agent.enabled: false` config는 기존과 동일 결과 |
| Judge provider | 신규 `tests/test_rag_judge.py` | Ollama/openai judge backend 교체 |
| Keyword scoring | `tests/test_rag_pipeline.py` (추가) | config 가중치 오버라이드 동작 |

### Smoke test

```bash
python -m pytest tests/test_rag_pipeline.py tests/test_rag_engines.py tests/test_rag_adapters.py -x
```

---

## 7. 리스크

| 리스크 | 완화 |
|--------|------|
| 프롬프트 불일치 (이원화) | **기본값 정책**: `prompt.py`에서 langchain 현재값을 기본값으로 통일. adapter와 langchain이 동일 프롬프트 사용 → 1번 브랜치에서 해결 |
| scoring.py 이관 시 토크나이징 불일치 | import 경로만 변경, 코드 복사 금지. byte-level regression test |
| `agent.enabled: false` config 답변 변동 | 각 브랜치 머지 전 `rag-baseline.yaml` 지표 변동 ±0.5% 이내 gate |
| Agent Loop 무한 루프 | `agent.max_steps: 15` 제한. Phase 수 * Tool 수 초과 시 abort |
| 기존 테스트 회귀 | `python -m pytest tests/ -x` → 브랜치별 머지 gate |
| judge 호출 실패 시 Agent 중단 | `judge.py` try/except 추가 + 실패 로깅 (4번 브랜치) |
| CSV 컬럼명 하드코딩 (L+/XL 진입 시) | `rag.loader.csv_columns` config 키 추가 (XL 진입 시점에 별도 구현) |

---

# 부록 A: 추가 하드코딩/결합 요소 (계획 보강분)

> 2026-06-24 추가 감사에서 식별. 기존 1~10번 외 신규 발견.

### A.1 Config 키 혼선

| # | 위치 | 문제 | 영향 |
|---|------|------|------|
| A1 | `rag.chunk` vs `rag.splitter` 이중 키 네임스페이스 | `rag_langchain.yaml`=splitter, `rag_keyword.yaml`=chunk. 코드는 `get("splitter", get("chunk", {}))`로 2중 fallback | Tool별 chunking 오버라이드 시 어느 키를 써야 하는지 불명확 |
| A2 | `max_tokens` 기본값 불일치 | `adapters.py:312`=256, `validation.py:309`=512 | 검증 통과했는데 런타임 다른 값 사용 |
| A3 | `rag.llm` legacy fallback | `langchain.py:154` `get("answerer", get("llm", {}))` | 미문서화된 dead config key. agent config에서 오용 가능 |

### A.2 Dead config (코드 0회 참조)

| # | Config 경로 | 비고 |
|---|------------|------|
| A4 | `backup.*` | `configs/README.md:361-373`에만 존재. 검증도 실행도 안 됨 |
| A5 | `metric.monitor`, `metric.mode` | 모든 config에 존재하나 코드에서 0회 참조 |
| A6 | `rag.answerer.require_citations` | validation만 하고 LangChain engine에선 읽지 않음 |
| A7 | `rag.chunk.unit` | `rag_keyword.yaml` 등에 있으나 아무 데서도 안 읽음 |
| A8 | `rag.embedding.normalize` | local embedding adapter가 전혀 참조하지 않음 |

### A.3 코드 중복 (리팩토링 대상)

| # | 중복 대상 | 파일 위치 | 비고 |
|---|----------|----------|------|
| A9 | `_dot()` | `adapters.py:392-393`, `vector_store.py:36-37`, `langchain.py:358-359` | 3곳 중복 |
| A10 | `_citations_from_chunks()` | `adapters.py:486-503`, `langchain.py:387-404` | 2곳 중복 |
| A11 | `_resolve_path()` | `pipeline.py:413`, `comparison.py:76`, `validation.py:366`, `document_loader.py:295`, `experiments.py:132` | 5곳 중복 |
| A12 | `_relative_path()` | `comparison.py:81`, `document_loader.py:300`, `experiments.py:124` | 3곳 중복 |
| A13 | retrieval row formatting | `retriever.py:23-35`, `adapters.py:396-406`, `langchain.py:317-331`, `langchain.py:362-372`, `vector_store.py:40-50` | 5곳 중복 |

### A.4 확장성 저해 하드코딩

| # | 위치 | 문제 | Agent 영향 |
|---|------|------|------------|
| A14 | `langchain.py:135` — reranker `max_length=512` 하드코딩 | CrossEncoder 입력 길이 조정 불가 | 긴 문서 분석 시 truncation 손실 |
| A15 | `langchain.py:137` — reranker text `[:400]` 하드코딩 | chunk text 400자로 강제 절단 | |
| A16 | `langchain.py:102` — `fetch_k = top_k * 3` 하드코딩 | reranker prefetch 배율 고정 | |
| A17 | `retriever.py:48-54` — 키워드 스코어 `+0.5`, `+1.0` 하드코딩 | substring/co-occurrence 가중치 고정 | Tool별로 다른 가중치 설정 불가 |
| A18 | `adapters.py:385` — `_score(...) * 0.5` 하드코딩 | semantic + keyword 블렌딩 비율 고정 | |
| A19 | `document_loader.py:124-137` — CSV 컬럼명 "공고 번호", "사업명", "텍스트", "본문" 하드코딩 | 다른 CSV 포맷 사용 불가 | Agent에 다른 입찰 데이터 피드 불가 |
| A20 | `judge.py:39` — `from langchain_openai import ChatOpenAI` 하드임포트 | Judge가 OpenAI 전용 | Agent 평가 단계 provider 일관성 깨짐 |
| A21 | `langchain.py:134` — reranker `model_name or "BAAI/bge-reranker-v2-m3"` 하드코딩 | 모델명 fallback이 코드에 박힘 | |
| A22 | `judge.py:23` — `model_name: str = "gpt-5-mini"` 존재하지 않는 모델명 | 플레이스홀더 오타 | |

### A.5 추가 하드코딩/결합 (2차 감사 신규 발견)

| # | 위치 | 문제 | Agent 영향 | 우선 |
|---|---|---|---|---|
| A23 | `adapters.py:449-469` — `_build_rag_prompt()` | adapter 쪽에도 별도 프롬프트 하드코딩. `langchain.py:375`의 `_build_prompt()`와 **내용이 다른** 템플릿이 2개 공존 | Adapter 경로로 통합 후 모든 Tool이 **이 하드코딩 프롬프트 하나를 강제**당함 → Tool별 `prompt_template` 구현해도 적용 불가 | **높음** |
| A24 | `answerer.py:6`, `adapters.py:10`, `vector_store.py:6` → `from src.rag.retriever import _tokenize, _score` | `retriever.py`의 private 함수(밑줄)를 3곳이 직접 import. retriever 내부 구현 변경 시 연쇄 장애 | `scoring.py` 통합(2.9) 시 자연히 해소되나, 통합 전까지는 **잠재 지뢰** | 중간 |
| A25 | `langchain.py:154` — `get("answerer", get("llm", {}))` | `rag.llm`은 모든 config 문서에 없는 **dead key**. agent config에서 `answerer` 없이 `llm`만 쓰면 의도치 않은 fallback 발생 | 잘못된 config 작성 시 **에러 없이 잘못된 provider로 동작**. Agent config에서 특히 위험 | 중간 |
| A26 | `judge.py:47` — `judge.invoke([HumanMessage(...)])` | network 실패 시 judge 호출에 try/except 없음. **Agent Phase 전체 중단** | Agent 평가 단계가 judge 실패 시 복구되지 않고 전체 abort | 중간 |
| A27 | `pipeline.py:255-259` — `except Exception: pass` | judge 호출 실패를 **완전히 swallow**. 어떤 이유로 judge가 실패했는지 로그 없음 | Agent 평가 시 `judge_correct_rate`가 judge 실패와 실제 오답을 구분하지 못해 **지표 왜곡** | 높음 |
| A28 | `configs/examples/rag/rag_llm_judge.yaml` | LLM Judge 설정이 `configs/examples/`에만 존재. `configs/experiments/rag/README.md:94-127`에 문서화만 되어 있고 **실제 실험 config 파일은 없음** | Agent 평가 config 작성 시 참조할 파일이 없음 | 낮음 |

### A.6 구현 시 버그 위험 (2차 감사)

Agent Loop 구현 과정에서 반드시 터지거나, 터지면 찾기 어려운 지점.

| # | 위치 | 버그 시나리오 | 발생 조건 | 완화 |
|---|---|---|---|---|
| BUG1 | `pipeline.py:174` — `_CHAT_HISTORY` 모듈 레벨 dict | Phase 내 Tool 2개가 동시에 `run_rag_chat_with_history()` 호출 → **dict 경합**, thread_id 충돌 | Agent 모드에서 `agent.enabled: true` + memory enabled | `_CHAT_HISTORY` 제거 + AgentRunner 인스턴스 State dict로 이관 |
| BUG2 | `pipeline.py:132` — retrieve → ingest 자동 호출 | Agent가 retrieve 단계를 분리 호출했는데, `_run_rag_retrieve_checked()` 내부에서 ingest를 중복 실행 → chunk 중복 + checkpoint 꼬임 | Agent Loop에서 retrieve를 Tool로 직접 호출할 때 | pipeline 분기 시 `_run_rag_retrieve_checked` 대신 adapter의 retriever 직접 호출 |
| BUG3 | `langchain.py:153-180` — `answer()` 이원화 | `agent.enabled: false`인 config가 langchain engine을 쓸 때는 자체 answer(), `agent.enabled: true`에서 Tool이 adapter 경로로 answer() 호출 → **같은 config인데 다른 답변** | Adapter 통합 전 과도기 | 부록 C 통합 시나리오를 1순위로 (구현 순서 6단계를 1단계 직후로 당김) |
| BUG4 | `document_loader.py:125-141` — CSV 컬럼명 하드코딩 | Agent가 외부 입찰 CSV를 로드했는데 컬럼명 불일치 → `text` 필드가 빈 배열 → 모든 Tool answer = `""` 또는 fallback | L+/XL 서비스로 갈 때 | `rag.loader.csv_columns` config 키 추가 |
| BUG5 | `configs/README.md:342-343` — `describe_rag_implementations()`가 openai/ollama를 `"implemented"`로 잘못 표기 | 사람이 README 보고 "openai answerer는 구현됐네" → config만 쓰면 된다고 판단 → `NotImplementedError` | Adapter 구현 전 과도기 | `"contract_only"`로 정정 |

---

# 부록 B: Config 인터페이스 평가 및 보강 제안

> `configs/experiments/rag/rag_agent.yaml` + `configs/README.md` 기준.

### B.1 `configs/README.md` 누락 항목

현재 README(396줄)에 아래 항목이 전혀 문서화되어 있지 않다.

| 누락 항목 | 설명 |
|----------|------|
| `agent.enabled` | 에이전트 모드 on/off 플래그 |
| `agent.max_steps` | 전체 루프 제한 |
| `agent.verbose` | Tool 호출 로깅 |
| `agent.phases[]` | Phase 정의, 순서, depends_on, tools 리스트 |
| `agent.tools.*` | Tool별 retriever/answerer 오버라이드, output_schema, rules, prompt_template |
| `tools.*.answerer.output_schema` | Structured Output 스키마 참조 |
| `tools.*.rules.patterns` | Rule 엔진 패턴 |
| `tools.*.input_from` | Phase 간 데이터 흐름 (신규 제안) |
| `tools.*.on_failure` | Tool 실패 처리 정책 (신규 제안) |
| `evaluation.llm_judge` | LLM-as-Judge 설정 (평가 문서에 없음) |

### B.2 `rag_agent.yaml` 인터페이스 부실 지점

| # | 문제 | 현상 | 제안 |
|---|------|------|------|
| B1 | `output_schema` 정의 위치 없음 | `facts_schema`, `decision_schema` 참조만 있고 실제 필드 정의는 config 어디에도 없음 | `agent.schemas` 섹션 추가 또는 inline schema 정의 지원 |
| B2 | Tool별 `prompt_template` 없음 | 모든 Tool이 동일한 하드코딩 프롬프트를 사용하게 됨 | `tools.*.answerer.prompt_template` 키 추가 |
| B3 | Phase 간 데이터 흐름 정의 없음 | `depends_on`은 순서만 정의. "어떤 Tool의 어떤 출력을 받을지"는 정의되지 않음 | `tools.*.input_from: [tool_name, ...]` 또는 Phase 레벨 `output_to` 추가 |
| B4 | Tool 실패 정책 없음 | LLM 호출 실패 시 전체 abort? skip? fallback? 미정의 | `tools.*.on_failure: skip | abort_phase | abort_agent` 추가 |
| B5 | 병렬 실행 제어 없음 | Phase 내 여러 Tool의 병렬/직렬 실행 제어 불가 | `phases[*].parallel: true | false` 추가 |
| B6 | `model_name` 기본값 상속 모호함 | 14개 Tool 중 1개만 `model_name` 명시. 나머지는 `rag.answerer.model_name` 상속? 그런데 기본값이 `provider: local`+빈 model_name → 대부분 extractive로 빠짐. Agent 의도와 불일치 | `rag.answerer.provider: openai` 같은 기본값을 쓰거나, model_name 없는 Tool에 대해 검증 경고 |
| B7 | `evaluation`, `metric` 섹션이 agent config에 포함됨 | Agent 모드 평가는 `run_rag_evaluation()`을 안 타는데, 이 항목이 있으면 평가가 동작한다고 착각 | agent config에서는 이 섹션 제거하거나, agent 전용 평가 섹션 별도 정의 |
| B8 | citation traceability 설계 없음 | Phase 5의 "참여 불가" 판단이 Phase 1의 어떤 chunk에서 왔는지 추적 경로 없음 | State dict에 `{tool_name: {answer, citations[], source_phase, source_tool}}` 메타데이터 추가 |

### B.3 권장 Config 구조 (보강판)

> v5: `base_config` 상속 지원 추가. RAG 검색 config와 Agent 확장 config를 분리하여
> Agent config에서는 `base_config: ../rag-baseline.yaml` 한 줄로 RAG 설정을 상속받을 수 있습니다.
> 이 방식은 `configs/experiments/rag/agent/agent_lplus.yaml`에 예시가 있습니다.

```yaml
agent:
  enabled: false
  max_steps: 15
  verbose: false
  
  # ── structured output 스키마 정의 (신규) ──
  schemas:
    facts_schema:
      fields:
        예산: str
        일정: str
        자격요건: list[str]
        제출서류: list[str]
    decision_schema:
      fields:
        참여여부: bool
        근거: str
        리스크: list[str]
        제안가_범위: str | null

  # ── Phase 정의 ──
  phases:
    - name: extract
      tools: [extract_facts, parse_bid_conditions]
      parallel: true            # 신규: Phase 내 Tool 병렬 실행

    - name: scan
      tools: [scan_unfair_clauses, scan_liability_shift, rate_clause_severity]
      depends_on: [extract]
      parallel: true

    - name: decide
      tools: [decide_participation, suggest_price]
      depends_on: [extract, scan]

  tools:
    extract_facts:
      description: "RFP에서 예산, 일정, 자격, 서류 등 핵심 정보 추출"
      input_from: null          # 신규: 최초 Tool, 입력 없음
      retriever:
        top_k: 10
      answerer:
        provider: openai        # 신규: 명시적 provider (상속 대신)
        model_name: gpt-4o-mini
        output_schema: facts_schema
        prompt_template: |       # 신규: 툴별 프롬프트
          너는 RFP 문서에서 사실 정보만 추출하는 분석기다.
          추측하지 말고, 문서에 명시된 내용만 답하라.
          문서에 없는 정보는 '확인 불가'로 표시하라.
        temperature: 0.1
      on_failure: abort_agent   # 신규: 핵심 Tool 실패 → 전체 중단

    check_qualification_gap:
      description: "우리 회사 보유 자격과 요구 자격 간 갭 분석"
      input_from: [extract_facts]  # 신규: extract_facts 결과만 입력으로
      # retriever 불필요
      answerer:
        provider: openai
        model_name: gpt-4o-mini
        prompt_template: |
          아래 추출된 RFP 자격요건과 우리 회사 프로필을 비교하여 갭을 분석하라.
          {extract_facts_output}
          {company_profile}
        temperature: 0.1
      on_failure: skip           # 신규: 실패해도 다음 Phase 진행
```

---

# 부록 C: 이중 Adapter 체계 통합 계획 (보강)

현재 answerer는 두 갈래로 동작한다.

| 경로 | 사용처 | 지원 provider |
|------|--------|--------------|
| `adapters.py` → `build_answerer_adapter()` | `LocalRagEngine` | extractive, huggingface |
| `langchain.py` → `answer()` 직통 | `LangChainRagEngine` | extractive, ollama, openai |

계획 1단계에서 `adapters.py`에 openai/ollama adapter를 추가해도, `LangChainRagEngine`은 여전히 자체 `answer()`를 쓴다. 즉, **adapter 경로와 langchain 직통 경로가 공존**하게 된다.

### 통합 시나리오 (6단계에서 실행)

```
변경 전:
  LangChainRagEngine.answer()
    ├─ provider=local      → build_answer() 직통
    └─ provider=ollama/openai → _build_chat_model().invoke() 직통

변경 후:
  LangChainRagEngine.answer()
    └─ 모든 provider → build_answerer_adapter(cfg).answer()
```

이렇게 하면:
- `output_schema` → adapter가 `with_structured_output()` 호출
- `prompt_template` → adapter가 템플릿 사용
- Reranker → adapter가 아닌 engine 레벨에서 동작 (retrieve 단계에서 이미 적용됨)
- 기존 `_build_prompt()`, `_citations_from_chunks()` → adapter 쪽으로 이동/통합

### Adapter 통합 후 기대 효과

| 항목 | 통합 전 | 통합 후 |

---

# 부록 F: 구현 평가 — 계획 대비 실적

> 2026-06-25, 4개 브랜치 전수 평가.

## 총평: A (96/100)

핵심 구현 100% 완료, 문서화 완료, 지표 출력 완료, 보류 항목 전부 해소.
2차 감사 버그 5건 수정. 52 tests pass.

> v7 (2026-06-25): 보류 3건 해소. Phase 병렬 실행, scoring 고도화, Agent 평가 구현.
> tool_selection_accuracy, hallucination_avoidance_rate 실제 계산값으로 대체.

## 브랜치별 평가

### ① feature/agent-foundation (밑작업) — ✅ 완료

| 계획 항목 | 계획량 | 실제 | 판정 | 비고 |
|---|---|---|---|---|
| adapters.py OpenAI/Ollama | +120L | 197L 추가 | ✅ | `output_schema` 지원 포함 |
| prompt.py 통일 | 신규 80L | 43L | ✅ | langchain 현재 프롬프트 기본값 |
| schema_parser.py | 신규 60L | 81L | ✅ | BUILTIN_SCHEMAS 3종 + inline 지원 |
| scoring.py 통합 | 신규 80L | 51L | ✅ | retriever/answerer/adapters/vector_store import 정리. v6: scoring_kwargs retriever 경로 연동 |
| tool.py | 신규 150L | 176L | ✅ | OnFailure Enum, build_tool_from_config. v6: prompt_template answerer 주입 |

### ② feature/agent-answerer-unification (통합) — ✅ 완료

| 계획 항목 | 계획량 | 실제 | 판정 | 비고 |
|---|---|---|---|---|
| langchain answer() → adapter | +30L | -64L (순삭감) | ✅ | provider=local 제외 전부 adapter 경로 |
| _build_chat_model 제거 | - | 완료 | ✅ | adapter로 이관 |
| _build_prompt 등 dead code 제거 | - | 완료 | ✅ | _citations_from_chunks, _parse_used_chunks 이관 |

### ③ feature/agent-loop (에이전트 심장) — ✅ 완료

| 계획 항목 | 계획량 | 실제 | 판정 | 비고 |
|---|---|---|---|---|
| agent.py Phase DAG + Tool dispatch | 신규 200L | 191L | ✅ | topological sort, State dict, `on_failure` 처리 |
| pipeline.py agent.enabled 분기 | +30L | 43L | ✅ | `run_rag_agent()`, dict/config_path 모두 지원 |

### ④ feature/agent-polish (마무리) — ✅ 완료

| 계획 항목 | 계획량 | 실제 | 판정 | 비고 |
|---|---|---|---|---|
| validation.py agent 검증 | +40L | 71L | ✅ | phase/tool/schema/on_failure 전부 검증 |
| judge.py provider 확장 | +30L | 완료 | ✅ | ollama/openai 분기 + try/except |
| scripts/run_rag_agent.py | 신규 50L | 45L | ✅ | CLI 구현 |
| langchain.py rag.llm deprecation | -3L | 완료 | ✅ | DeprecationWarning |
| dead code 제거 | - | -73L | ✅ | langchain.py에서 _build_* 4종 제거 |
| configs/README.md agent 문서화 | +50L | +91L | ✅ | 10종 키, base_config 상속 문서화 |
| dead config 정리 | - | 7파일 | ✅ | metric.*, embedding.normalize deprecation 주석 |
| scoring.py config 연동 | - | +77L | ✅ | keyword_weights, co_occurrence_bonus, substring_bonus |
| tests/test_rag_agent.py | 신규 | 6건 | ✅ | DAG, 실행, max_steps, ToolNotFound, disabled |
| load_config base_config 상속 | 신규 | +30L | ✅ | 연쇄 상속 + deep merge |
| agent/agent_lplus.yaml | 신규 | 완료 | ✅ | L+ 시나리오 예시 config |
| Agent 산출물 + 지표 | 신규 | +110L | ✅ | agent_state.jsonl, agent_metrics.json 7종 지표 |

## 보류 항목 — v7에서 전부 해소

| 항목 | 사유 | 상태 |
|---|---|---|
| Phase 병렬 실행 (`parallel: true`) | 검증 부담 | ✅ 구현 (ThreadPoolExecutor, _run_single_tool) |
| Scoring 가중치 고도화 | semantic/hybrid 경로 미연동 | ✅ 구현 (전체 retriever 경로 scoring_kwargs) |
| Agent 전용 평가 (D.3) | 평가셋 기반 judge 연동 | ✅ 구현 (run_rag_agent_evaluation) |

## 2차 감사 — 발견 및 수정 (v6)

| # | 버그 | 파일:라인 | 영향 | 판정 |
|---|---|---|---|---|
| BUG1 | `resolve_output_schema`가 config의 inline schemas 완전히 무시 | `schema_parser.py:69-81` | config에서 정의한 커스텀 스키마 필드가 BUILTIN으로 대체됨 | ✅ 수정 |
| BUG2 | Phase DAG cycle 시 `set(self.phases)` TypeError crash | `agent.py:163` | dict unhashable → Agent 전체 중단 | ✅ 수정 |
| BUG3 | `build_answerer_adapter`가 `prompt` 키만 읽고 `prompt_template` 무시. Tool의 `prompt_template`도 answerer 미주입 | `adapters.py:458`, `tool.py:171` | 커스텀 프롬프트 완전히 무시됨 | ✅ 수정 |
| BUG4 | `build_scoring_kwargs()` retriever 경로 미호출 | `retriever.py:18` | `rag.scoring.*` config가 검색 점수에 반영 안 됨 | ✅ 수정 |
| BUG5 | `build_retriever_adapter`가 `similarity`, `mmr` 미지원 | `adapters.py:436` | `rag-baseline.yaml` 상속 agent config에서 `NotImplementedError` crash | ✅ 수정 |

**중간 우선순위 이슈 (보류)**:
- `adapters.py` vs `prompt.py` 프롬프트 템플릿 내용 불일치 (짧게 누락, source_path 포함 여부) — `_build_rag_prompt`는 HuggingFace 전용, OpenAI/Ollama는 `_build_answer_prompt`(prompt.py) 사용. 분리 경로이므로 영향 없음.
- `adapters.py` not_found 감지 로직 불일치 (부분문자열 vs 정확비교) — HuggingFace와 OpenAI/Ollama 경로 분리. 유지보수 시 혼란 가능성만 존재.
- `run_rag_agent.py --verbose` dead flag — config의 `agent.verbose`로 대체. CLI 플래그 제거 예정.

## 변경 통계

```
신규 파일: prompt.py, schema_parser.py, scoring.py, tool.py, agent.py
           run_rag_agent.py, test_rag_agent.py,
           agent/agent_lplus.yaml, rag_agent_demo.yaml
           reports/agent_loop_implementation_plan.md
수정 파일: adapters.py, langchain.py, pipeline.py, retriever.py,
           answerer.py, vector_store.py, validation.py, judge.py,
           __init__.py, config.py, configs/README.md,
           configs/experiments/rag/*.yaml (7개),
           test_rag_adapters.py, test_rag_quality_gate.py,
           test_rag_engines.py
테스트: 52 passed, 하위호환성 byte-level 검증 완료
```
|------|---------|---------|
| answerer provider 추가 | 2곳 수정 필요 (adapters.py + langchain.py) | 1곳만 수정 (adapters.py) |
| output_schema 적용 | langchain engine에서 불가 | 모든 engine에서 가능 |
| prompt_template 적용 | 불가 | 모든 engine에서 가능 |
| Tool 연동 | 경로 분기 필요 | adapter 경로로 단일화 |

---

# 부록 D: Agent State 명세 + CLI 설계 (누락 설계 포인트)

## D.1 Agent State dict 최소 필드 명세

Phase 간 Tool 결과를 주고받는 State dict의 스키마. `reports/` 보고서의 B3(`input_from`), B8(`citation traceability`)과 직결.

```python
# src/rag/agent.py — State 타입
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ToolResult:
    tool_name: str
    phase_name: str
    status: str                      # "ok" | "failed" | "skipped"
    answer: str                      # LLM 원시 응답 텍스트
    structured_output: dict | None   # output_schema 적용된 Pydantic dict
    citations: list[dict]            # [{"chunk_id", "document_id", "text_snippet", "score"}]
    errors: list[str]                # 실패 사유 누적 (비어있으면 정상)
    started_at: str
    finished_at: str
    duration_ms: int
    retry_count: int

@dataclass
class PhaseResult:
    phase_name: str
    tools: dict[str, ToolResult]     # {tool_name: ToolResult}
    status: str                       # "ok" | "partial" | "failed"

# AgentRunner 내부
class AgentRunner:
    state: dict[str, ToolResult]      # tool_name → ToolResult (전체 누적)
    phase_results: list[PhaseResult]  # Phase 순서대로 누적
```

**설계 결정**:
- `structured_output`가 있으면 `answer`보다 이걸 우선 사용 (다음 Phase Tool의 `input_from`이 이걸 참조)
- `citations`에 `text_snippet`을 같이 넣어 Phase 간 citation 추적 가능하게 (B8 해결)
- `errors`는 빈 배열이면 정상. Tool 실패 + `on_failure: skip`이면 errors 누적 후 다음 Phase 진행

## D.2 Agent 모드 전용 CLI 설계

현재 `scripts/run_rag_chat.py`는 단일 질문 + 단일 config 전용. Agent 모드는 진입점 필요.

```bash
# 단일 질문
python scripts/run_rag_agent.py \
  --config configs/experiments/rag/rag_agent.yaml \
  --question "이 RFP의 예산은 얼마인가?"

# 배치 모드 (평가용)
python scripts/run_rag_agent.py \
  --config configs/experiments/rag/rag_agent.yaml \
  --input-file /shared/data/eval_questions.csv \
  --output-dir experiments/rag_agent_eval

# Phase별 중간 산출물 덤프
python scripts/run_rag_agent.py \
  --config configs/experiments/rag/rag_agent.yaml \
  --question "..." \
  --verbose \
  --dump-state       # 각 Phase 완료 시점 State dict를 JSONL로 저장
```

**구현 위치**: `scripts/run_rag_agent.py` 신규 (~50L). 내부에서 `AgentRunner` import → `run_rag_agent()` 호출.

## D.3 Agent 전용 평가 설계

기존 `run_rag_evaluation()`은 `pipeline.py:243`에서 retrieve → answer 하드코딩. Agent 모드 평가는 Phase DAG 전체를 실행하고, 마지막 Phase의 특정 Tool 결과를 평가 지표로 삼아야 한다.

```yaml
# rag_agent.yaml 평가 섹션 확장 (B7 해결)
agent:
  evaluation:
    enabled: true
    questions_path: /shared/data/eval_questions.csv
    target_tool: compile_report       # 이 Tool의 결과를 평가 (기본값: 마지막 Phase 마지막 Tool)
    target_field: answer              # answer | structured_output.<key>
    llm_judge:
      enabled: true
      provider: ollama                # ← judge provider 확장 (2.10)
      model_name: gemma3:latest
```

**주의**: `rag_agent.yaml` 최상위 `evaluation:`과 `metric:` 섹션은 Agent 모드에서 **무시**되어야 한다(B7). `agent.evaluation`이 전용 섹션으로 대체.

---

# 부록 E: 변경 이력

| 버전 | 일자 | 내용 |
|------|------|------|
| v1 | 2026-06-24 | 최초 작성. Config → 코드 갭 10건 + 구현 8항목 |
| v2 | 2026-06-24 | 부록 A~C 추가 (2차 감사: 하드코딩 28건, Config 평가, Adapter 통합) |
| v3 | 2026-06-24 | 부록 D~E 추가 (State 명세, CLI, 구현 순서 보정) |
| v4 | 2026-06-24 | **기본값 정책 적용**. 위험도 전면 재측정 → 4개 브랜치 구조로 단순화. 3.2~3.3, 5절, 7절 갱신 |
| v5 | 2026-06-25 | **리뷰 반영**: 4건 보완 (configs/README.md agent 문서화, dead config 정리, scoring.py config 연동, test_rag_agent.py 추가). **load_config base_config 상속** 구현. agent/ 디렉터리 예시 config 추가. |
| v6 | 2026-06-25 | **2차 감사 버그 수정**: 5건 (inline schema 무시, Phase DAG cycle crash, prompt_template 키 불일치, scoring retriever 미연동, similarity/mmr 미지원). Agent 산출물 지표 추가. |
| v7 | 2026-06-25 | **보류 3건 해소**: Phase 병렬, scoring 고도화, Agent 평가. tool_selection_accuracy/hallucination_avoidance_rate 실제 계산. |
| v8 | 2026-06-25 | **챗봇 지원**: ChatbotRunner(LLM 동적 Tool 선택), agent.chatbot.enabled, CLI 루프. 3차 리뷰 버그 5건 수정. A (96/100). |
| v9 | 2026-06-25 | **통합 감사 해소**: 32건 이슈(🔴6 🟠6 🟡10 🟢10) 전수 수정. 15 fix 커밋. 55 tests pass. 실패 가시성 강화(ValueError/errors/artifact_status). 파생 버그 2건 추가 수정. |
| v10 | 2026-06-29 | **AgentLoopRunner 구현**: Plan→Execute→Evaluate 반복 루프. `agent.loop.*` config 신설. |
| v11 | 2026-06-29 | **확장 구현**: Ollama/OpenAI embedding adapters. Chatbot input_from 자동 연쇄. _format_tool_result() + citation 확장. 대화 메모리. 한국어 키워드 fallback. 20개 문서 갱신. 55 passed. |
| v12 | 2026-06-29 | **서비스 Tool 구현**: extract_requirements, search_rfp_documents, compare_rfps config 기반 추가. BM25+RRF hybrid search 머지. C2 업무형 RFP 챗봇 완성. |

---

# 부록 G: 최종 구현 상태 (2026-06-29)

## 신규 모듈 (12개)
`agent.py`, `tool.py`, `chatbot.py`, `prompt.py`, `schema_parser.py`, `scoring.py`, `judge.py`, `run_rag_agent.py`, `test_rag_agent.py`, `agent_lplus.yaml`, `agent_loop.yaml`, `rag_agent_demo.yaml`

## 확장 구현 (5개)
OllamaEmbeddingAdapter, OpenAIEmbeddingAdapter, AgentLoopRunner, BM25+RRF hybrid search, input_from auto-chain

## 챗봇 Tool (5개)
extract_facts, extract_requirements, decide_participation, search_rfp_documents, compare_rfps

## 버그 수정 (32건)
치명 8 + 높음 12 + 중간 12

## 문서 갱신 (20+개)
docs/llm/ 4, docs/team/ 8, docs/md/ 6, configs/README.md, src/rag/README.md, reports/PM/

## Config 기반 모드 전환
`agent.enabled: false` → RAG 기본
`agent.enabled: true` → Phase DAG
`agent.chatbot.enabled: true` → Chatbot
`agent.loop.enabled: true` → Agent Loop (Plan→Execute→Evaluate)

## 테스트
55 passed, RAG 회귀 없음, 하위호환성 유지

---

# 부록 H: Fix 로그 — 15건

> v9 기준. `feature/agent-polish` 브랜치의 모든 fix 커밋 연대기.

| # | 커밋 | 내용 |
|---|------|------|
| 1 | `2ebfc01` | 치명: 문서 chunk 로딩, structured_output 보존, adapter payload |
| 2 | `8b1cb6e` | chunks.csv 로딩으로 수정 |
| 3 | `807754d` | 치명 6건: state context, eval output_dir, Pydantic model_dump, not_found status, structured_output 포함, nested JSON |
| 4 | `209aca7` | 높음 5건: chatbot chunks, embedding config, answerer on_failure, retry partial, judge word boundary |
| 5 | `d560d82` | #14 chatbot LLM 실패 진단 stderr |
| 6 | `c72061f` | #18 judge import re + normalized 토큰 비교 |
| 7 | `e84eaa8` | 중간 10건: dead code, StopIteration, schema 경고, json 방어, rules 타입체크, answer 절단 |
| 8 | `e4891a9` | #25 output_dir guard + #24 model_name warning |
| 9 | `4c7326c` | 실패 가시성 3건: model_name ValueError, schema errors 기록, artifact_status |
| 10 | `afd383c` | 경미 9건: abort 주석, prompt KeyError, enum 비교, DAG wording, 코드 스타일 |
| 11 | `035d6dd` | 파생 버그: OnFailure/write_json import, abort_phase 회귀 테스트 |
| 12 | `f192e38` | BUG4 _CHAT_HISTORY, BUG5 DAG cycle |
| 13 | `bae0957` | 3차 리뷰: scoring 경로, mode 정정, CLI dead flag |
| 14 | `5505138` | 감사 5건 버그 수정 |
| 15 | `068af9d` | 챗봇 4건: provider 분기, JSON 강건화, 히스토리 주입 |
