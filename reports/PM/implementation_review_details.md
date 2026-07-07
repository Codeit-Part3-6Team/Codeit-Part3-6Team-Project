# 구현 리뷰 상세 보고서

> 작성일: 2026-07-05  
> 대상: RAG/Chroma/SQLite 전환, Streamlit 내부 문서 분석 서비스  
> 기준 문서: `reports/PM/checklist_and_improvement_plan.md`

---

## 1. 요약

현재 구현은 SQLite run/document 저장소, Chroma retriever adapter, Streamlit 전용 config, 비동기 ingest, structured output 분리 등 큰 방향은 반영되어 있습니다.

다만 데모 품질에 직접 영향을 줄 수 있는 핵심 리스크가 남아 있습니다.

1. Chroma 모드에서 선택 문서 필터가 적용되지 않습니다.
2. 챗봇 cache/state 구조 때문에 답변과 출처가 섞일 수 있습니다.
3. Tool dependency 결과가 질문 단위로 초기화되지 않습니다.
4. Chroma persist 디렉터리와 `embeddings.jsonl` resume 상태가 불일치할 수 있습니다.
5. config 상속 실패가 조용히 무시됩니다.
6. 문서/체크리스트 일부가 실제 구현 상태보다 앞서 있습니다.

---

## 2. 우선순위별 상세 이슈

### P1-1. Chroma 모드에서 선택 문서 필터가 적용되지 않음

**관련 파일**

- `app/services/rag_service.py`
  - `_filter_bot_documents()`
  - `ask_with_document_filter()`
  - `run_tool()`
- `src/rag/adapters.py`
  - `ChromaRetrieverAdapter.retrieve()`
- `app/views/workspace.py`
  - `chat_ask(question, ss.run_id, selected_ids or None, titles)`

**현재 동작**

`ask_with_document_filter()`와 `run_tool()`은 `selected_doc_ids`를 받지만, Chroma 모드에서는 `_filter_bot_documents()`가 바로 `True`를 반환합니다.

```python
if getattr(bot, "_use_chroma", False):
    return True
```

그리고 실제 Chroma 검색은 전체 컬렉션을 대상으로 수행됩니다.

```python
rows = store.similarity_search_with_score(question, k=self.top_k)
```

**문제 시나리오**

1. 사용자가 문서 A만 선택합니다.
2. 워크스페이스는 "선택한 문서 범위에서 검색"이라고 안내합니다.
3. 질문: "사업 예산은?"
4. Chroma는 문서 A가 아니라 전체 컬렉션에서 가장 유사한 chunk를 검색합니다.
5. 문서 B 또는 C의 예산과 citation이 응답에 섞일 수 있습니다.

**영향**

- 단일 문서 요약이 다른 문서 기준으로 생성될 수 있습니다.
- 비교 분석에서 각 문서별 요약이 실제로는 전체 corpus 검색 결과가 될 수 있습니다.
- 데모 시나리오의 신뢰도가 크게 떨어집니다.

**권장 수정**

Chroma retriever config에 `document_ids` 필터를 전달하고, `ChromaRetrieverAdapter.retrieve()`에서 `where` 조건을 사용합니다.

예상 방향:

```python
where = None
if self.document_ids:
    where = {"document_id": {"$in": self.document_ids}}
rows = store.similarity_search_with_score(question, k=self.top_k, filter=where)
```

LangChain Chroma API 버전에 따라 인자명이 `filter`인지 `where`인지 확인해야 합니다.

**테스트 포인트**

- Chroma adapter fake store를 만들어 `selected_doc_ids=["doc-a"]`일 때 filter가 전달되는지 검증
- `summarize(run_id, ["doc-a"])` 결과 citation의 `document_id`가 모두 `doc-a`인지 검증
- `compare(run_id, ["doc-a", "doc-b"])`가 각 문서별로 다른 필터를 적용하는지 검증

---

### P1-2. Cache hit 시 답변과 citation/structured_output이 섞일 수 있음

**관련 파일**

- `src/rag/chatbot.py`
  - `chat()`
  - `_cache`
- `app/services/rag_service.py`
  - `ask()`
  - `ask_with_document_filter()`
  - `_get_state_result()`

**현재 동작**

`ChatbotRunner.chat()`의 cache key는 질문 문자열뿐입니다.

```python
cache_key = user_input.strip()
```

cache hit 시에는 cached response를 그대로 반환합니다.

```python
return cached
```

하지만 서비스 레이어는 citation/structured_output을 cached payload에서 직접 꺼내지 않고, 현재 `bot.state`에서 다시 조회합니다.

