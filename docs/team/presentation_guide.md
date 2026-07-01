# 팀 발표 가이드 — RAG 파이프라인 + 서비스 계층

## 발표 흐름 (10~15분)

### 1. 우리가 만든 것 — 한 장 그림 (2분)

```
사용자 업로드 문서
      │
      ▼
app/services/rag_service.py     ← "서비스 어댑터" (오늘의 주인공)
      │
      ├── create_and_ingest()   → src/rag/pipeline.py  → chunks.csv + embeddings.jsonl
      ├── summarize()           → extract_facts Tool
      ├── extract_requirements()→ extract_requirements Tool
      ├── compare()             → compare_rfps Tool
      └── ask_with_document_filter() → ChatbotRunner (LLM이 Tool 자동 선택)
                                             │
                                             ▼
                                   reply + structured_output + citations
```

**핵심 문장:** "UI는 RAG 내부를 전혀 몰라요. `rag_service.py` 함수만 호출하면 됩니다."

---

### 2. 왜 이렇게 했는가 — 문제 → 해결 (2분)

| 문제 | 해결 |
|------|------|
| Streamlit에서 `src.rag.*` 직접 import하면 UI 바꿀 때마다 파이프라인도 깨짐 | `rag_service.py`라는 중간 계층을 둠 |
| mock_data.py로는 실제 RAG 검증 불가능 | `rag_service.py`가 실제 파이프라인 호출 |
| config가 코드에 하드코딩되면 실험 결과 반영 불가능 | `streamlit.yaml`이 `agent_lplus.yaml` 상속 → 연구자가 config만 바꾸면 서비스도 자동 반영 |
| 챗봇 기능마다 코드를 새로 짜야 함 | Tool 기반 — config에 Tool 하나 추가 = 새 기능 완성 |

---

### 3. 연결 구조 — 세 가지 계층 (3분)

```
[config 계층]            streamlit.yaml → agent_lplus.yaml → rag-baseline.yaml
                             │                    │
                         paths만 override    Tool·프롬프트·embedding·retriever
                             │
[서비스 계층]           app/services/rag_service.py
                             │
                    create_and_ingest | summarize | extract_requirements
                    compare | ask | ask_with_document_filter | run_tool
                             │
[UI 계층]               Streamlit (app/views/)
                             │
                    reply | structured_output | citations
```

**중요:** Tool 추가는 config만 수정하면 됨. 예:

```yaml
# streamlit.yaml → agent.tools 아래에 추가
summarize_risks:
  description: "RFP 문서의 리스크/독소조항을 분석합니다."
  retriever:
    top_k: 8
  answerer:
    prompt_template: |
      아래 근거에서 계약상 불리한 조항을 찾아내라.
      {context}
      질문: {question}
    temperature: 0.1
```

이 한 방이면 챗봇이 "리스크 분석해줘" 라고 하면 자동으로 이 Tool을 선택해서 돌아감. **코드 변경 제로.**

---

### 4. 계약 — UI 개발자가 알면 되는 것 (2분)

| 함수 | 언제 호출 | 반환 |
|------|----------|------|
| `create_and_ingest(raw_docs_dir)` | 파일 업로드 직후 | `{run_id, status, documents, chunks}` |
| `summarize(run_id, selected_doc_ids)` | 요약 버튼 | `{reply, structured_output, citations}` |
| `extract_requirements(run_id, selected_doc_ids)` | 요구사항 버튼 | `{reply, structured_output, citations}` |
| `compare(run_id, selected_doc_ids)` | 비교 버튼 (2개 이상 선택 시) | `{reply, structured_output, citations}` |
| `ask_with_document_filter(run_id, q, doc_ids)` | 채팅 입력 | `{reply, structured_output, citations}` |
| `get_documents(run_id)` | 문서 목록 표시 | `[{document_id, title, chunk_count}]` |

**응답 스키마:**
```python
{
    "reply": "사용자에게 보여줄 텍스트",
    "tool_used": "extract_facts",
    "structured_output": {"사업명": "...", "발주기관": "...", ...},
    "citations": [{"source_path": "...", "page": "3", "chunk_id": "..."}],
    "status": "ok",
    "error": None
}
```

---

### 5. 역할별 — 각자 뭘 보면 되는가 (1분)

| 역할 | 볼 문서 | 할 일 |
|------|---------|-------|
| **UI 개발자** | `rag_frontend_contract.md` + `rag_contract_demo.py` | 계약 함수만 호출해서 화면 구성 |
| **Experiment Lead** | `rag-baseline.yaml` + `agent_lplus.yaml` | config 튜닝, 새 Tool 추가 |
| **PM** | `SPRINT_PLAN.md` + 이 문서 | 전체 상황 파악 |
| **Data Engineer** | 기존 `data_engineer_guide.md` | 내부 문서 100건 ingest |

---

### 6. 앞으로 — 확장 방향 (1분)

1. **내부 문서 100건 사전 ingest** → `build_internal_corpus.py` 실행, enterprise run_id 하나로 전체 Q&A
2. **새 Tool 추가** → config에 10줄만 추가하면 챗봇이 인식
3. **FastAPI 전환** → `rag_service.py`를 그대로 API로 감싸면 됨 (서비스 계층이 이미 분리돼 있음)
4. **React 프론트** → `rag_service.py` 함수 계약만 유지하면 어떤 프론트도 붙일 수 있음

---

## 시연 시나리오

```bash
# 1. 서비스 어댑터 계약 검증
python -m streamlit run app/views/rag_contract_demo.py

# 흐름: 파일 업로드 → 분석 실행 → 요약/요구사항 카드 → 채팅 질문 → citation 확인
```

또는 CLI로 빠르게:

```bash
python app/examples/rag_contract_example.py /path/to/docs --question "사업 예산은?"
```

---

## 참고 문서

| 문서 | 대상 | 용도 |
|------|------|------|
| [rag_frontend_contract.md](rag_frontend_contract.md) | UI 개발자 | 함수 계약, 응답 스키마, 표시 방식 |
| [agent_pipeline_overview.md](agent_pipeline_overview.md) | 전체 | Agent/Chatbot 작동 원리 |
| [pipeline_walkthrough.md](pipeline_walkthrough.md) | 전체 | 파이프라인 내부 구조 |
| [SPRINT_PLAN.md](SPRINT_PLAN.md) | PM/전체 | 스프린트 계획 |
| `app/views/rag_contract_demo.py` | UI 개발자 | 실제 동작하는 참고 화면 |
| `app/examples/rag_contract_example.py` | UI 개발자 | CLI 예제 |
| `configs/experiments/rag/streamlit.yaml` | Experiment Lead | 서비스 config 템플릿 |
