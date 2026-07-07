# PM 종합 체크리스트 & 개선 계획

> **작성일**: 2026-07-05    
> **대상**: 팀 전체 공유   
> **참고**: DB 선정 상세 → [`vector_db_comparison.md`](vector_db_comparison.md)    

---

## 1. 종합 이슈 체크리스트

### 1.1 인메모리 처리 → DB 전환 (P0 - 최우선)

| # | 이슈 | 현재 위치 | 변경 파일 | 구현 방법 | 담당 | 상태 |
|---|------|----------|----------|----------|------|------|
| 1 | `_chatbot_cache` dict 휘발성 | `rag_service.py:42` | `app/services/rag_service.py` | `_chatbot_cache`는 유지하되 `_chatbot_lock`으로 보호. run/document/chat history는 SQLite로 영속화 | PM | 부분 |
| 2 | `load_document_context()` 전체 메모리 적재 | `chatbot.py:47-66` | `src/rag/chatbot.py` | Chroma 경로에서는 chunks/embeddings 로딩을 건너뛰고 persist collection에 연결. memory fallback 경로는 CSV/JSONL 로딩 유지 | PM | 부분 |
| 3 | `_ChatMemory` dict 휘발성 | `pipeline.py:343-357` | `src/rag/pipeline.py`, `app/services/sqlite_store.py` | `_ChatMemory` dict는 캐시로 남아 있으나 SQLite `chat_history` 조회/삭제와 연동 | PM | 부분 |
| 4 | `embeddings.jsonl` 파일 기반 | `pipeline.py:85-86`, `chatbot.py:62-66` | `src/rag/adapters.py`, `src/rag/chatbot.py`, `src/rag/engines/langchain.py` | Chroma vector store와 `ChromaRetrieverAdapter` 구현. `embeddings.jsonl`은 artifact/resume 용도로 유지 | PM | 부분 |
| 5 | run 관리 파일시스템 순회 | `rag_service.py:614-653` | `app/services/rag_service.py`, `app/services/sqlite_store.py` | SQLite run 목록과 filesystem run을 병합. 신규 run은 SQLite에 저장하고 기존 artifact run도 fallback 조회 | PM | 부분 |
| 6 | 문서 목록 매번 CSV 파싱 | `rag_service.py:559-593` | `app/services/rag_service.py`, `app/services/sqlite_store.py` | SQLite documents 테이블 우선 조회, 없으면 CSV artifact fallback. filesystem run도 `get_documents()`로 문서 수 계산 | PM | 부분 |

**핵심 변경 포인트**:
```
[변경 전]                                [변경 후]
embeddings.jsonl 중심 검색               ChromaDB Collection + artifact 병행
    ↓                                        ↓
ChatbotRunner.load_document_context()     Chroma 모드면 persist_dir 연결 후 메모리 로딩 skip
    ↓                                        ↓
self.embeddings (list, in-memory)         ChromaRetrieverAdapter.retrieve()
    ↓                                        ↓
Tool.run(question, chunks, embeddings)    Tool.run() 계약 유지 + retriever가 Chroma 직접 조회
```

---

### 1.2 챗봇 응답 품질 개선 (P0)

| # | 이슈 | 현재 위치 | 변경 파일 | 구현 방법 | 담당 | 상태 |
|---|------|----------|----------|----------|------|------|
| 7 | `_format_tool_result()` key-value 나열 | `chatbot.py:135-155` | `src/rag/chatbot.py`, `app/services/rag_service.py` | chatbot payload에 `structured_output`을 분리해 담고, `rag_service._display_reply()`에서 reply 뒤 분석 결과 블록으로 표시. CLI 포맷터의 key-value 출력은 일부 유지 | PM | 부분 |
| 8 | `_display_reply()` 가 structured_output 우선 | `rag_service.py:289-293` | `app/services/rag_service.py` | `_display_reply()` → `structured_output`을 reply 뒤 "📋 분석 결과" 블록으로 별도 출력. reply가 비어있을 때만 structured_output을 fallback | PM | ✅ |
| 9 | 시스템 프롬프트 기계적 지시 | `chatbot.py:33-37` | `src/rag/chatbot.py` → `system_prompt` 필드 | `"JSON으로 응답하라"` → `"너는 RFP 입찰 전문 컨설턴트 'IT'S MINE'이다. 사용자 질문을 이해하고 자연스러운 대화로 답변하라. 분석이 필요하면 내부 도구를 호출하라."`. config의 `agent.chatbot.system_prompt`로 오버라이드 가능하게 | PM | ✅ |
| 10 | `_strip_source_block()` 무조건 제거 | `rag_service.py:282-286` | `app/services/rag_service.py`, `app/services/frontend_adapter.py` | inline `[출처]` 블록은 표시용 reply에서 제거하고, `citations` 리스트를 별도 UI sources로 전달 | PM | 부분 |
| 11 | extract_facts 프롬프트 보수적 | `agent_lplus.yaml:140-149` | `configs/experiments/rag/agent/agent_lplus.yaml` | `"문서에 명시된 내용만 답하고"` → `"근거에 있는 정보를 기반으로 자연스럽게 요약하라. 명시되지 않은 항목은 '명시되지 않음'으로 표시하라."`. temperature 0.1 → 0.3 | PM | ✅ |
| 12 | extract_requirements 프롬프트 동일 | `agent_lplus.yaml:88-97` | `configs/experiments/rag/agent/agent_lplus.yaml` | 11번과 동일한 방향으로 수정. `참가자격`, `제출서류`, `평가기준` 필드별 요구사항 설명 강화 | PM | ✅ |