```python
tool_result = bot.state[tool_name]
citations = _dedupe_citations(list(tool_result.citations))
structured_output = tool_result.structured_output
```

**문제 시나리오**

1. 질문 Q1: "예산은?"
2. `extract_facts` 실행 후 `bot.state["extract_facts"]`에 Q1 결과 저장
3. 질문 Q2: "마감일은?"
4. 같은 tool이 실행되어 `bot.state["extract_facts"]`가 Q2 결과로 덮임
5. 다시 질문 Q1: "예산은?"
6. cache hit로 reply는 Q1 답변 반환
7. citation/structured_output은 현재 state의 Q2 결과를 사용

**영향**

- 답변 본문과 출처가 서로 다른 질문 기준이 될 수 있습니다.
- UI는 citation을 별도 표시하므로 사용자가 바로 발견할 수 있는 회귀입니다.

**권장 수정**

cache payload에 아래 데이터를 함께 저장하고, service layer는 cache hit 여부와 무관하게 response payload를 신뢰하도록 정리합니다.

```python
{
  "reply": str,
  "tool_used": list[str] | str | None,
  "tool_result": dict | None,
  "structured_output": dict | None,
  "citations": list[dict],
}
```

또는 `bot.chat()`은 항상 최종 `ToolResult`를 포함해 반환하고, `rag_service.ask()`가 `bot.state`를 재조회하지 않도록 바꿉니다.

**테스트 포인트**

- Q1 실행 → Q2 실행 → Q1 cache hit 순서로 호출
- Q1 cache hit 응답의 citation이 Q1 최초 citation과 동일한지 검증
- selected doc이 다른 동일 질문의 cache가 분리되는지 검증

---

### P1-3. Cache key가 문서 범위를 포함하지 않음

**관련 파일**

- `src/rag/chatbot.py`
  - `chat()`
- `app/services/rag_service.py`
  - `ask_with_document_filter()`

**현재 동작**

질문 문자열만 cache key로 사용합니다.

```python
cache_key = user_input.strip()
```

**문제 시나리오**

1. 문서 A를 선택하고 "예산은?" 질문
2. 문서 B를 선택하고 동일하게 "예산은?" 질문
3. 같은 cache key를 사용하면 문서 A 기준 응답이 문서 B 선택 상태에서 재사용될 수 있습니다.

현재 `ask_with_document_filter()`는 selected docs가 있으면 `_build_chatbot()`로 새 bot을 만들기 때문에 일부 완화되지만, 구조적으로 cache contract가 질문+문서범위를 보장하지 않습니다. 향후 `_get_or_build_chatbot()` 재사용이나 Chroma filter 도입 시 다시 문제가 됩니다.

**권장 수정**

cache key에 문서 범위를 포함합니다.

```python
cache_key = hash((question.strip(), tuple(sorted(selected_doc_ids or []))))
```

이를 위해 `ChatbotRunner.chat()`에 `scope` 또는 `selected_doc_ids` 인자를 추가하거나, service layer에서 cache를 관리하는 방식으로 정리합니다.

**테스트 포인트**

- 동일 질문 + 다른 selected_doc_ids가 서로 다른 cache entry를 사용하는지 검증

---

### P1-4. Tool dependency 결과가 질문별로 초기화되지 않음

**관련 파일**

- `src/rag/chatbot.py`
  - `_run_agent_loop()`
  - `_run_tool_with_retry()`
- `src/rag/tool.py`
  - `input_from`

**현재 동작**

Tool이 `input_from` dependency를 가지면, 해당 dependency가 `self.state`에 없는 경우에만 실행합니다.

```python
for dep_name in tool.input_from:
    if dep_name not in self.state:
        dep_tool = self.tools.get(dep_name)
        if dep_tool:
            dep_result = self._run_tool_with_retry(dep_tool, user_input)
            self.state[dep_name] = dep_result
```

**문제 시나리오**

1. 질문 Q1: "이 사업 참여해도 돼?"
2. `decide_participation` 실행 전 `extract_facts`가 실행되어 Q1 정보 저장
3. 질문 Q2: "다른 사업 참여 가능성 봐줘"
4. `extract_facts`가 이미 `state`에 있으므로 재실행하지 않음
5. Q2 판단에 Q1의 facts가 사용됨

**영향**

- 참여 판단, 리스크 판단, 후속 분석 결과가 이전 질문 문맥에 오염될 수 있습니다.
- 대화형 챗봇에서 가장 위험한 상태 공유 버그입니다.

