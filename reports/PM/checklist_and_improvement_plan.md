# PM 종합 체크리스트 & 개선 계획

> **작성일**: 2026-07-05    
> **대상**: 팀 전체 공유   
> **참고**: DB 선정 상세 → [`vector_db_comparison.md`](vector_db_comparison.md)    

---

## 1. 종합 이슈 체크리스트

### 1.1 인메모리 처리 → DB 전환 (P0 - 최우선)

| # | 이슈 | 현재 위치 | 변경 파일 | 구현 방법 | 담당 | 상태 |
|---|------|----------|----------|----------|------|------|
| 1 | `_chatbot_cache` dict 휘발성 | `rag_service.py:42` | `app/services/rag_service.py` | `_chatbot_cache: dict` → `_get_chatbot(run_id)` 내부에서 `ChatbotRunner` 대신 `ChromaChatbotRunner` 생성. SQLite로 run_id별 연결 상태 관리 | PM | ☐ |
| 2 | `load_document_context()` 전체 메모리 적재 | `chatbot.py:47-66` | `src/rag/chatbot.py` | `load_document_context()` → `connect_collection(run_id)`. self.chunks, self.embeddings 제거. 내부적으로 ChromaDB 컬렉션 쿼리로 대체 | PM | ☐ |
| 3 | `_ChatMemory` dict 휘발성 | `pipeline.py:343-357` | `src/rag/pipeline.py` | class 변수 dict → `sqlite3` 기반 `chat_history` 테이블. `thread_id`로 조회/저장 | PM | ☐ |
| 4 | `embeddings.jsonl` 파일 기반 | `pipeline.py:85-86`, `chatbot.py:62-66` | `src/rag/adapters.py`, `src/rag/chatbot.py` | `ChromaRetrieverAdapter` 신규 구현. `RagRetrieverAdapter.retrieve()` 시그니처 유지하되 chunks/embeddings 파라미터는 무시하고 ChromaDB 컬렉션에서 직접 쿼리 | PM | ☐ |
| 5 | run 관리 파일시스템 순회 | `rag_service.py:614-653` | `app/services/rag_service.py` | `list_runs()` → SQLite `runs` 테이블 조회. `create_and_ingest()` 시 run 메타데이터 INSERT | PM | ☐ |
| 6 | 문서 목록 매번 CSV 파싱 | `rag_service.py:559-593` | `app/services/rag_service.py` | `get_documents()` → SQLite `documents` 테이블 또는 ChromaDB 컬렉션 메타데이터 조회 | PM | ☐ |

**핵심 변경 포인트**:
```
[변경 전]                                [변경 후]
embeddings.jsonl 파일                    ChromaDB Collection (영속)
    ↓                                        ↓
ChatbotRunner.load_document_context()     ChatbotRunner.connect_collection(run_id)
    ↓                                        ↓
self.embeddings (list, in-memory)         collection.query(query_embedding, top_k)
    ↓                                        ↓
Tool.run(question, chunks, embeddings)    Tool.run(question, collection, top_k)
```

---

### 1.2 챗봇 응답 품질 개선 (P0)

| # | 이슈 | 현재 위치 | 변경 파일 | 구현 방법 | 담당 | 상태 |
|---|------|----------|----------|----------|------|------|
| 7 | `_format_tool_result()` key-value 나열 | `chatbot.py:135-155` | `src/rag/chatbot.py` | structured_output이 있으면 "요약 카드"용 마크다운 테이블로 따로 렌더링. reply(answer)는 자연어 문장 그대로 노출. `_format_tool_result()`가 structured_output을 평문에 섞지 않도록 분리 | PM | ☐ |
| 8 | `_display_reply()` 가 structured_output 우선 | `rag_service.py:289-293` | `app/services/rag_service.py` | `_display_reply()` → `structured_output`을 reply 뒤 "📋 분석 결과" 블록으로 별도 출력. reply가 비어있을 때만 structured_output을 fallback | PM | ☐ |
| 9 | 시스템 프롬프트 기계적 지시 | `chatbot.py:33-37` | `src/rag/chatbot.py` → `system_prompt` 필드 | `"JSON으로 응답하라"` → `"너는 RFP 입찰 전문 컨설턴트 'IT'S MINE'이다. 사용자 질문을 이해하고 자연스러운 대화로 답변하라. 분석이 필요하면 내부 도구를 호출하라."`. config의 `agent.chatbot.system_prompt`로 오버라이드 가능하게 | PM | ☐ |
| 10 | `_strip_source_block()` 무조건 제거 | `rag_service.py:282-286` | `app/services/rag_service.py` | 출처 블록을 제거하지 않고 `citations` 리스트를 UI에 전달. UI에서 접이식(foldable) 출처 영역으로 렌더링 | PM | ☐ |
| 11 | extract_facts 프롬프트 보수적 | `agent_lplus.yaml:140-149` | `configs/experiments/rag/agent/agent_lplus.yaml` | `"문서에 명시된 내용만 답하고"` → `"근거에 있는 정보를 기반으로 자연스럽게 요약하라. 명시되지 않은 항목은 '명시되지 않음'으로 표시하라."`. temperature 0.1 → 0.3 | PM | ☐ |
| 12 | extract_requirements 프롬프트 동일 | `agent_lplus.yaml:88-97` | `configs/experiments/rag/agent/agent_lplus.yaml` | 11번과 동일한 방향으로 수정. `참가자격`, `제출서류`, `평가기준` 필드별 요구사항 설명 강화 | PM | ☐ |

