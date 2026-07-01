# 파이프라인 구조 설명

이 문서는 우리 RAG 파이프라인이 내부적으로 어떻게 돌아가는지, 실제 명령어와 실제 파일을 예시로 설명합니다.

"코드 한 줄 몰라도, 아래 예시를 따라가면 파이프라인 전체가 이해된다"가 목표입니다.

---

## 5분 안에 이해하는 파이프라인

**여러분이 하는 일은 딱 3가지입니다.**

### 첫째, 문서를 등록한다 (ingest)

터미널에 이렇게 칩니다:

```
python scripts/run_rag_ingest.py --config configs/experiments/rag/rag_langchain.yaml --project-root .
```

그러면 컴퓨터가 아래 3개 파일을 만듭니다:

| 생성된 파일 | 무슨 내용인가 | 실제 예시 |
|---|---|---|
| `experiments/rag_langchain/parsed_documents.csv` | "어떤 문서를 읽었더니 제목이 이거고, 몇 페이지짜리였고, 내용은 이렇더라" | `rfp_sample.txt` 파일을 읽었더니 3개 문단이 있었음 |
| `experiments/rag_langchain/chunks.csv` | "그 문서를 chunk_size=500 글자씩 잘랐더니 총 6조각이 나왔음" | `rfp_001_chunk_0001`: "제안 마감일은 2026년 7월..." |
| `experiments/rag_langchain/embeddings.jsonl` | "각 조각을 숫자 벡터로 변환했음 (나중에 검색용)" | `rfp_001_chunk_0001` → `[0.023, -0.451, ...]` |

### 둘째, 질문에 대한 근거를 찾는다 (retrieve)

```
python scripts/run_rag_retrieve.py --config configs/experiments/rag/rag_langchain.yaml --project-root . --question "예산은 얼마야?"
```

컴퓨터가 "예산은 얼마야?"라는 질문과 가장 비슷한 chunk를 위에서 만든 `chunks.csv` + `embeddings.jsonl`을 뒤져서 찾아냅니다.

결과는 `experiments/rag_langchain/retrieval_results.jsonl`에 저장됩니다:

```json
{
  "question": "예산은 얼마야?",
  "retriever_method": "semantic",
  "top_k": 3,
  "retrieved_chunks": [
    {"rank": 1, "chunk_id": "rfp_001_chunk_0002", "text": "예산 총액은 50억원..."},
    {"rank": 2, "chunk_id": "rfp_001_chunk_0005", "text": "사업비는 총 50억원 규모로..."},
    {"rank": 3, "chunk_id": "rfp_001_chunk_0001", "text": "제안 마감일은..."}
  ]
}
```

### 셋째, 근거를 바탕으로 답변을 만든다 (chat)

```
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_langchain.yaml --project-root . --question "예산은 얼마야?"
```

위에서 찾은 3개 chunk를 보고 답변을 만듭니다.

결과는 `experiments/rag_langchain/answers.jsonl`에:

```json
{
  "question": "예산은 얼마야?",
  "answer": "예산 총액은 50억원입니다.",
  "citations": [
    {"chunk_id": "rfp_001_chunk_0002", "source_path": "data/rag_sample/rfp_sample.txt"}
  ],
  "status": "answered"
}
```

---

## 왜 파일이 이렇게 여러 개인가?

"그냥 답변만 보여주면 안 되나요?" → **안 됩니다.**

답변이 틀렸을 때, **어디서 틀렸는지**를 알아야 고칠 수 있기 때문입니다.

| 증상 | 범인 | 확인할 파일 |
|---|---|---|
| 답변이 엉뚱하다 | 검색이 잘못된 chunk를 가져옴 | `retrieval_results.jsonl` |
| 답변은 맞는데 출처가 틀렸다 | citation 생성 로직 문제 | `answers.jsonl`의 `citations` 필드 |
| chunk 자체가 이상하다 | 문서가 너무 짧게/길게 잘림 | `chunks.csv` |
| 아예 답변이 "모르겠습니다" | 검색 결과 0건 or chunk가 빈 문자열 | `parsed_documents.csv` |

---

## 전체 흐름: 데이터가 어떻게 흘러가는가

