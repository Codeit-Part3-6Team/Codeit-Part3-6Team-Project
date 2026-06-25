# 2026-06-24 일일 요약 — Agent Loop 설계 평가 및 계획 보강

## 1. 오늘의 목표

- `fix/answer-quality` 브랜치 완성 직후, Config → 코드 갭 전수 분석
- Agent Loop + Tool I/F + Structured Output 구현 계획의 현실성 평가
- Config만으로 L+까지 도달 가능한지, XL은 추가 구현 얼마나 필요한지 판단

## 2. 수행한 작업

| 작업 | 내용 |
|------|------|
| **전체 코드베이스 감사** | `src/rag/` 전체 + `configs/` + `tests/` + `app/` 하드코딩·결합도 스캔 |
| **Agent Loop 계획 평가** | 원계획 7개 Config→코드 갭 + 3개 하드코딩 결합 진단 검증 |
| **추가 문제점 22건 식별** | 계획에 없던 Config 키 혼선, Dead config, 코드 중복, 확장성 저해 요소 발굴 |
| **Config 인터페이스 평가** | `rag_agent.yaml` + `configs/README.md` 부실 지점 8건 식별 |
| **데모 앱 연동 가능성 검증** | `app/mock_data.py` ↔ RAG Pipeline 출력 구조 계약 확인 |
| **계획 문서 갱신** | `reports/agent_loop_implementation_plan.md` — 부록 A/B/C + 우선순위 보강 |

## 3. 핵심 판단

| 질문 | 결론 |
|------|------|
| Config만으로 L+까지 가능한가? | **가능.** Phase DAG + Tool + output_schema + company_profile 주입으로 충분 |
| Config만으로 XL까지 가능한가? | **불가.** Rule 엔진, 외부DB 커넥터, cross-doc citation chaining은 추가 구현 필요 |
| XL 가려면 추가 구현 얼마나? | Tool plugin 2~3개 (`RegulatoryCheckTool`, `SimilarBidSearchTool`, `RiskScoringTool`). Phase 체이닝·State 전파는 Agent Loop가 이미 제공 |
| 데모 앱 붙일 때 모델 교체해도 앱 수정 필요한가? | **필요 없음.** `RagAnswererAdapter.answer()` Protocol로 출력 구조 통일. 브릿지 함수 10줄이면 mock→실제 교체 완료 |
| Streaming은? | adapter에 streaming 인터페이스 추가 필요 (계획에 포함) |

## 4. 산출물

| 파일 | 용도 |
|------|------|
| `reports/agent_loop_implementation_plan.md` | Agent Loop 전체 구현 계획 (원본 + 보강) |
| `reports/daily_2026-06-24_agent_loop_planning.md` | 이 문서 |

## 5. 발견된 리스크 (계획 외)

| 리스크 | 심각도 | 대응 |
|--------|:---:|------|
| `pipeline.py:174` `_CHAT_HISTORY` 글로벌 dict | 🔴 | AgentRunner 인스턴스화 시 제거 |
| `rag.chunk` vs `rag.splitter` 이중 키 | 🟡 | 단일화 마이그레이션 |
| `max_tokens` 기본값 불일치 (256 vs 512) | 🟡 | 통일 |
| Dead config 5종 (`backup`, `metric`, `rag.llm` 등) | 🟢 | 정리 또는 구현 |
| Agent config 인터페이스 부실 (prompt_template, input_from, on_failure 미정의) | 🟡 | 계획 부록 B에 보강안 제시 |

## 6. 구현 우선순위 요약

```
Phase 1 (M 서비스):  adapters.py openai/ollama  →  schema_parser.py  →  tool.py
Phase 2 (L~L+):      agent.py  →  langchain.py 통합  →  pipeline.py 분기
Phase 3 (완성):      validation.py  →  judge.py 확장  →  configs/README.md 문서화
```

## 7. Next Action

1. 계획 리뷰 완료 후 `feature/agent-loop` 브랜치에서 Phase 1 구현 착수
2. `app/mock_data.py` → 실제 RAG 브릿지 연결은 Agent Loop 완성 후 별도 작업
3. XL 진입은 L+ 검증 완료 후 Tool plugin 개발로