**권장 수정**

질문 단위 scratch state와 장기 대화 memory를 분리합니다.

예상 방향:

```python
run_state: dict[str, ToolResult] = {}
```

`_run_agent_loop()` 내부에서는 `run_state`를 사용하고, 필요한 경우에만 최종 결과를 `self.state`에 기록합니다.

**테스트 포인트**

- `decide_participation`을 서로 다른 질문으로 두 번 실행
- 두 번째 실행에서 dependency tool이 다시 호출되는지 검증

---

### P1-5. `base_config` 경로가 틀려도 조용히 무시됨

**관련 파일**

- `src/config.py`
  - `load_config()`
- `configs/experiments/rag/streamlit.yaml`
- `configs/experiments/rag/agent/agent_lplus.yaml`

**현재 동작**

`base_config`가 존재하지만 파일이 없으면 아무 에러 없이 현재 config만 반환합니다.

```python
if base_config:
    base_path = config_path.parent / str(base_config)
    if base_path.exists():
        base = load_config(base_path)
        merged = _deep_merge(base, loaded)
        return merged
return loaded
```

**문제 시나리오**

1. `streamlit.yaml`의 `base_config: agent/agent_lplus.yaml` 경로가 오타로 깨짐
2. `load_config()`는 에러를 내지 않음
3. `rag.answerer`, `rag.embedding`, `agent.tools` 등이 누락된 config가 런타임으로 전달됨
4. 실제 실패는 훨씬 뒤에서 `KeyError`, 빈 tool, provider 누락 같은 형태로 발생

**영향**

- config 기반 실험 파이프라인의 신뢰성이 떨어집니다.
- 팀원이 config 오타를 빠르게 찾기 어렵습니다.

**권장 수정**

`base_config`가 명시되어 있으면 파일 미존재는 `FileNotFoundError`로 처리합니다.

```python
if base_config and not base_path.exists():
    raise FileNotFoundError(f"base_config not found: {base_path}")
```

**테스트 포인트**

- 없는 `base_config`를 가진 임시 YAML 로드 시 `FileNotFoundError` 발생 검증

---

### P2-1. Chroma persist와 `embeddings.jsonl` resume 상태가 불일치할 수 있음

**관련 파일**

- `src/rag/pipeline.py`
  - `run_rag_ingest()`
- `src/rag/engines/langchain.py`
  - `_persist_vector_store()`
  - `_load_vector_store()`

**현재 동작**

ingest resume에서 `embeddings.jsonl`이 있으면 `engine.embed_chunks()`를 건너뜁니다.

```python
if resume_enabled and embeddings_path.exists():
    embeddings = _read_jsonl(embeddings_path)
else:
    embeddings = engine.embed_chunks(chunks)
```

Chroma persist는 `engine.embed_chunks()` 내부에서 생성됩니다.

```python
self._persist_vector_store(chunks, embeddings)
```

**문제 시나리오**

1. `embeddings.jsonl`은 존재
2. `vector_store/` 디렉터리는 삭제되었거나 백업에서 누락
3. resume 실행 시 embedding 단계 skip
4. Chroma index가 재생성되지 않음
5. 검색 시 빈 Chroma 또는 로드 실패 발생

**권장 수정**

vector_store가 Chroma인 경우 resume 조건에 Chroma persist 존재 여부도 포함합니다.

예상 방향:

```python
if vector_store.type == "chroma" and not chroma_persist_exists:
    embeddings = engine.embed_chunks(chunks)
```

또는 Chroma persist 검증 함수를 만들어 ingest 시작 시 artifact consistency check를 수행합니다.

**테스트 포인트**

- `embeddings.jsonl`만 있고 Chroma dir이 없는 상태에서 ingest 재실행
- Chroma persist가 다시 생성되는지 검증

---

### P2-2. `RAG_MODE=rag` 강제 모드가 없음

**관련 파일**

- `app/services/frontend_adapter.py`
  - `_load_rag()`

**현재 동작**

`RAG_MODE=mock`만 처리합니다.

```python
forced_mode = os.environ.get("RAG_MODE", "").lower()
if forced_mode == "mock":
    ...
```

**문제 시나리오**

1. 데모/운영에서 반드시 RAG 연결 상태로 실행해야 함
2. 의존성 누락이나 import 오류 발생
3. 앱은 Mock으로 fallback
4. 배너는 뜨지만 사용자가 놓치면 Mock 응답을 실제 RAG로 착각할 수 있음

**권장 수정**

