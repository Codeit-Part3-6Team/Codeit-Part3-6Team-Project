## 변경 개요

RAG 파이프라인 위에 Agent Loop + 챗봇 모드를 추가했습니다. config 하나로 RAG / Agent / Chatbot 전환이 가능하며, Tool 기반 확장 구조를 통해 새 기능을 config만으로 추가할 수 있습니다.

## 변경 유형

- [x] 코드 / RAG 파이프라인
- [x] Config / 실행 스크립트
- [ ] 데이터 / EDA / 전처리
- [ ] Notebook
- [x] 문서
- [ ] GitHub 운영 / 템플릿
- [x] 버그 수정 / 리팩토링

## 주요 변경사항

### Agent / Chatbot 파이프라인

| 모듈 | 역할 |
|------|------|
| `src/rag/agent.py` | AgentRunner — Phase DAG 순차/병렬 실행, Tool dispatch |
| `src/rag/chatbot.py` | ChatbotRunner — LLM이 Tool description 읽고 동적 선택, 대화형 Q&A |
| `src/rag/tool.py` | Tool wrapper — retriever + answerer 실행, OnFailure 정책(skip/abort_phase/abort_agent), input_from 의존성 체인 |
| `src/rag/schema_parser.py` | Pydantic 동적 output_schema 생성 (structured output) |
| `src/rag/scoring.py` | tokenize/score 기반 답변 평가 |
| `src/rag/judge.py` | LLM-as-Judge 정성 평가 (ollama/openai) |
| `src/rag/prompt.py` | Phase별 프롬프트 템플릿 통합 |

### Config 확장

- `agent.enabled: true/false` — Agent/Chatbot ↔ 기존 RAG 전환
- `agent.phases` — Phase DAG 정의 (depends_on으로 순차/병렬)
- `agent.tools.<tool>` — Tool별 retriever/answerer/prompt/output_schema 개별 오버라이드
- `agent.chatbot.enabled: true` — Phase DAG 대신 LLM 동적 Tool 선택
- `agent.loop.enabled: true` — Agent Loop 반복 실행 (Plan→Execute→Evaluate)
- `base_config` 상속 지원 — `agent_lplus.yaml`이 `rag-baseline.yaml` 상속

### CLI

- `scripts/run_rag_agent.py` — Agent/Chatbot 실행 진입점 (기존 RAG CLI와 동일한 인터페이스)

### 문서

| 문서 | 내용 |
|------|------|
| `docs/team/agent_pipeline_overview.md` | Agent/Chatbot 파이프라인 개요 + 모드별 사용법 |
| `docs/md/PIPELINE_FLOW.md` | RAG + Agent 전체 흐름도 |
| `configs/README.md` | agent.* 설정 체계 문서화 |
| `docs/llm/ARCHITECTURE_MAP.md` | Agent 경로 + 산출물 갱신 |
| `docs/llm/PROJECT_CONTEXT.md` | Agent 구현 상태 반영 |

## 확인한 것

- [x] 필요한 테스트 또는 실행 확인을 했습니다.
- [x] config 변경 시 프로젝트 루트 기준 상대 경로가 동작하는지 확인했습니다.
- [x] RAG 변경 시 retrieval / answer / citation 중 영향 범위를 확인했습니다.
- [x] 데이터, API key, 대용량 산출물, 임시 파일이 커밋에 포함되지 않았습니다.
- [x] 문서 업데이트 필요 여부를 확인했습니다.

## 실행 / 검증 결과

python -m pytest tests/ -k "not pdf" → 전체 통과

Agent 모드 (단일 질문):
python scripts/run_rag_agent.py --config configs/experiments/rag/agent/agent_lplus.yaml --question "예산은?"

챗봇 모드 (대화형):
python scripts/run_rag_agent.py --config configs/experiments/rag/agent/agent_lplus.yaml --verbose

Agent 평가:
python scripts/run_rag_agent.py --config configs/experiments/rag/agent/agent_lplus.yaml --evaluate

## 리뷰어가 봐야 할 부분

- `ChatbotRunner._select_tool()` — LLM 응답 JSON 파싱 실패 시 한국어 키워드 fallback이 의도대로 동작하는지
- `Tool.run()` — retriever 실패 시 OnFailure 정책에 따른 skip/abort 분기
- `AgentRunner.run()` — Phase DAG depends_on 그래프가 순차/병렬을 정확히 제어하는지
- config 상속 (`base_config`) — deep merge가 예상대로 동작하는지
