# Vector DB 선정 보고서

> **작성일**: 2026-07-05 | **결정**: ChromaDB

---

## 1. 선정 기준

| 기준 | 설명 |
|------|------|
| 배포 용이성 | Python 3.11 + conda 환경에서 추가 설치 없이 사용 가능해야 함 |
| 초기 규모 | 문서 100건, chunk 약 2,000~5,000건 규모에서 충분한 성능 |
| LangChain 통합 | 기존 LangChain 기반 엔진과 자연스럽게 연결 |
| 메타데이터 필터 | document_id, section, page 기준 필터링 |
| 확장 가능성 | 추후 PostgreSQL+pgvector 등으로 마이그레이션 가능한 구조(추후 확장이 용이하다는건 발표 근거가 될 수 있음) |

---

## 2. 후보 비교

|  | ChromaDB | FAISS | LanceDB | Qdrant |
|---|---|---|---|---|
| **설치** | `pip install chromadb` | `conda install faiss-cpu` | `pip install lancedb` | Docker 권장 |
| **의존성** | 이미 `requirements.txt`에 있음 (`langchain-chroma==1.0.0`) | 추가 설치 필요 | 추가 설치 필요 | 추가 설치 필요 |
| **속도 (소규모)** | 빠름 (5K건 기준 수ms) | 매우 빠름 | 빠름 | 빠름 |
| **속도 (대규모)** | 100K+에서 저하 | 100만건도 실시간 | 100만건도 실시간 | 수백만건 실시간 |
| **메타데이터 필터** | O (where 조건) | 직접 구현 필요 | O (컬럼 기반, 강력) | O (payload index) |
| **Full-Text Search** | X | X | X | O (payload index) |
| **영속성** | 자동 (SQLite 기반) | 수동 (index 파일 저장/로드) | 자동 (Lance 파일) | 자동 |
| **LangChain 통합** | O (공식) | O (langchain-community) | X (직접 구현) | O (langchain-community) |
| **프로젝트 적용 난이도** | **하** (import만 하면 됨) | 중 (인덱스 관리 코드 필요) | 중 (신규 의존성 추가) | 상 (Docker 필요) |

---

## 3. 최종 선정: ChromaDB

### 채택 사유

1. **의존성 추가 제로** — `requirements.txt`에 `langchain-chroma==1.0.0`이 이미 포함되어 있음. 추가 설치 없이 `import chromadb`만으로 바로 사용 가능
2. **구현 난이도 최저** — LangChain 공식 통합으로 `Chroma.as_retriever()` 한 줄이면 검색기 완성. FAISS처럼 index 저장/로드를 직접 구현할 필요 없음
3. **현재 규모에 적합** — 문서 100건, chunk 5,000건 수준에서는 충분한 성능 (수ms 응답). 100K건 이상으로 커지기 전까지 문제 없음
4. **영속성 기본 제공** — SQLite 기반으로 별도 설정 없이 DB 파일로 저장되어 서버 재시작 후에도 유지

### 한계 및 대응 계획

| 한계 | 대응 |
|------|------|
| 100K+ chunk에서 검색 속도 저하 | 현재 파일 규모에서는 문제 없음, 추후 규모가 커질 경우에 고려할 것 |
| Full-Text Search 미지원 | SQLite FTS5 또는 기존 keyword retriever와 병행 |
| 단일 머신 전용 (분산 안 됨) | 현재 VM 단일 서버로 충분. 분산 필요 시 Qdrant 검토 |

---

## 4. 적용 범위

```
[변경 전]                          [변경 후]
embeddings.jsonl 파일               ChromaDB Collection
    ↓                                  ↓
ChatbotRunner.load_document_context()  chatbot.connect_collection(run_id)
    ↓                                  ↓
self.embeddings (list in memory)      collection.query(query_embedding)
```

- `adapters.py` → `ChromaRetrieverAdapter` 신규 추가
- `chatbot.py` → `load_document_context()` → Chroma connection으로 대체
- `rag_service.py` → `_chatbot_cache` → Chroma client 관리로 변경

---