`RAG_MODE=rag`일 때는 fallback하지 않고 오류를 명확히 반환하거나 앱 상단에 fatal 상태를 표시합니다.

예상 정책:

- `RAG_MODE=mock`: 강제 Mock
- `RAG_MODE=rag`: RAG import 실패 시 healthy false + 문서 목록 차단
- 미설정: 자동 감지 + Mock fallback

**테스트 포인트**

- `RAG_MODE=rag` + import 실패 상황에서 `backend_mode()["healthy"] == False`
- `internal_corpus()`가 mock docs를 반환하지 않는지 검증

---

### P2-3. 내부 corpus 목록 cache가 앱 실행 중 갱신되지 않음

**관련 파일**

- `app/services/frontend_adapter.py`
  - `internal_corpus()`
- `app/views/documents.py`

**현재 동작**

`internal_corpus()`는 첫 결과를 `_corpus_cache`에 저장합니다.

```python
if _corpus_cache is not None and not force_refresh:
    return _corpus_cache
```

documents 화면에서는 `force_refresh=True`를 전달하지 않습니다.

**문제 시나리오**

1. 앱 실행
2. 아직 corpus 없음 또는 문서 1건짜리 test run만 있음
3. 이후 `build_internal_corpus.py`로 98건 ingest 완료
4. 앱을 새로 시작하지 않으면 목록이 갱신되지 않음

**권장 수정**

documents 화면에 새로고침 버튼을 추가하거나, `list_runs()`의 최신 timestamp를 보고 cache invalidation을 수행합니다.

간단한 방향:

```python
if st.button("문서 목록 새로고침"):
    corpus = internal_corpus(force_refresh=True)
```

**테스트 포인트**

- 첫 호출 이후 rag.list_runs 결과가 바뀌었을 때 force refresh로 새 문서 목록 반환 검증

---

### P2-4. Async ingest 실패가 progress API에 명확히 반영되지 않음

**관련 파일**

- `app/services/rag_service.py`
  - `create_and_ingest()`
  - `get_ingest_progress()`

**현재 동작**

비동기 worker 실패 시 SQLite run status만 `failed`로 바꿉니다.

```python
except Exception as exc:
    logger.error("Async ingest failed for %s: %s", run_id, exc)
    sqlite_store.update_run_status(run_id, "failed")
```

`get_ingest_progress()`는 `run_status.json`의 success만 별도 처리하고, 실패 상태는 반환하지 않습니다.

```python
if data.get("status") == "success":
    return {"stage": "ready", "progress": 1.0, "message": "분석 완료"}
```

**문제 시나리오**

1. 비동기 ingest 실패
2. UI가 progress API를 polling
3. 실패 메시지 대신 checkpoint 기준 처리 중 또는 대기 중으로 보임

**권장 수정**

`run_status.json`의 failed 상태와 SQLite status failed를 모두 확인해 progress에 반영합니다.

예상 반환:

```python
{"stage": "failed", "progress": 1.0, "message": "분석 실패", "error": "..."}
```

**테스트 포인트**

- failed `run_status.json` fixture
- SQLite failed status만 있는 fixture
- 둘 다 progress stage가 failed인지 검증

---

### P2-5. `list_runs()`가 DB run이 있으면 파일시스템 run을 숨김

**관련 파일**

- `app/services/rag_service.py`
  - `list_runs()`

**현재 동작**

SQLite run이 하나라도 있으면 파일시스템 fallback을 수행하지 않습니다.

```python
db_runs = sqlite_store.list_runs()
if db_runs:
    return db_runs
```

**문제 시나리오**

1. 기존 `experiments/streamlit/*`에 과거 run이 있음
2. SQLite에는 신규 test run 1개만 있음
3. UI는 DB run만 보고 기존 corpus run을 후보에서 제외

**권장 수정**

DB run과 파일시스템 run을 merge하고, 동일 run_id는 DB metadata를 우선합니다.

**테스트 포인트**

- DB run 1개 + filesystem run 1개 공존 시 둘 다 반환되는지 검증

---

### P2-6. Agent DAG에서 존재하지 않는 dependency가 조용히 무시됨

**관련 파일**

- `src/rag/agent.py`
  - `_resolve_dag()`

**현재 동작**

`depends_on`에 없는 phase 이름이 있어도 무시합니다.

```python
if dep in phase_map:
    adj[dep].append(phase["name"])
    in_degree[phase["name"]] += 1
```

**문제 시나리오**