---

### 1.3 관련 없는 질문 처리 (P1)

| # | 이슈 | 현재 위치 | 변경 파일 | 구현 방법 | 담당 | 상태 |
|---|------|----------|----------|----------|------|------|
| 13 | Domain classification 부재 | `chatbot.py:230-273` | `src/rag/chatbot.py` | `_fallback_tool_selection()` 호출 전 `_is_rfp_question(question)` 게이트 추가. LLM에게 "이 질문이 RFP/입찰 문서 분석과 관련 있는가?" 1차 판단 후 관련 없으면 거절 응답 | PM | ☐ |
| 14 | Out-of-scope 응답 정의 | 없음 | `src/rag/chatbot.py` | `self.out_of_scope_reply = "저는 RFP 문서 전문 분석 도우미입니다. 문서 요약, 요구사항 추출, 비교 분석, 참여 판단에 대해 질문해 주세요."` | PM | ☐ |
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
| 16 | 응답 속도 목표(SLA) | 없음 | `configs/experiments/rag/streamlit.yaml` | `agent.performance.target_first_response_ms: 3000`, `target_full_analysis_ms: 10000` config 항목 추가. 초과 시 로그 경고 | PM | ☐ |
| 17 | 반복 질문 캐싱 | 없음 | `src/rag/chatbot.py` | `_cache: dict[str, ToolResult]`. key = `hash(question + sorted(doc_ids))`. TTL 300초. 동일 질문+문서 조합이면 Tool 실행 건너뛰고 캐시 응답 | PM | ☐ |
| 18 | 검색 최적화 (BM25+RRF) | `rag_hybrid.yaml` config만 존재 | `configs/experiments/rag/streamlit.yaml` | `rag.retriever.method: hybrid` 설정 확인. BM25 scorer(`src/rag/scoring.py`)가 실제로 `rank-bm25`를 사용하는지 검증. 아니면 `rank_bm25` import 추가 | PM | ☐ |
| 19 | LLM 호출 최적화 | `tool.py:59-80` | `src/rag/tool.py` | `input_from`이 있는 Tool은 이전 Tool의 `structured_output`을 context로 바로 주입하여 chunk 재검색 생략. `decide_participation`이 `extract_facts` 결과를 바로 받아쓰도록 이미 구현됨 — 다른 Tool에도 확장 | PM | ☐ |

---

### 1.5 임베딩 데이터 용량 관리 (P1)

| # | 이슈 | 현재 위치 | 변경 파일 | 구현 방법 | 담당 | 상태 |
|---|------|----------|----------|----------|------|------|
| 20 | Embedding 용량 제한 없음 | `chatbot.py:44-45` | `src/rag/chatbot.py` | ChromaDB 사용 시 자동 해결 (DB가 인덱스 관리). 단, 컬렉션별 최대 chunk 수 제한 config 추가: `agent.limits.max_chunks_per_run: 10000` | PM | ☐ |
| 21 | Dimensionality 고정 64dim | `vector_store.py:15`, `embedder.py` | `src/rag/embedder.py` | `rag.embedding.dimension` config를 읽어 동적으로 차원 결정. Ollama `nomic-embed-text` 사용 시 768dim 자동 적용 | PM | ☐ |
| 22 | 용량 산정 | 없음 | (산정만, 코드 변경 없음) | chunk당 `768dim * 4byte(float32) = 3KB`. 5,000 chunks = ~15MB. 100,000 chunks = ~300MB. → ChromaDB 사용 시 디스크에 저장되므로 메모리 부담 없음 | PM | ☐ |

---

