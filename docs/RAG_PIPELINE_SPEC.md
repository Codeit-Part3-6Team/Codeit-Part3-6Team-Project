# RAG 파이프라인 스펙

이 문서는 RFP 분석 챗봇을 만들 때 사용할 RAG 파이프라인의 입력/출력 계약을 정리합니다.
목표는 구현을 바로 시작하기 전에, 각 단계가 무엇을 받고 무엇을 남겨야 하는지 먼저 맞추는 것입니다.

## 한 줄 요약

RAG 파이프라인은 **문서를 작은 근거 단위로 쪼개고, 질문과 관련 있는 근거를 검색한 뒤, 그 근거를 바탕으로 답변과 출처를 함께 반환하는 구조**입니다.

```text
raw document
  -> parsed document
  -> chunks
  -> embeddings
  -> retrieved chunks
  -> answer + citations
```

현재 smoke pipeline은 여기까지 구현되어 있습니다.
별도 vector DB/index는 아직 만들지 않고, `embeddings.jsonl`을 읽어 cosine similarity로 검색합니다.

## 왜 계약이 필요한가

RAG는 단순히 LLM에게 문서를 넣고 답하게 만드는 작업이 아닙니다.
문서 파싱, chunking, embedding, 검색, 답변 생성이 모두 연결되어야 합니다.

계약이 없으면 다음 문제가 생깁니다.

- chunk가 어떤 문서/페이지에서 왔는지 추적하기 어렵습니다.
- 검색 결과가 답변에 제대로 쓰였는지 확인하기 어렵습니다.
- 답변의 출처를 발표나 데모에서 보여주기 어렵습니다.
- 모델이 모르는 내용을 꾸며냈는지 판단하기 어렵습니다.

그래서 RAG에서는 **답변 자체보다 답변의 근거를 남기는 것**이 중요합니다.

## 폴더 구조 초안

```text
data/
|-- raw_docs/              # 원본 RFP 문서
|-- processed_docs/        # 파싱/청킹 결과
`-- rag_smoke/             # 작은 txt 기반 smoke test 문서

indexes/
`-- rag_smoke/             # vector index 후보

experiments/
`-- rag_smoke_test/        # 검색/답변 실험 산출물

src/
`-- rag/
    |-- document_loader.py
    |-- chunker.py
    |-- embedder.py
    |-- vector_store.py
    |-- retriever.py
    |-- answerer.py
    `-- pipeline.py

scripts/
|-- run_rag_ingest.py
|-- run_rag_retrieve.py
`-- run_rag_chat.py
```

처음 smoke 데이터는 작은 `.txt` 문서이지만, loader 자체는 `txt`, `pdf`, `docx`, `hwpx`, `hwp`를 대상으로 합니다.

## 현재 구현된 smoke pipeline

현재 구현은 외부 모델이나 vector DB 없이 RAG 운영 흐름을 먼저 검증하는 버전입니다.
embedding은 문자 n-gram 기반 hashing vector를 사용하고, 검색은 cosine similarity에 keyword 보정을 더해 수행합니다.

실행 config:

```text
configs/rag_smoke_test.yaml
```

샘플 데이터:

```text
data/rag_smoke/
|-- rfp_sample.txt
`-- eval_questions.csv
```

실행 명령:

```bash
python scripts/run_rag_ingest.py --config configs/rag_smoke_test.yaml --project-root .
python scripts/run_rag_retrieve.py --config configs/rag_smoke_test.yaml --project-root . --question "예산이 얼마야?"
python scripts/run_rag_chat.py --config configs/rag_smoke_test.yaml --project-root . --question "예산이 얼마야?"
python scripts/run_rag_chat.py --config configs/rag_smoke_test.yaml --project-root . --evaluate
```

현재 구현된 단계:

- `document_loader.py`: txt/pdf/docx/hwpx/hwp 문서를 document row로 변환
- `chunker.py`: document row를 검색 가능한 chunk row로 변환
- `embedder.py`: chunk text를 hashing embedding으로 변환
- `vector_store.py`: 질문 embedding과 chunk embedding을 비교해 top-k 검색
- `retriever.py`: keyword fallback 검색
- `answerer.py`: 검색된 chunk에서 답변 문장 추출 및 citation 생성
- `pipeline.py`: ingest/retrieve/chat/evaluation 실행과 산출물 저장

현재 산출물:

```text
experiments/rag_smoke_test/
|-- parsed_documents.csv
|-- chunks.csv
|-- embeddings.jsonl
|-- retrieval_results.jsonl
|-- answers.jsonl
|-- evaluation_results.csv
|-- bad_retrievals.csv
|-- unsupported_answers.csv
|-- failed_questions.csv
|-- metrics.json
|-- config.yaml
|-- run_status.json
|-- failure.log         # 실패한 경우
`-- run_info.json
```