1. YAML에 `depends_on: [extract_fact]` 오타
2. 실제 phase 이름은 `extract`
3. dependency가 없는 것으로 처리되어 phase가 먼저 실행될 수 있음

**권장 수정**

존재하지 않는 dependency는 config validation에서 warning 또는 error로 처리합니다.

**테스트 포인트**

- 없는 phase dependency를 가진 agent config에서 validation warning/error 검증

---

### P3-1. `app/README.md`가 현재 UI 구조와 맞지 않음

**관련 파일**

- `app/README.md`
- `app/views/`

**현재 문서**

README에는 `analyze.py`, 업로드 기반 `create_and_ingest(temp_dir)`, `rag_contract_demo.py`가 남아 있습니다.

**실제 구조**

- 실제 화면: `documents.py`, `workspace.py`
- 주요 흐름: 내부 corpus run 선택 → 문서 검색/선택 → `analyze_selection()` → workspace
- `app/views/rag_contract_demo.py`는 현재 views 디렉터리에 없음

**영향**

새 팀원이 README를 보고 업로드 기반 화면을 찾거나, 없는 파일을 기준으로 작업할 수 있습니다.

**권장 수정**

README를 현재 구조로 갱신합니다.

필수 반영:

- `documents.py` 중심 흐름
- `frontend_adapter.py` 역할
- `RAG_CORPUS_RUN_ID`
- `RAG_MODE`
- Mock fallback 정책
- 선택 문서 분석/비교/채팅 흐름

---

## 3. 체크리스트 상태 재판정

| 항목 | 문서 상태 | 실제 판단 | 근거 |
|---|---:|---:|---|
| `_chatbot_cache` 제거 | ✅ | 부분/미완료 | dict cache 유지 |
| `load_document_context()` 메모리 제거 | ✅ | 부분 | Chroma면 skip, memory 경로 유지 |
| SQLite run 관리 | ✅ | 부분 | 신규 run은 DB, 기존 FS fallback/merge 미흡 |
| 문서 목록 DB 조회 | ✅ | 부분 | DB 우선, CSV fallback 유지 |
| Chroma 검색 | ✅ | 부분 | 전체 컬렉션 검색, 선택 문서 필터 없음 |
| 출처 블록 UI 전달 | ✅ | 부분 | citation list는 전달하지만 inline 출처 block은 strip |
| Domain filter | ✅ | 부분 | LLM classifier가 아니라 keyword gate |
| 질문 캐싱 | ✅ | 부분/위험 | TTL cache 있음, scope/citation contract 미흡 |
| 진행률 UI | ✅ | 미완료 | backend 함수만 있고 workspace 연결 없음 |
| RAG_MODE 명시 전환 | ☐ | 부분 | mock 강제만 있음 |
| error handling 통합 | ☐ | 부분 | `_service_error` 일부 사용, decorator 없음 |

---

## 4. 권장 작업 순서

### 1차: 데모 correctness

1. Chroma selected_doc_ids filter 구현
2. cache payload에 citations/structured_output 포함
3. 질문 단위 state 분리
4. 관련 테스트 추가

### 2차: 운영 안정성

1. `base_config` fail-fast
2. Chroma persist consistency check
3. `RAG_MODE=rag` 강제 정책
4. async ingest failed progress 반영
5. list_runs DB+filesystem merge

### 3차: UX/문서 정리

1. workspace progress UI 연결
2. documents 화면 corpus refresh 버튼
3. `app/README.md` 갱신
4. `checklist_and_improvement_plan.md` 상태 재표기

---

## 5. 최소 테스트 목록

아래 테스트는 우선 추가하는 것을 권장합니다.

```text
tests/test_streamlit_rag_service.py
- test_chroma_selected_doc_filter_is_applied
- test_chat_cache_keeps_original_citations
- test_same_question_different_doc_scope_uses_different_cache
- test_list_runs_merges_db_and_filesystem_runs
- test_get_ingest_progress_returns_failed_status

tests/test_config.py
- test_load_config_raises_when_base_config_missing

tests/test_rag_agent.py
- test_agent_validation_reports_unknown_phase_dependency

tests/test_rag_pipeline.py
- test_chroma_resume_rebuilds_vector_store_when_persist_dir_missing
```

---

## 6. 검증 기록

실행 가능했던 검증:

```bash
python -m compileall -q app src scripts tests
```

결과:

```text
통과
```

실행하지 못한 검증:

```bash
python -m pytest
```

사유:

```text
현재 접근 가능한 Windows/WSL/번들 Python 환경에 pytest가 설치되어 있지 않음
```