---

### 1.3 관련 없는 질문 처리 (P1)

| # | 이슈 | 현재 위치 | 변경 파일 | 구현 방법 | 담당 | 상태 |
|---|------|----------|----------|----------|------|------|
| 13 | Domain classification 부재 | `chatbot.py:230-273` | `src/rag/chatbot.py` | `_select_tool()` 호출 전 `_is_rfp_question(question)` keyword gate 추가. LLM intent classifier는 후속 항목으로 분리 | PM | ✅ |
| 14 | Out-of-scope 응답 정의 | 없음 | `src/rag/chatbot.py` | RFP/입찰 문서 분석 범위를 벗어난 질문에는 문서 요약, 요구사항 추출, 비교 분석, 참여 판단을 안내하는 거절 응답 반환 | PM | ✅ |
| 15 | Intent classifier 도입 | Tool 선택만 있음 | `src/rag/chatbot.py` | `_select_tool()` 전 단계로 `_classify_intent()` 추가. 반환값: `("rfp_question", tool_name)` / `("general", None)` / `("feature_question", None)`. 일반 질문은 out_of_scope_reply, 기능 문의는 help 메시지 | PM | ☐ |

**구현 구조**:
```
chat(user_input)
    ↓
_classify_intent(user_input)   ← 신규
    ├── "rfp_question" → _select_tool() → _run_agent_loop()
    ├── "general"      → out_of_scope_reply 반환
    └── "feature_help" → 사용가능 기능 목록 반환
```

---

### 1.4 응답 속도 (P1)

| # | 이슈 | 현재 위치 | 변경 파일 | 구현 방법 | 담당 | 상태 |
|---|------|----------|----------|----------|------|------|
| 16 | 응답 속도 목표(SLA) | 없음 | `configs/experiments/rag/streamlit.yaml` | `agent.performance.target_first_response_ms: 3000`, `target_full_analysis_ms: 10000` config 항목 추가. 초과 시 로그 경고는 VM 실측 후 보강 | PM | 부분 |
| 17 | 반복 질문 캐싱 | 없음 | `src/rag/chatbot.py` | `_cache: dict` 추가. key = `(question, tuple(sorted(doc_ids)))`. TTL 300초. 동일 질문+문서 조합이면 Tool 실행 건너뛰고 캐시 응답 | PM | ✅ |
| 18 | 검색 최적화 (BM25+RRF) | `rag_hybrid.yaml` config만 존재 | `configs/experiments/rag/`, `src/rag/engines/langchain.py` | local hybrid retriever와 `rag_hybrid.yaml` 비교 config 구현. LangChain 경로는 `hybrid_bm25` 옵션에서 `rank_bm25` 기반 BM25+RRF 지원. Streamlit 기본은 Chroma 유지 | PM | 부분 |
| 19 | LLM 호출 최적화 | `tool.py:59-80` | `src/rag/tool.py` | `input_from`이 있는 Tool은 이전 Tool의 `structured_output` 또는 answer를 context로 주입. `decide_participation` 등 의존 Tool 흐름에 적용 | PM | ✅ |

---

### 1.5 임베딩 데이터 용량 관리 (P1)