현재 metric:

- `retrieval_hit_rate`
- `answer_contains_expected_rate`
- `citation_correct_rate`
- `not_found_rate`

검색 방식 비교:

```bash
python scripts/compare_rag_retrievers.py --project-root .
```

기본 비교 대상은 `configs/rag_smoke_keyword.yaml`와 `configs/rag_smoke_test.yaml`입니다.
비교 결과는 `reports/rag_retriever_comparison.csv`와 `reports/rag_retriever_comparison.json`에 저장됩니다.

이 구현의 목적은 성능이 아니라, RAG 프로젝트에서도 config 기반 실행, embedding 산출물 저장, citation 추적, 평가 산출물 저장, 실험 요약이 끝까지 이어지는지 확인하는 것입니다.
실행 상태는 `run_status.json`에 남기고, 실패한 경우 `failure.log`에 traceback과 에러 메시지를 남깁니다.

## 1. Document Input

원본 문서를 파싱한 뒤에는 최소한 아래 정보를 보존합니다.

```csv
document_id,title,source_path,page,section,text
rfp_sample,샘플 RFP,data/rag_smoke/rfp_sample.txt,1,사업 개요,"본 사업의 예산은 5천만 원입니다."
```

필수 컬럼:

- `document_id`: 문서를 구분하는 id
- `title`: 문서 제목
- `source_path`: 원본 파일 경로
- `page`: 페이지 번호 또는 없으면 1
- `section`: 문서 안의 구역명
- `text`: 파싱된 본문

원칙:

- 답변에 출처를 붙이려면 `document_id`, `source_path`, `page`를 잃지 않아야 합니다.
- 파일 형식이 달라도 downstream에서는 같은 document row 형태를 사용합니다.
- PDF는 페이지 단위, txt/docx/hwpx는 섹션/본문 단위로 시작합니다.
- HWP는 `olefile` 기반 best-effort 추출이라 실제 문서에 따라 추가 보정이 필요할 수 있습니다.

지원 파일 형식:

| 형식 | 현재 처리 방식 |
|---|---|
| txt | `#`, `##` heading을 기준으로 section 분리 |
| pdf | `pypdf`로 페이지별 text 추출 |
| docx | zip 내부 `word/document.xml`에서 paragraph 추출 |
| hwpx | zip 내부 XML에서 paragraph 추출 |
| hwp | `olefile`로 BodyText section을 best-effort 추출 |

## 2. Chunk Output

검색은 문서 전체가 아니라 chunk 단위로 수행합니다.

```csv
chunk_id,document_id,source_path,page_start,page_end,section,text,token_count
rfp_sample_chunk_0001,rfp_sample,data/rag_smoke/rfp_sample.txt,1,1,사업 개요,"본 사업의 예산은 5천만 원입니다.",18
```

필수 컬럼:

- `chunk_id`: chunk 고유 id
- `document_id`: 원본 문서 id
- `source_path`: 원본 파일 경로
- `page_start`: chunk 시작 페이지
- `page_end`: chunk 끝 페이지
- `section`: 문서 구역명
- `text`: 검색과 답변 생성에 사용할 본문
- `token_count`: 대략적인 token 또는 단어 수

config 후보:

```yaml
chunk:
  size: 500
  overlap: 80
  unit: char
```