### 1.6 요약 태스크 출력 정제 (P1)

| # | 이슈 | 현재 위치 | 변경 파일 | 구현 방법 | 담당 | 상태 |
|---|------|----------|----------|----------|------|------|
| 23 | extract_facts 결과 정제 | `src/rag/schema_parser.py` | `src/rag/schema_parser.py` | `_format_structured_output()`에서 빈 값이 전체 필드의 몇 %인지 `coverage_rate` 계산. `"명시되지 않음"` 비율이 50% 초과 시 경고 플래그 | PM | ☐ |
| 24 | 누락 필드 원인 설명 | `rag_service.py:261-279` | `app/services/rag_service.py` | `_format_structured_output()` → 누락 필드 하단에 `"※ '사업예산', '사업기간' 항목은 문서 내에 명시되지 않았습니다."` 추가 | PM | ☐ |
| 25 | 요약 품질 평가 자동화 | `src/rag/judge.py` | `src/rag/judge.py` | `judge_binary()` → `judge_graded()`: `["정확", "부분정확", "부정확", "환각", "무응답"]` 5단계 평가. `agent.evaluation.llm_judge.grading: "graded"` config로 전환 | PM | ☐ |

---

### 1.7 서비스 완성도 (P2)

| # | 이슈 | 현재 위치 | 변경 파일 | 구현 방법 | 담당 | 상태 |
|---|------|----------|----------|----------|------|------|
| 26 | 에러 핸들링 통합 | 각 함수별 try/except | `app/services/rag_service.py` | `@handle_rag_error` 데코레이터 생성 → 공통 에러 응답 포맷 `{"reply": "", "error": "...", "error_code": "..."}`. 사용자 메시지는 한글로, 내부 로그는 영어로 | PM | ☐ |
| 27 | 로깅 체계 | `chatbot.py:213` (print) | `src/rag/chatbot.py`, `src/rag/tool.py` | `logging.getLogger("rag")` 사용. `configs/experiments/rag/streamlit.yaml`에 `logging.level: INFO`, `logging.file: experiments/streamlit/rag.log` 추가 | PM | ☐ |
| 28 | Mock ↔ RAG 전환 명시화 | `frontend_adapter.py:42-69` | `app/services/frontend_adapter.py` | 환경변수 `RAG_MODE` → `"rag"` / `"mock"`. `_load_rag()`가 이 값을 우선 확인. 자동 감지는 유지하되 경고 배너 표시 | PM | ☐ |
| 29 | Thread-safe 세션 | `rag_service.py:42` | `app/services/rag_service.py` | `threading.Lock` 추가 또는 SQLite WAL 모드 사용. `_chatbot_cache` → SQLite `chatbot_sessions` 테이블로 대체되면 자연스럽게 해결 | PM | ☐ |
| 30 | 업로드 → 비동기 ingest | `rag_service.py:100-173` | `app/services/rag_service.py` | `create_and_ingest()` 내부에서 `threading.Thread`로 ingest 실행. 콜백으로 진행률 업데이트. `run_status.json` 폴링하여 완료 감지 | PM | ☐ |
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
| 1 | `_display_reply()` + `_format_tool_result()` 분리 | `rag_service.py`, `chatbot.py` | 2h | ☐ |
| 2 | 시스템 프롬프트 페르소나 변경 | `chatbot.py`, `agent_lplus.yaml` | 1h | ☐ |
| 3 | SQLite: run 관리 + 대화 기록 | `rag_service.py`, `pipeline.py` | 3h | ☐ |
| 4 | Domain classifier (off-topic 필터) | `chatbot.py` | 2h | ☐ |
| 5 | ChromaDB 연동: embeddings 검색 | `adapters.py`, `chatbot.py` | 4h | ☐ |
| 6 | extract_facts 프롬프트 튜닝 | `agent_lplus.yaml` | 1h | ☐ |
| 7 | 응답 속도 측정 + 질문 캐싱 | `chatbot.py`, `streamlit.yaml` | 2h | ☐ |
| 8 | 분석 진행률 UI | `workspace.py`, `rag_service.py` | 2h | ☐ |

### 발표 데모 시나리오

```
1. 문서 5건 선택 → "예산이 어떻게 돼?" → 자연어 답변 + 접이식 출처 카드
2. "오늘 날씨 어때?" → "RFP 전문 분석 도우미입니다" (off-topic 필터)
3. "A랑 B 비교해줘" → 표 형식 비교 + 근거 citation
4. "참가 자격 알려줘" → 요구사항 리스트 + 누락 항목 설명
```

---