| # | 이슈 | 현재 위치 | 변경 파일 | 구현 방법 | 담당 | 상태 |
|---|------|----------|----------|----------|------|------|
| 20 | Embedding 용량 제한 없음 | `chatbot.py:44-45` | `src/rag/chatbot.py`, `src/rag/adapters.py` | Streamlit/Chroma 경로는 embeddings 전체 메모리 적재 대신 Chroma persist를 사용. 컬렉션별 최대 chunk 제한 config는 후속 운영 보강 | PM | 부분 |
| 21 | Dimensionality 고정 64dim | `vector_store.py:15`, `embedder.py` | `src/rag/embedder.py`, `src/rag/adapters.py`, `src/rag/engines/langchain.py` | `rag.embedding.dimension` config를 읽어 local embedding 차원을 결정. Ollama/OpenAI/HuggingFace provider는 provider 모델 차원을 사용 | PM | ✅ |
| 22 | 용량 산정 | 없음 | (산정/문서화) | ChromaDB 사용 시 vector index가 디스크에 저장되어 메모리 부담을 낮춤. 100건/수천 chunk 규모는 Chroma로 처리 가능한 것으로 판단 | PM | ✅ |

---

### 1.6 요약 태스크 출력 정제 (P1)

| # | 이슈 | 현재 위치 | 변경 파일 | 구현 방법 | 담당 | 상태 |
|---|------|----------|----------|----------|------|------|
| 23 | extract_facts 결과 정제 | `src/rag/schema_parser.py` | `src/rag/schema_parser.py` | `_format_structured_output()`에서 빈 값이 전체 필드의 몇 %인지 `coverage_rate` 계산. `"명시되지 않음"` 비율이 50% 초과 시 경고 플래그 | PM | ☐ |
| 24 | 누락 필드 원인 설명 | `rag_service.py:261-279` | `app/services/rag_service.py` | `_format_structured_output()` → 누락 필드 하단에 `"※ '사업예산', '사업기간' 항목은 문서에 명시되지 않았습니다."` 추가 | PM | ✅ |
| 25 | 요약 품질 평가 자동화 | `src/rag/judge.py` | `src/rag/judge.py` | `judge_binary()` → `judge_graded()`: `["정확", "부분정확", "부정확", "환각", "무응답"]` 5단계 평가. `agent.evaluation.llm_judge.grading: "graded"` config로 전환 | PM | ☐ |

---

### 1.7 서비스 완성도 (P2)

| # | 이슈 | 현재 위치 | 변경 파일 | 구현 방법 | 담당 | 상태 |
|---|------|----------|----------|----------|------|------|
| 26 | 에러 핸들링 통합 | 각 함수별 try/except | `app/services/rag_service.py` | `_service_error()` 공통 응답 포맷 도입. `ask()`/`ask_with_document_filter()` 등 주요 서비스 경로에서 한글 사용자 메시지와 내부 로그를 분리 | PM | 부분 |
| 27 | 로깅 체계 | `chatbot.py:213` (print) | `app/services/rag_service.py`, `src/rag/chatbot.py`, `src/rag/agent.py` | `logging.getLogger(...)` 기반 로그 사용. config 기반 log file 설정은 후속 보강 | PM | 부분 |
| 28 | Mock ↔ RAG 전환 명시화 | `frontend_adapter.py:42-69` | `app/services/frontend_adapter.py` | 환경변수 `RAG_MODE` → `"rag"` / `"mock"`. `RAG_MODE=rag`에서 백엔드 연결 실패 시 mock 문서/채팅 fallback을 막고 에러 표시 | PM | ✅ |
| 29 | Thread-safe 세션 | `rag_service.py:42` | `app/services/rag_service.py`, `app/services/sqlite_store.py` | `_chatbot_lock`으로 chatbot cache 접근 보호, SQLite 저장소는 WAL + lock 사용 | PM | ✅ |
| 30 | 업로드 → 비동기 ingest | `rag_service.py:100-173` | `app/services/rag_service.py`, `app/examples/build_internal_corpus.py` | `create_and_ingest()` 내부에서 `threading.Thread`로 ingest 실행. 내부 corpus 스크립트는 `async_mode=False`로 완료 후 반환 | PM | ✅ |
| 31 | 분석 진행률 표시 | 없음 | `app/views/workspace.py` | `run_status.json`의 `stage` 필드(`"documents"→"chunks"→"embeddings"`) 기반 Streamlit `st.progress()` 표시 | PM | ☐ |

---

## 2. DB 선정: ChromaDB

> 상세 비교는 [`vector_db_comparison.md`](vector_db_comparison.md) 참고

**결정**: **ChromaDB** (1차), 규모 확장 시 **PostgreSQL+pgvector** (2차)

**선정 근거**:
1. `requirements.txt`에 `langchain-chroma==1.0.0` 이미 포함 — 추가 설치 제로
2. `pip install` 수준 배포, SQLite 기반 자동 영속성
3. 현재 100건/5K chunks 규모에서 충분한 성능
4. 규모가 커지면 PostgreSQL+pgvector로 마이그레이션 (API 유사)