처음 smoke test에서는 `char` 기준으로 단순하게 시작해도 됩니다.
실제 RFP 문서에서는 문단/섹션 기준 chunking을 우선 검토합니다.

## 3. Embedding Output

chunk를 embedding으로 바꾼 뒤에는 vector와 metadata가 함께 관리되어야 합니다.
현재 smoke pipeline에서는 `hashing-char-ngram-v1` embedding을 사용합니다.
이 방식은 외부 모델 없이 vector retrieval 계약을 검증하기 위한 것이며, 실제 프로젝트에서는 sentence-transformers 같은 모델로 교체할 수 있습니다.

파일 예시:

```text
experiments/rag_smoke_test/
|-- chunks.csv
|-- embeddings.jsonl
`-- vector_index/
```

`embeddings.jsonl` 예시:

```json
{"chunk_id":"rfp_sample_chunk_0001","embedding_model":"sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2","vector":[0.01,0.02,0.03]}
```

필수 정보:

- `chunk_id`
- `embedding_model`
- `vector`

원칙:

- vector store가 무엇이든 chunk metadata와 다시 연결되어야 합니다.
- embedding model 이름을 남겨야 나중에 검색 결과를 비교할 수 있습니다.

## 4. Retrieval Output

질문을 넣으면 top-k chunk를 반환합니다.

```json
{
  "question": "예산이 얼마야?",
  "top_k": 3,
  "retrieved_chunks": [
    {
      "rank": 1,
      "chunk_id": "rfp_sample_chunk_0001",
      "score": 0.87,
      "document_id": "rfp_sample",
      "source_path": "data/rag_smoke/rfp_sample.txt",
      "page": 1,
      "section": "사업 개요",
      "text": "본 사업의 예산은 5천만 원입니다."
    }
  ]
}
```

필수 정보:

- `question`
- `top_k`
- `rank`
- `chunk_id`
- `score`
- `document_id`
- `source_path`
- `page`
- `section`
- `text`

검색 결과는 `retrieval_results.jsonl`로 저장합니다.

## 5. Answer Output

답변은 반드시 근거와 함께 저장합니다.

```json
{
  "question": "예산이 얼마야?",
  "answer": "이 사업의 예산은 5천만 원입니다.",
  "citations": [
    {
      "chunk_id": "rfp_sample_chunk_0001",
      "document_id": "rfp_sample",
      "source_path": "data/rag_smoke/rfp_sample.txt",
      "page": 1,
      "section": "사업 개요"
    }
  ],
  "status": "answered"
}
```

필수 정보:

- `question`
- `answer`
- `citations`
- `status`

status 후보:

```text
answered: 근거를 찾고 답변함
not_found: 관련 근거가 부족함
needs_review: 답변은 했지만 사람이 확인해야 함
error: 실행 중 오류 발생
```

중요한 원칙:

- 검색된 근거가 없거나 약하면 답을 꾸며내지 않습니다.
- 이 경우 `status: not_found`와 함께 “문서에서 확인하지 못했습니다”라고 답합니다.

## 6. Evaluation Input

RAG 평가는 label이 있는 질문 세트가 있을 때 가능합니다.

```csv
question,expected_answer,expected_chunk_ids
예산이 얼마야?,5천만 원,rfp_sample_chunk_0001
마감일은 언제야?,2026년 7월 10일,rfp_sample_chunk_0002
참가 자격은 뭐야?,최근 3년 이내 유사 사업 수행 경험,rfp_sample_chunk_0003
```

필수 컬럼:

- `question`
- `expected_answer`
- `expected_chunk_ids`

처음에는 사람이 만든 작은 평가 질문 5~10개로 시작합니다.

## 7. Evaluation Output

평가 결과는 질문별 결과와 전체 metric을 나눠 저장합니다.

질문별 결과:

```csv
question,retrieval_hit,answer_contains_expected,citation_correct,status
예산이 얼마야?,true,true,true,answered
```

전체 metric:

```json
{
  "retrieval_hit_rate": 1.0,
  "answer_contains_expected_rate": 1.0,
  "citation_correct_rate": 1.0,
  "not_found_rate": 0.0
}
```

초기 metric 후보:

- `retrieval_hit_rate`: 기대 chunk가 검색 결과 top-k 안에 있는 비율
- `answer_contains_expected_rate`: 답변에 기대 답변 문자열이 포함된 비율
- `citation_correct_rate`: citation이 기대 chunk와 맞는 비율
- `not_found_rate`: 답변하지 못한 질문 비율

LLM judge 기반 평가는 나중에 추가합니다.
초기에는 사람이 이해하기 쉬운 rule 기반 평가부터 시작합니다.

## 8. Error Analysis

분류 프로젝트의 `wrong_predictions.csv`에 대응되는 RAG 오답노트입니다.

후보 산출물:

```text
failed_questions.csv
bad_retrievals.csv
unsupported_answers.csv
```

의미:

- `failed_questions.csv`: 답변하지 못했거나 에러가 난 질문
- `bad_retrievals.csv`: 기대 chunk를 검색하지 못한 질문
- `unsupported_answers.csv`: 답변은 했지만 citation 근거가 약한 질문

RAG에서는 “답변이 그럴듯한가”보다 “문서 근거로 지지되는가”를 우선 봅니다.
현재 smoke pipeline은 평가 실행 시 위 세 파일을 자동 생성합니다.
실패가 없더라도 header만 있는 빈 CSV를 남겨, 다음 실험과 산출물 구조를 항상 같게 유지합니다.

## 9. Config 초안

```yaml
experiment:
  name: rag_smoke_test
  seed: 42