```
[터미널 명령어]              [내부에서 일어나는 일]                   [생성되는 파일]

run_rag_ingest.py ──────→ ① PDF/DOCX에서 텍스트를 추출       → parsed_documents.csv
                              (pipeline.py → document_loader.py)

                        → ② 텍스트를 chunk_size 글자씩 자름   → chunks.csv
                              (chunk_size=500이면 500자씩)
                              (chunk_overlap=80이면 앞뒤 80자 겹침)

                        → ③ 각 chunk를 숫자 벡터로 변환      → embeddings.jsonl
                              (local: 빠름, huggingface: 정확)

run_rag_retrieve.py ────→ ④ 질문을 벡터로 변환해서
                              chunks.csv + embeddings.jsonl 중
                              가장 비슷한 top_k개를 찾음       → retrieval_results.jsonl
                              (method=keyword: 단어매칭)
                              (method=semantic: 의미매칭)
                              (method=hybrid: 둘 다 섞음)

run_rag_chat.py ────────→ ⑤ 찾은 chunk를 보고 답변 생성      → answers.jsonl
                              provider=local: 원문 그대로 추출
                              provider=ollama: LLM이 생성

run_rag_chat.py          → ⑥ 사람이 만든 정답(eval CSV)과
--evaluate                  비교해서 4개 지표 계산            → metrics.json
                                                              → bad_retrievals.csv
                                                              → unsupported_answers.csv
                                                              → failed_questions.csv
```

---

## 실제 실험 폴더를 열어보면

`experiments/rag_langchain/` 폴더 안에는 이런 파일들이 있습니다:

```
experiments/rag_langchain/
├── config.yaml                   ← 내가 사용한 Config가 그대로 복사됨
├── run_status.json               ← 각 단계 성공/실패 여부
│
├── parsed_documents.csv          ← ① 어떤 문서를 읽었는지
├── chunks.csv                    ← ② 문서를 어떻게 잘랐는지
├── embeddings.jsonl              ← ③ 벡터로 변환한 결과
│
├── retrieval_results.jsonl       ← ④ 질문별 검색 결과
├── answers.jsonl                 ← ⑤ 질문별 답변 + citation
│
├── evaluation_results.csv        ← ⑥ 질문별 정답 비교 결과
├── metrics.json                  ← ⑥ 전체 점수 (4개 지표)
├── bad_retrievals.csv            ← ⑥ 검색 실패한 질문만 모음
├── unsupported_answers.csv       ← ⑥ 답변/citation 틀린 질문만
├── failed_questions.csv          ← ⑥ 실행 중 오류난 질문만
│
├── rag_ingest_checkpoint.json    ← 어디까지 처리했는지 기록
└── README.md                     ← 실험 요약
```

---

## Config 하나만 바꿨을 때 무슨 일이?

예시: `rag_langchain.yaml`에서 `chunk_size`를 500 → 800으로 바꿨다면?

```
변경 전 (chunk_size=500):
  chunks.csv → 6개 chunk (평균 450자)

변경 후 (chunk_size=800):
  chunks.csv → 3개 chunk (평균 720자)
```

chunk가 커지면: 한 chunk에 더 많은 정보가 들어감 → 검색이 더 넓은 맥락을 잡을 수 있음.
하지만 chunk가 너무 크면: 검색 결과가 질문과 무관한 내용까지 포함할 수 있음.

그래서 **실험의 기본 사이클**은:
1. Config에서 **하나만** 바꾼다
2. ingest부터 다시 돌린다
3. `metrics.json`을 확인한다
4. 점수가 올랐는지 내렸는지 기록한다
5. 다시 1로 돌아간다

---

## configs/experiments/rag/ 폴더에는 뭐가 있나

| Config 파일 | 용도 | 언제 쓰나 |
|---|---|---|
| `rag_langchain.yaml` | TXT 샘플로 파이프라인 정상작동 확인 | 가장 먼저, 무조건 |
| `rag_realistic_docs.yaml` | DOCX/HWPX 실제 문서 형식 테스트 | 문서 loader가 깨지는지 확인할 때 |
| `rag_keyword.yaml` | keyword 방식 검색 (local 엔진) | retriever 비교할 때 |
| `rag_semantic.yaml` | semantic 방식 검색 (local 엔진) | retriever 비교할 때 |
| `rag_hybrid.yaml` | keyword + semantic 혼합 (local 엔진) | retriever 비교할 때 |

