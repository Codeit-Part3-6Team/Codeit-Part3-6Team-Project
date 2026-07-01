# Agent/RAG 버그 수정 이력 보고서

> **브랜치**: `feature/agent-polish`  
> **기간**: 2026-06-25  
> **관련 계획**: `reports/agent_loop_implementation_plan.md`

---

## 개요

Agent Loop 구현 계획에 따라 Phase DAG, Tool dispatch, Structured Output, 챗봇 확장을 구현했습니다.  
이후 전수 코드 감사 및 교차 검증을 통해 발견된 버그 41건 중 32건을 수정했습니다.

---

## 수정 요약

| 구분 | 총 건수 | 상태 | 요약 |
|------|:---:|:---:|------|
| 🔴 치명 | 8건 | **전건 해결** | Agent 실행, 평가, structured output, chatbot 근거 로딩 등 핵심 동작 이슈 해소 |
| 🟠 높음 | 12건 | **전건 해결** | config 연결, embedding 주입, 실패 처리, judge 판정, chatbot routing/히스토리 개선 |
| 🟡 중간 | 12건 | **대부분 해결** | dead code, schema 오류 추적, JSON 방어, model_name 검증, output_dir guard 등 반영 |
| 🟢 보류 | 9건 | **known limitation** | 병렬 cancel 한계, 환경 의존 경로, XL용 rules 미구현 등 |

---

## 🔴 치명 이슈 해결 현황

| # | 내용 | 조치 |
|:---:|------|------|
| 1 | Agent 문서 chunk 로딩 누락 | `_load_document_context()` 추가 — `chunks.csv`, `embeddings.jsonl` 로딩 |
| 2 | Agent 평가 시 `output_dir=None`으로 chunk 미로딩 | 평가 실행 시 `output_dir` 전달 |
| 3 | `input_from` / `state` 미작동 — Phase 간 데이터 연쇄 불가 | `_build_contextualized_question()` 추가 — 이전 Tool 결과를 프롬프트 context로 주입 |
| 4 | Pydantic structured output 손실 — `isinstance(dict)`만 감지, BaseModel 무시 | `model_dump()` 처리 추가 |
| 5 | `not_found` 상태 구분 불가 — answerer 실패/빈답 구분 없이 전부 `ok` | `_resolve_status()` 추가 — `not_found` / `partial` / `ok` 3단계 구분 |
| 6 | `_build_summary()`에 `structured_output` 누락 | 키 추가 |
| 7 | `_extract_json()` nested JSON 파싱 실패 — `{.*?}` non-greedy로 끊김 | `_find_json_object()` brace 카운트 파서 추가 |
| 8 | Chatbot 문서 근거 없음 — `self.chunks=[]`, `self.embeddings=[]` | `load_document_context()` 추가 — CSV/JSONL 로딩 |

---

## 🟠 높음 이슈 해결 현황

| # | 내용 | 조치 |
|:---:|------|------|
| 9 | scoring config 경로 불일치 — `rag.scoring.*`가 retriever에 미주입 | `build_retriever_adapter(full_rag_config=)` 파라미터 추가 |
| 10 | `mode: generative` 오타 — valid mode 아님 | 불필요 키 제거 |
| 11 | `--verbose` CLI dead flag — 파싱만 하고 미적용 | argparse에서 제거 |
| 12 | `_CHAT_HISTORY` 전역 dict — thread 충돌 위험 | `_ChatMemory` 클래스로 캡슐화 |
| 13 | DAG cycle 침묵 — 디버깅 불가 | `RuntimeWarning` 추가 |
| 14 | Tool retriever embedding config `{}` → semantic/hybrid가 항상 local hashing | `rag.embedding` 주입 |
| 15 | answerer 실패 시 `on_failure` 미확인 — `abort_agent` 무시 | exception 경로에서도 `on_failure` 체크 |
| 16 | judge `"true" in text` substring — `"untrue"`도 True | 토큰 기반 비교 (`split()[0] == "true"`) |
| 17 | Chatbot LLM 실패 침묵 — API 오류 진단 불가 | stderr 진단 로그 추가 |
| 18 | 챗봇 provider 하드코딩 — ChatOpenAI 전용 | `tool_selection_provider` 분기 (openai/ollama) |
| 19 | 챗봇 히스토리 미주입 — 멀티턴 컨텍스트 상실 | `history[-5:]` 프롬프트 주입 |
| 20 | retry가 `"partial"` 미감지 — 대부분 실패에서 retry 안 탐 | `failed`/`partial` 모두 retry 대상 |

