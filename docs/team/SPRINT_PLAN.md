# Sprint Plan (6/23 ~ 7/8 발표)

---

## Experiment Lead — 유수빈

**목표**: RAG 베이스라인 성능 고도화

| # | Task | 산출물 | 상태 |
|---|------|--------|------|
| 1 | VM에서 `rag_langchain.yaml` ingest 실행 | `parsed_documents.csv`, `chunks.csv`, `embeddings.jsonl` | 대기 |
| 2 | 단건 retrieve/chat 테스트 | retrieval 품질, answer 품질 확인 | 대기 |
| 3 | metric 뽑기 (`--evaluate`) | `metrics.json` (retrieval_hit_rate, citation_correct_rate 등) | 대기 |
| 4 | chunk_size, top_k, retriever_method 튜닝 | 실험 config 2~3종 + 결과 비교 | 대기 |
| 5 | Ollama 모델 pull (`nomic-embed-text`, `llama3.2`) | VM 모델 준비 | 대기 |

**실행 명령어**:
```bash
# 1. ingest
python scripts/run_rag_ingest.py --config configs/experiments/rag/rag_langchain.yaml --project-root .

# 2. 단건 테스트
python scripts/run_rag_retrieve.py --config ... --question "예산이 얼마야?"
python scripts/run_rag_chat.py --config ... --question "예산이 얼마야?"

# 3. 평가
python scripts/run_rag_chat.py --config ... --evaluate
```

---

## Presentation Lead — 정진우

**목표**: 데모 앱 스택 조사 + 최종 발표 준비

| # | Task | 산출물 | 상태 |
|---|------|--------|------|
| 1 | 데모 앱 프레임워크 조사 (Streamlit / Gradio / Chainlit) | 비교 요약 | 대기 |
| 2 | VM에서 웹앱 띄웠을 때 팀원 접속 방식 조사 | "이 방식으로" 한 줄 결론 | 대기 |
| 3 | 기술 보고서 초안 작성 (데이터→파이프라인→실험→서비스화 흐름) | 보고서 문서 | 대기 |
| 4 | 최종 발표 자료 준비 (15분, 전체 취합) | 슬라이드 + 대본 | 대기 |

**발표 흐름 제안**:

| 순서 | 시간 | 내용 | 자료 출처 |
|------|------|------|-----------|
| 1 | 2분 | 프로젝트 개요 + 문제 정의 | 공통 |
| 2 | 3분 | 데이터: 100건 RFP, 평가셋 897건, DE 작업 | DE → PL 취합 |
| 3 | 3분 | RAG 파이프라인: ingest → chunk → embed → 검색 → 답변 | EL → PL 취합 |
| 4 | 3분 | 실험 결과: metric, 성능 진척, 튜닝 효과 | EL → PL 취합 |
| 5 | 3분 | 서비스 확장: M(요약)→L(비교) 로드맵 + 데모 앱 | PM + PL |
| 6 | 1분 | 향후 계획 | 공통 |
| — | 10분 | Q&A | 전원 지원 |

---

## Data Engineer — 정승호

**목표**: 평가셋 확장 + 데이터 보정

| # | Task | 산출물 | 상태 |
|---|------|--------|------|
| 1 | `eval_questions.csv` Drive 업로드 | - | ✅ 완료 |
| 2 | M(요약)용 평가셋: 897건 중 복합질문 30~50건 선별 | `eval_questions_summary.csv` | 대기 |
| 3 | L(비교)용 평가셋: 2~3건 문서 조합 비교질문 10~20건 초안 | `eval_questions_compare.csv` | 대기 |
| 4 | `data_list.csv` 7건 텍스트 불량 수동 보정 (HWP 직접 파싱 결과로) | `data_list.csv` 수정본 | 대기 |

**M 평가셋 예시**:
```csv
question,expected_answer
"이 RFP의 예산, 기간, 자격을 모두 알려줘","예산: 5억, 기간: 6개월, 자격: SW사업자"
"제출 서류 전부 나열해줘","제안서, 사업자등록증, 실적증명서, ..."
```

**L 평가셋 예시**:
```csv
question,expected_answer
"A사업과 B사업 중 예산이 더 큰 쪽은?","A사업 (5억 vs 3.2억)"
"세 RFP 중 자격이 가장 까다로운 것은?","B사업 — 보안인증 추가 필요"
```

---

## Project Manager — 윤승준

**목표**: 서비스 기획 + 방향 설정

| # | Task | 산출물 | 상태 |
|---|------|--------|------|
| 1 | 팀 회의 주도: `SERVICE_PLANNING.md` 발표 + M/L/XL 결정 | 회의록, 결정사항 | 대기 |
| 2 | M(요약) 리포트 항목 리스트 확정 | "예산, 일정, 자격, 서류, 발주기관, 평가기준, 특이사항..." | 대기 |
| 3 | "RFP 요약 전문가" 페르소나 + 시스템 프롬프트 초안 | 프롬프트 텍스트 | 대기 |
| 4 | `docs/fix-csv-column` 브랜치 PR 생성 후 머지 | 브랜치 정리 | 대기 |

**M 요약 항목 초안 (검토용)**:
- 사업명, 예산(금액), 사업기간, 발주기관
- 참가자격 요약, 제출서류 목록
- 평가기준 (기술/가격 비율)
- 입찰방식 (협상/적격심사/...)
- ⚠ 특이사항 (예산이 0원이면 "비공개", 자격 없으면 "문서 미기재")

---

## 전체 일정

| 주차 | 기간 | 내용 |
|------|------|------|
| **1주차** | 6/23~6/27 | 방향 결정 + RAG 베이스라인 실험 + 평가셋 준비 + 앱 조사 |
| **2주차** | 6/30~7/4 | RAG 성능 고도화 완료 → M(요약) 구현 착수 |
| **3주차** | 7/7~7/8 | 발표 준비 + 자료 정리 + 데모 영상 촬영 |

- 1주차 목표: EL metric 확보, DE 평가셋 완료, PL 앱 스택 결정
- 2주차 목표: M(요약) MVP 완성 — RFP 던지면 한 장 요약 나오는 데모
- 3주차: 발표자료 + 시연 영상