비교 실험은 `compare_rag_retrievers.py`가 자동으로 3개 config를 다 돌리고 `reports/rag_retriever_comparison.csv`로 만들어줍니다.

---

## 자주 하는 질문

**Q: `chunk_size`를 200으로 바꿨는데 점수가 더 나빠졌어요. 왜 그런가요?**

A: chunk가 너무 작으면 문장 하나가 두 chunk로 찢어질 수 있습니다.
예를 들어 이런 경우입니다:

```
chunk_size=200 (너무 작음):
  chunk_1: "2026년 제안 마감일은"     ← "언제" 정보가 없음 → 검색 실패
  chunk_2: "7월 31일 18:00까지다"     ← "무엇의" 정보가 없음 → 검색 실패

chunk_size=500 (적당):
  chunk_1: "2026년 제안 마감일은 7월 31일 18:00까지다"  ← 완전한 정보 → 검색 성공
```

해결: `chunk_size`를 늘리거나 `chunk_overlap`을 늘려서 정보가 찢어지지 않게 하세요.


**Q: hybrid가 무조건 제일 좋은 방식인가요?**

A: 이론적으로는 그렇지만, 문서 특성에 따라 다릅니다.

예를 들어 RFP 문서에 "총 예산: 50억원"이라고 정확히 쓰여 있으면:
- keyword 방식: "예산"이라는 단어가 정확히 매칭 → 1등으로 찾음
- semantic 방식: "예산"과 "비용", "금액"을 비슷한 의미로 처리 → 1등이 다른 chunk일 수도 있음
- hybrid 방식: 둘을 섞어서 keyword의 강점을 살림 → 보통 가장 안정적

문서가 짧고 용어가 일관되면 keyword만으로도 충분히 좋은 점수가 나옵니다.
실제로 비교해보려면 `compare_rag_retrievers.py`를 돌려서 3가지 방식을 한 번에 측정하세요.


**Q: local answerer와 ollama answerer의 결과가 완전히 다릅니다. 어느 게 맞나요?**

A: 평가 질문 CSV의 `expected_answer` 기준으로 판단합니다.

```
local answerer (추출형):
  chunk 원문: "예산 총액은 50억원이다."
  답변: "예산 총액은 50억원이다."     ← 원문 그대로

ollama answerer (생성형):
  chunk 원문: "예산 총액은 50억원이다."
  답변: "이 사업의 예산은 50억원입니다." ← 자연스럽지만 원문과 다름
```

`expected_answer`가 "50억원"이면 둘 다 맞습니다 (answer_contains_expected_rate = 1.0).
`expected_answer`가 "예산 총액은 50억원"이면 local만 맞고 ollama는 틀립니다.

따라서 **평가 질문 CSV를 만들 때 `expected_answer`를 어떻게 쓸지**가 중요합니다.
핵심 키워드만 적을지, 원문 그대로 적을지 팀과 합의하세요.


**Q: Config 하나 수정했는데 어떤 명령어를 다시 실행해야 하나요?**

A: 바꾼 항목에 따라 다릅니다.

| Config에서 바꾼 것 | 다시 실행할 명령어 | 이유 |
|---|---|---|
| `rag.splitter.chunk_size` | `run_rag_ingest.py` + `run_rag_retrieve.py` + `run_rag_chat.py --evaluate` | chunk가 바뀌면 그 이후 모든 게 바뀜 |
| `rag.embedding.provider` | `run_rag_ingest.py` + 이후 전부 | embedding이 바뀌면 검색 결과도 바뀜 |
| `rag.retriever.method` | `run_rag_retrieve.py` + `run_rag_chat.py --evaluate` | chunk/embedding은 그대로, 검색만 다시 |
| `rag.retriever.top_k` | `run_rag_retrieve.py` + `run_rag_chat.py --evaluate` | 검색 결과 개수만 다시 |
| `rag.answerer.provider` | `run_rag_chat.py --evaluate` | 검색 결과는 그대로, 답변만 다시 |
| `evaluation.questions_path` | `run_rag_chat.py --evaluate` | 평가 질문만 바뀜 |
| `agent.tools` / `agent.max_steps` | `run_rag_agent.py --evaluate` | Agent 실행만 다시 |