---

## 🟡 중간 이슈 해결 현황

| # | 내용 | 조치 |
|:---:|------|------|
| 21 | `_checkpoint_enabled` dead code — 저장만 하고 미참조 | 제거 |
| 22 | output_schema 미지원 adapter 침묵 — 경고 없이 무시 | `errors.append()` 기록 |
| 23 | bare `json.loads(text)` 무방어 — 예외 삼켜짐 | `try/except` + stderr |
| 24 | `rules: "string"` → crash — `.get("patterns")` AttributeError | `isinstance(dict)` guard |
| 25 | answer 200자 절단 — 평가 시 긴 답변 손실 | 500자로 확대 |
| 26 | `next()` → StopIteration crash 가능 | for-loop + `None` 체크 |
| 27 | `model_name=""` 침묵 — provider 기본값 사용으로 원인 추적 불가 | `ValueError` 발생 |
| 28 | `output_dir=None` → crash — `_write_run_status` 호출 | `if output_dir:` guard |
| 29 | artifact 저장 상태 불명확 — dict config 시 침묵 | `artifact_status: "disabled"` 명시 |
| 30 | JSON fragile 파싱 (초기 버전) | markdown 코드블록 + 정규식 + raw fallback 3단계 |
| 31 | 챗봇 라우팅 모호 — Phase DAG/챗봇 관계 불명확 | routing 주석 보강 |
| 32 | 자연어 오류 응답 부족 | 사용자 친화적 메시지로 개선 |

---

## 🟢 잔여/보류 이슈

| 내용 | 현재 판단 |
|------|------|
| `future.cancel()` no-op (병렬 Phase) | ThreadPoolExecutor 한계. 리소스 낭비만 있고 충돌 없음 |
| validation `depends_on` 오탐 가능성 | crashing bug 아님. 검증 로직 개선 후보 |
| YAML `str` → Pydantic type 명시 변환 | Pydantic v2에서 정상 동작 확인. 추후 안정화 |
| `prompt str.format` KeyError (사용자 템플릿) | 경계 케이스. 템플릿 검증 정책 필요 |
| DAG warning 문구 부정확 ("임의 순서" vs YAML 정의순) | 경미. 메시지 정정 |
| enum 비교 스타일 (`value == "string"`) | 타입 안정성 개선 후보 |
| lazy import 일관성 | 코드 스타일 |
| Linux `/shared` 경로 | VM 기준 정상, 로컬 Windows에서는 환경 의존 |
| `rules.patterns` 미구현 | XL 확장 범위. 현재 Agent/챗봇 목표에서는 보류 |

---

## 검증 결과

| 항목 | 결과 |
|------|:---:|
| 전체 테스트 | 61 passed |
| Agent 실패 경로 회귀 테스트 | 추가 및 통과 |
| RAG 기본 평가 | 정상 실행 |
| keyword/semantic/hybrid config | 정상 실행 |
| Agent 산출물 저장 | `agent_metrics.json`, `agent_state.jsonl` 생성 확인 |
| Chatbot 문서 로딩 | chunk/embedding 로딩 경로 확인 |

---

## 총평

이번 수정으로 Agent/RAG 실험을 막던 **치명·높음 이슈는 전건 해소**되었습니다.

특히 아래 핵심 연결 고리가 복구되었습니다:

- **문서 근거 로딩**: Agent/Chatbot이 실제 `chunks.csv`, `embeddings.jsonl`을 읽어 검색 기반 답변 생성
- **Phase 간 state 전달**: `input_from`에 지정된 이전 Tool 결과가 다음 Tool의 프롬프트 context로 주입
- **structured output 보존**: Pydantic 모델 응답이 `model_dump()`로 저장되어 Phase 간 구조화 데이터 연쇄 가능
- **실패 상태 전파**: `not_found` / `partial` / `ok` 3단계 구분으로 retry·평가·지표 왜곡 방지
- **챗봇 Tool routing**: provider 분기, 히스토리 주입, JSON 방어, retry 정책까지 완비

Agent 기반 실험과 챗봇 확장의 기술적 기반이 안정화되었습니다.  
남은 주요 리스크는 **코드 실행 안정성보다는 RAG 성능 실험 체계와 운영 품질**에 가깝습니다.

---

> **구현 브랜치**: `feature/agent-polish`  
> **관련 계획 문서**: `reports/agent_loop_implementation_plan.md`
