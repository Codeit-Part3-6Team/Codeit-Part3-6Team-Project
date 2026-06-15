# 골든 데이터셋 구축 가이드

이 문서는 RAG 파이프라인의 평가 지표를 신뢰할 수 있게 만들기 위해 질문-정답-청크 쌍을 어떻게 만드는지 설명합니다.

## 왜 골든 데이터셋이 필요한가

RAG 파이프라인은 문서를 읽고 질문에 답합니다. 이 답변이 실제로 맞는지 확인하려면 "정답"이 필요합니다.
골든 데이터셋은 사람이 직접 검증한 질문-정답 쌍으로, 파이프라인이 제대로 동작하는지 측정하는 기준이 됩니다.

## 구축 순서

### 1. 문서 ingest부터 실행한다

질문을 만들기 전에 반드시 실제 RFP 문서를 ingest합니다.

```bash
python scripts/run_rag_ingest.py \
  --config configs/experiments/rag/rag_langchain.yaml \
  --project-root .
```

생성된 `chunks.csv`를 먼저 확인합니다. chunk가 어떻게 나뉘었는지 모르는 상태에서 질문을 만들면 `expected_chunk_ids`를 나중에 맞출 수 없습니다.

### 2. 질문 유형을 나눠서 만든다

한 가지 유형의 질문만 만들면 평가가 한쪽으로 치우칩니다. 아래 유형을 의식하면서 만듭니다.

| 유형 | 설명 | 예시 | 권장 비중 |
| --- | --- | --- | --- |
| 사실 확인 | 문서에 명시된 단일 정보를 묻습니다 | "제안 마감일은 언제인가?" | ~40% |
| 조건/자격 | ~해야 한다, ~이어야 한다 같은 조건을 묻습니다 | "입찰 참가 자격은 무엇인가?" | ~25% |
| 수치/예산 | 금액, 기간, 인원 등 숫자 정보를 묻습니다 | "총 예산은 얼마인가?" | ~20% |
| 비교/판단 | 두 항목의 차이나 포함 관계를 묻습니다 | "1차 평가와 2차 평가의 차이는?" | ~15% |

총 **50~100건**을 목표로 합니다. 50건이면 각 유형별로 20/13/10/7건 정도입니다.

### 3. 질문 작성 기준

**좋은 질문:**
- 문서에서 답을 찾을 수 있는 질문만 만듭니다
- 질문만 읽어도 무엇을 묻는지 알 수 있게 씁니다
- 한 질문에 여러 답변이 나오지 않게 구체적으로 씁니다

**피해야 할 질문:**
- "이 사업의 장점은?" → 문서에 안 나올 수 있음 (주관적 판단)
- "입찰에 대해 설명해줘" → 너무 넓음 (검색 범위가 애매함)
- "A사의 제안은 무엇인가?" → 문서에 없는 내용

### 4. expected_answer 작성 기준

`expected_answer`는 평가 시 `answer_contains_expected_rate`를 계산할 때 사용합니다.
파이프라인이 생성한 답변에 `expected_answer`가 포함되어 있으면 정답으로 봅니다.

**작성 요령:**
- 문서 원문에서 핵심 키워드만 뽑습니다. 전체 문장을 복사할 필요는 없습니다.
- `in` 연산자로 비교하므로 띄어쓰기에 주의합니다.
- 예시: 질문 "총 예산은 얼마인가?" → expected_answer "50억원" (O), "50억 원" (X, 띄어쓰기 차이로 불일치 가능)

### 5. expected_chunk_ids 매핑

`chunks.csv`를 열고, 정답 정보가 들어있는 chunk의 `chunk_id`를 찾아 세미콜론(`;`)으로 연결합니다.
하나의 질문에 여러 chunk에 걸쳐 정답이 흩어져 있다면 모두 적습니다.

**확인 방법:**
```python
import pandas as pd
chunks = pd.read_csv("experiments/rag_langchain/chunks.csv")
# 질문과 관련된 내용을 담은 chunk 찾기
chunks[chunks["text"].str.contains("마감일")]
```

### 6. CSV 형식

최종 산출물은 아래 열을 가진 CSV 파일입니다.

```csv
question,expected_answer,expected_chunk_ids
"제안 마감일은 언제인가?","2026년 7월 31일","rfp_sample_001_chunk_001;rfp_sample_001_chunk_002"
"입찰 참가 자격은 무엇인가?","사업자등록증","rfp_sample_001_chunk_003"
"총 예산은 얼마인가?","50억원","rfp_sample_001_chunk_002"
```

### 7. 품질 점검

CSV를 완성한 뒤 아래 항목을 확인합니다.

- [ ] 모든 질문이 문서에서 답변 가능한가? (문서 밖 질문이 없는가?)
- [ ] `expected_chunk_ids`가 실제 `chunks.csv`에 존재하는 chunk_id인가?
- [ ] 질문 유형이 한쪽으로 치우치지 않았는가?
- [ ] `expected_answer` 띄어쓰기가 원문과 일치하는가?
- [ ] CSV 파일이 UTF-8 인코딩인가?

### 8. 보관 위치

평가 질문 CSV는 다른 실험 config에서도 참조하므로 안정적인 위치에 둡니다.

```text
data/
  rag_sample/
    eval_questions.csv       # 샘플용 (참고)
  eval_questions.csv         # 실제 평가용 (Git ignored 또는 별도 공유)
```

실제 문서 기반 평가 질문은 Git에 올리지 않습니다.
Google Drive 공유 폴더에 두고 config의 `evaluation.questions_path`로 지정합니다.

## 역할별 작업 분담

| 역할 | 할 일 |
| --- | --- |
| Data Engineer | 문서 ingest, chunk 구조 파악, CSV 초안 작성 |
| Experiment Lead | chunk_ids 존재 여부 검증, 질문 유형 분포 확인 |
| PM | 질문 수/유형 목표 합의, CSV 검수 일정 조율 |

## 작업 시간 예상

- 문서가 5~10건, 100~300 chunk일 때
- 50건 작성: 2~3시간 (2인이 나눠서)
- 100건 작성: 4~5시간 (2인이 나눠서)

가장 시간이 걸리는 부분은 `expected_chunk_ids` 매핑입니다.
질문과 expected_answer를 먼저 다 만든 뒤, chunk_ids는 한 번에 매핑하는 것이 효율적입니다.