팁: 노트북에서 FLAG를 쓰면 `RUN_INGEST=False`로 두고 필요한 부분만 다시 돌릴 수 있습니다.


**Q: `experiments/rag_langchain/` 폴더에 파일이 하나도 없어요.**

A: `run_rag_ingest.py`를 아직 실행하지 않은 상태입니다.
순서대로:
```
python scripts/run_rag_ingest.py --config configs/experiments/rag/rag_langchain.yaml --project-root .
```
를 먼저 실행하세요. 그래도 안 되면:
- `paths.raw_docs_dir`가 실제 존재하는 폴더인지 Config를 확인하세요.
- `paths.output_dir`이 쓰기 가능한 경로인지 확인하세요.


**Q: 점수가 1.0이 나왔는데 이게 정상인가요?**

A: 샘플 데이터(`data/rag_sample/`)로 돌리면 1.0이 나오는 게 정상입니다.
샘플 데이터는 파이프라인이 잘 돌아가는지 확인하는 용도로, 질문과 chunk가 서로 딱 맞게 만들어져 있습니다.

실제 RFP 문서를 넣으면 점수가 0.3~0.6 정도로 떨어지는 게 일반적입니다.
그때부터 Config를 바꿔가며 점수를 올리는 실험이 시작됩니다.


**Q: `rag.engine`을 `local`로 해야 하나요, `langchain`으로 해야 하나요?**

A:
- `langchain`: 모든 기능 사용 가능. Chroma 벡터DB, Ollama/OpenAI LLM, RecursiveCharacterTextSplitter 등
- `local`: pip install 없이 돌아가는 경량 모드. 속도 빠르지만 기능 제한적 (keyword/semantic/hybrid 검색 + 추출형 답변만)

처음 시작할 땐 무조건 `langchain`을 쓰세요. `local`은 의존성 문제로 langchain을 못 쓸 때의 비상용입니다.


**Q: 평가 질문 CSV는 어떻게 만드나요?**

A: [golden_dataset_guide.md](golden_dataset_guide.md)를 참고하세요.
간단히 말하면:
1. `run_rag_ingest.py`로 실제 문서를 먼저 돌린다
2. `chunks.csv`를 열어서 어떤 chunk가 있는지 파악한다
3. 각 chunk에서 답변 가능한 질문을 만들고, 정답과 어떤 chunk_id에서 왔는지 CSV에 기록한다

---

## Agent 모드

`ingest → retrieve → answer`의 단일 흐름을 넘어, 여러 Tool을 순차적으로 조합하는 **Agent 모드**가
`scripts/run_rag_agent.py`로 제공됩니다.

```bash
python scripts/run_rag_agent.py --config configs/experiments/rag/agent/agent_lplus.yaml --project-root . --question "이 RFP 요약해줘"
```

Agent 모드는 `agent.enabled: true` config에서 활성화되며, Phase DAG에 따라 Tool을
순차 실행하고 structured output을 생성합니다. 자세한 구조는 [agent_pipeline_overview.md](agent_pipeline_overview.md)를 참고하세요.

---

## 관련 문서

- 파이프라인 입출력 계약 (상세): [docs/md/rag/RAG_PIPELINE_SPEC.md](../md/rag/RAG_PIPELINE_SPEC.md)
- Agent 파이프라인 개요: [agent_pipeline_overview.md](agent_pipeline_overview.md)
- 프론트엔드 연결 계약 (UI 개발자용): [rag_frontend_contract.md](rag_frontend_contract.md)
- 실험 실행 가이드: [docs/md/experiments/EXPERIMENT_GUIDE.md](../md/experiments/EXPERIMENT_GUIDE.md)
- 골든 데이터셋 구축 가이드: [golden_dataset_guide.md](golden_dataset_guide.md)
- 첫 주 작업 목록: [first-week.md](first-week.md)
- 실행 전 검증 체크리스트: [rehearsal.md](rehearsal.md)
- 노트북 사용법: [../md/experiments/NOTEBOOK_USAGE_CHECKLIST.md](../md/experiments/NOTEBOOK_USAGE_CHECKLIST.md)