paths:
  raw_docs_dir: data/rag_smoke
  processed_docs_dir: data/processed_docs/rag_smoke
  output_dir: experiments/rag_smoke_test
  index_dir: experiments/rag_smoke_test/vector_index

rag:
  loader:
    file_types: [txt, pdf, docx, hwpx, hwp]
  chunk:
    size: 500
    overlap: 80
    unit: char
  embedding:
    provider: local
    model_name: hashing-char-ngram-v1
    dimension: 64
  retriever:
    method: semantic
    top_k: 3
    score_threshold: 0.0
  answerer:
    mode: extractive
    fallback_message: 문서에서 확인하지 못했습니다.

metric:
  monitor: retrieval_hit_rate
  mode: max
```

현재 smoke pipeline에서는 `answerer.mode: extractive`로 시작합니다.
즉 LLM 답변 생성 전에, 검색된 chunk에서 문장을 찾아 반환하는 방식으로 파이프라인을 먼저 검증합니다.

## 10. Smoke Test 목표

처음 RAG smoke test의 목표는 성능이 아닙니다.

목표:

- txt 문서를 읽을 수 있다.
- chunk를 만들 수 있다.
- embedding 산출물을 만들 수 있다.
- 질문과 관련 있는 chunk를 찾을 수 있다.
- 답변에 citation을 붙일 수 있다.
- 실험 산출물을 저장할 수 있다.
- summary에 RAG metric을 포함할 수 있다.

샘플 질문:

```text
예산이 얼마야?
마감일은 언제야?
참가 자격은 뭐야?
```

예상 답변:

```text
이 사업의 예산은 5천만 원입니다. [source: rfp_sample, page 1]
```

## 11. 구현 순서

1. `configs/rag_smoke_test.yaml` 작성
2. `data/rag_smoke/rfp_sample.txt` 작성
3. `src/rag/document_loader.py` 작성
4. `src/rag/chunker.py` 작성
5. `src/rag/embedder.py` 작성
6. `src/rag/vector_store.py` 작성
7. `src/rag/retriever.py` 작성
8. `scripts/run_rag_ingest.py` 작성
9. `scripts/run_rag_retrieve.py` 작성
10. `scripts/run_rag_chat.py` 작성
11. RAG smoke test 추가
12. 실험 summary에 RAG metric 연결

현재는 hashing embedding과 in-memory cosine retrieval까지 구현되어 있습니다.
그 다음 단계에서 sentence-transformers, FAISS/Chroma 등을 붙이면 됩니다.