---

## 3. 재설계 vs 점진적 개선 → **점진적 개선**

- 아키텍처 core (pipeline, chatbot, agent) 유지
- storage layer만 교체 (CSV/JSONL → ChromaDB + SQLite)
- presentation layer (응답 포맷) 개선
- prompt engineering 고도화

---

## 4. 7/8(월)까지 달성 목표 (1차 데모)

| 순번 | 작업 | 변경 파일 | 예상 소요 | 완료 |
|------|------|----------|----------|------|
| 1 | `_display_reply()` + `_format_tool_result()` 분리 | `rag_service.py`, `chatbot.py` | 2h | ✅ |
| 2 | 시스템 프롬프트 페르소나 변경 | `chatbot.py`, `agent_lplus.yaml` | 1h | ✅ |
| 3 | SQLite: run 관리 + 대화 기록 | `rag_service.py`, `pipeline.py` | 3h | ✅ |
| 4 | Domain classifier (off-topic 필터) | `chatbot.py` | 2h | ✅ |
| 5 | ChromaDB 연동: embeddings 검색 | `adapters.py`, `chatbot.py` | 4h | ✅ |
| 6 | extract_facts 프롬프트 튜닝 | `agent_lplus.yaml` | 1h | ✅ |
| 7 | 응답 속도 측정 + 질문 캐싱 | `chatbot.py`, `streamlit.yaml` | 2h | ✅ |
| 8 | 분석 진행률 API | `rag_service.py` | 2h | 부분 |

### 발표 데모 시나리오

```
1. 문서 5건 선택 → "예산이 어떻게 돼?" → 자연어 답변 + 접이식 출처 카드
2. "오늘 날씨 어때?" → "RFP 전문 분석 도우미입니다" (off-topic 필터)
3. "A랑 B 비교해줘" → 표 형식 비교 + 근거 citation
4. "참가 자격 알려줘" → 요구사항 리스트 + 누락 항목 설명
```

---

## 5. 2026-07-06 구현 재검토 메모

> 코드 기준 재검토 결과입니다. 세부 동작은 VM에서 실제 ingest/Streamlit 실행으로 최종 확인합니다.

### 반영 확인

- P1-1 Chroma 선택 문서 필터: `document_ids`가 retriever config에 주입되고, `ChromaRetrieverAdapter`가 `{"document_id": {"$in": ...}}` filter로 검색합니다.
- P1-2 cache payload: 챗봇 응답 payload에 `structured_output`, `citations`가 포함되고, `rag_service.ask()` 계열은 `bot.state` 재조회 대신 response payload를 사용합니다.
- P1-3 cache scope: cache key가 `(question, tuple(sorted(doc_ids)))` 형태로 문서 범위를 포함합니다.
- P1-4 질문별 state 격리: `_run_agent_loop()` 내부 `run_state`로 dependency Tool 결과를 질문 단위로 분리합니다.
- P1-5 config fail-fast: `base_config`가 명시됐는데 파일이 없으면 `FileNotFoundError`를 발생시킵니다.
- P2 주요 항목: Chroma persist 재생성, failed progress, `list_runs()` DB+filesystem merge, DAG unknown dependency warning, `RAG_MODE=rag` mock 차단은 코드에 반영되어 있습니다.

### 내일 VM 실테스트 우선 확인

- 내부 corpus 생성 스크립트는 `async_mode=False`로 보완되었습니다. VM에서 실제 90~100건 corpus 생성이 끝까지 성공하는지 확인합니다.
- filesystem에만 남은 run도 `get_documents()` 기반 문서 수로 병합됩니다. VM에서 실제 corpus 자동 선택이 기대한 run을 고르는지 확인합니다.
- `RAG_MODE=rag`에서 import 실패 시 mock 문서/분석/채팅 fallback 차단이 화면에서 기대한 메시지로 보이는지 확인합니다.
- 앱 실행 중 새 corpus ingest 후 `internal_corpus(force_refresh=True)`를 UI에서 호출할 필요가 있는지 확인합니다.
- 선택 문서 질의의 citation `document_id`가 선택 범위 밖으로 새지 않는지 단일/다중 문서 모두 확인합니다.

### 문서 상태

- `app/README.md`는 업로드 기반 설명에서 내부 corpus 기반 `documents.py -> workspace.py` 흐름으로 갱신했습니다.
- 이 PM 체크리스트의 기존 표에는 과거 목표/상태가 함께 남아 있으므로, 최종 VM 검증 이후 표 상태를 한 번 더 정리합니다.
