# Experiment Lead — 실험 가이드

이 문서는 RAG 실험을 처음부터 끝까지 실행하는 방법을 단계별로 안내합니다.

## 준비물 확인

실험을 시작하기 전에 아래 항목들이 준비되었는지 확인합니다:

- [ ] VM에 SSH로 접속할 수 있나요? (`ssh 계정@VM_IP`)
- [ ] `/shared/data/raw_docs/` 에 실제 RFP 문서가 들어있나요? (`ls /shared/data/raw_docs/`)
- [ ] 평가용 질문 CSV가 있나요? (`cat /shared/data/eval_questions.csv`)
- [ ] `conda activate codeit-ml-pipeline` 이 되나요?

하나라도 안 되면 PM에게 문의하세요.

## 디렉터리 구조 이해하기

```
~/project/                                    ← 코드 (git repo)
├── configs/experiments/rag/*.yaml             ← 실험 조건 파일
└── notebooks/rag/rag_config_run.ipynb         ← 실험 노트북

/shared/                                       ← 공유 데이터/산출물
├── data/raw_docs/                              ← 원본 RFP 문서
├── data/eval_questions.csv                     ← 평가 질문 (DE가 만듦)
└── experiments/                                ← 실험 결과가 저장되는 곳
```

**핵심:** 실험 결과는 `/shared/experiments/` 아래에 저장됩니다. 모든 팀원이 볼 수 있어요.

## 1. 기본 실험 config 확인하기

가장 기본이 되는 config는 `rag_langchain.yaml` 입니다. 내용을 한번 보세요:

```bash
cat configs/experiments/rag/rag_langchain.yaml
```

주목할 부분:
- `paths.raw_docs_dir`: 여기 경로에 문서가 있어야 실험이 돌아갑니다
- `paths.output_dir`: 실험 결과가 저장될 위치입니다
- `rag.splitter.chunk_size`: 문서를 몇 글자 단위로 자를지 (500이면 500자)
- `rag.retriever.top_k`: 검색 결과를 몇 개 가져올지 (5면 상위 5개)

## 2. 첫 실험 돌리기 (CLI)

터미널에서 한 줄씩 실행해보세요:

```bash
# VM 접속 후
cd ~/project
conda activate codeit-ml-pipeline

# 1단계: config가 올바른지 검사
python scripts/check_rag_pipeline.py \
  --config configs/experiments/rag/rag_langchain.yaml \
  --project-root .

# 정상 출력 예시:
# {'ok': True, 'errors': [], ...}
```

```bash
# 2단계: 문서 읽기 + 청킹 + embedding
python scripts/run_rag_ingest.py \
  --config configs/experiments/rag/rag_langchain.yaml \
  --project-root .

# 정상 출력 예시:
# RAG ingest completed.
# Documents: 51
# Chunks: 1234
# Embeddings: 1234
```

```bash
# 3단계: 질문 하나로 테스트
python scripts/run_rag_chat.py \
  --config configs/experiments/rag/rag_langchain.yaml \
  --project-root . \
  --question "이 사업의 총 예산은 얼마인가요?"

# 출력에 "answer" 항목이 있으면 검색/답변 성공
```

```bash
# 4단계: 평가셋 전체 평가
python scripts/run_rag_chat.py \
  --config configs/experiments/rag/rag_langchain.yaml \
  --project-root . \
  --evaluate

# 출력 예시:
# {"retrieval_hit_rate": 0.72, "answer_contains_expected_rate": 0.58, ...}
```

## 3. 결과 확인하기

실험 결과는 `experiments/rag_langchain/` 아래에 저장됩니다:

```bash
ls experiments/rag_langchain/
```

주요 파일:

| 파일 | 내용 | 보는 방법 |
|---|---|---|
| `metrics.json` | 최종 점수 4개 | `cat experiments/rag_langchain/metrics.json` |
| `evaluation_results.csv` | 질문별 결과표 | `cat experiments/rag_langchain/evaluation_results.csv` |
| `bad_retrievals.csv` | 검색 실패 목록 | hit_rate 낮을 때 확인 |
| `answers.jsonl` | 답변+출처 | 답변이 이상할 때 확인 |

**metrics.json 설명:**
```json
{
  "retrieval_hit_rate": 0.72,           // 검색이 정답 chunk를 찾은 비율 (높을수록 좋음)
  "answer_contains_expected_rate": 0.58, // 답변에 정답이 포함된 비율 (높을수록 좋음)
  "citation_correct_rate": 0.50,         // 출처가 맞는 비율 (높을수록 좋음)
  "not_found_rate": 0.10                 // 답변 불가능 비율 (낮을수록 좋음)
}
```

## 4. 파라미터를 바꿔가며 실험하기

실험의 핵심은 config 파일에서 아래 값들을 바꿔보는 것입니다:

### 바꿀 수 있는 것들

| 파라미터 | 위치 | 기본값 | 변경 예시 |
|---|---|---|---|
| 청크 크기 | `rag.splitter.chunk_size` | 500 | 300, 500, 800 |
| 청크 겹침 | `rag.splitter.chunk_overlap` | 80 | 50, 80, 120 |
| 검색 방식 | `rag.retriever.method` | similarity | keyword, similarity, hybrid |
| 검색 개수 | `rag.retriever.top_k` | 5 | 3, 5, 7 |
| 임베딩 모델 | `rag.embedding.provider` | local | local, ollama |
| 답변 모델 | `rag.answerer.provider` | local | local, ollama, openai |
| Agent 활성화 | `agent.enabled` | false | true, false |
| Agent 최대 단계 | `agent.max_steps` | 15 | 10, 15, 30 |
| Agent Tool 목록 | `agent.tools` | config별 정의 | extract_facts, decide_participation, ... |
| Tool별 Structured Output | `tools.*.answerer.output_schema` | 없음 | facts_schema, decision_schema |
| Tool별 프롬프트 | `tools.*.answerer.prompt_template` | 기본 프롬프트 | 커스텀 템플릿 |

### 실험 config 만들기

```bash
# 1. base config를 복사해서 새 파일 만들기
cp configs/experiments/rag/rag_langchain.yaml \
   configs/experiments/rag/rag_chunk300.yaml

# 2. nano로 열어서 수정
nano configs/experiments/rag/rag_chunk300.yaml

# 3. 바꿀 부분만 수정
# chunk_size: 300
# output_dir: /shared/experiments/rag_chunk300     ← 결과가 겹치지 않게!

# 4. 저장 후 실행
python scripts/run_rag_ingest.py --config configs/experiments/rag/rag_chunk300.yaml --project-root .
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_chunk300.yaml --project-root . --evaluate

# 5. 결과 비교
cat experiments/rag_langchain/metrics.json
cat /shared/experiments/rag_chunk300/metrics.json
```

### 추천 실험 순서

처음에는 이 순서대로 하나씩 해보세요:

```bash
# 실험 1: 기본값 (chunk=500, top_k=5, local)
# 이미 위에서 했음 → baseline 결과 기록

# 실험 2: chunk 크기를 줄여보기
cp configs/experiments/rag/rag_langchain.yaml configs/experiments/rag/rag_chunk300.yaml
# nano로 열어서 chunk_size: 300, output_dir: /shared/experiments/rag_chunk300 으로 수정
python scripts/run_rag_ingest.py --config configs/experiments/rag/rag_chunk300.yaml --project-root .
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_chunk300.yaml --project-root . --evaluate

# 실험 3: 검색 개수를 늘려보기
cp configs/experiments/rag/rag_langchain.yaml configs/experiments/rag/rag_top7.yaml
# nano: top_k: 7, output_dir: /shared/experiments/rag_top7
# 실행...

# 실험 4: 검색 방식을 키워드로 바꿔보기
cp configs/experiments/rag/rag_langchain.yaml configs/experiments/rag/rag_keyword.yaml
# nano: retriever.method: keyword, output_dir: /shared/experiments/rag_keyword
# 실행...
```

## 5. 노트북으로 실험하기 (CLI 대신)

CLI가 익숙하지 않다면, 노트북으로도 실험 전체를 실행할 수 있습니다.

### 실험용 노트북: `rag_config_run.ipynb`

이 노트북 하나로 config 검증부터 ingest, 검색, 평가까지 한 번에:

```bash
# VS Code에서 IPYNB 파일 열기 (Remote-SSH로 VM에 연결된 상태)
# File > Open File > notebooks/rag/rag_config_run.ipynb
# 또는 터미널에서:
code notebooks/rag/rag_config_run.ipynb
```

**노트북 실행 방법:**

1. 맨 위 `EXP_NAME` 셀에서 실험할 config 이름을 설정합니다:
   ```python
   EXP_NAME = "rag_langchain"    # configs/experiments/rag/ 디렉터리의 yaml 이름
   ```

2. 각 섹션에 있는 `RUN_*` 플래그로 실행 여부를 조절합니다:
   ```python
   RUN_CHECK = True      # config 검증만 (첫 실행 시)
   RUN_INGEST = True     # 문서 읽기 + 청킹 + embedding
   RUN_RETRIEVE = True   # 질문 하나로 검색 테스트
   RUN_EVALUATE = True   # 평가셋 전체 실행
   ```

3. 위에서부터 순서대로 `Shift+Enter`로 셀을 실행합니다.

**각 섹션에서 볼 수 있는 것:**

| 섹션 | 내용 |
|---|---|
| Input Check | config 파일 존재 확인 + 평가 질문 미리보기 |
| Config Validation | `check_rag_pipeline` 실행 결과 |
| Ingest | 문서 개수, chunk 개수, chunk 길이 통계 |
| Retrieve Check | 질문 하나에 대해 어떤 chunk가 검색됐는지 미리보기 |
| Metrics & Failures | 4개 지표를 막대 그래프로, 실패 유형별 분석 |
| Answers & Citations | 모든 질문의 답변 + 출처 표로 확인 |

### 분석용 노트북: `rag_compare_results.ipynb`

여러 실험 결과를 비교할 때 사용합니다. **이 노트북은 실험을 다시 실행하지 않고, 이미 저장된 결과만 읽어서 분석합니다.**

```bash
code notebooks/rag/rag_compare_results.ipynb
```

**실행 후 볼 수 있는 분석:**

| 분석 | 설명 |
|---|---|
| grouped bar chart | 실험별 4개 지표를 한 번에 비교. 어느 config가 가장 좋은지 한눈에 보임 |
| config diff | 실험 간 config 차이를 표로 비교. "뭘 바꿨길래 결과가 달라졌지?"를 바로 확인 |
| answer text table | 같은 질문에 대해 각 실험이 어떤 답변을 했는지 나란히 비교 |
| hit/miss heatmap | 질문×실험 행렬. "이 질문은 모든 실험에서 틀렸네" 같은 패턴 발견 |
| failure analysis | 실패 유형(retrieval 실패 / 답변 부족 / 실행 오류)별로 집계 |

**사용 흐름:**
```
rag_config_run.ipynb 로 실험 2~3개 실행
         ↓
rag_compare_results.ipynb 열어서 비교 분석
         ↓
가장 좋은 config 찾기
         ↓
다시 rag_config_run.ipynb 로 파라미터 변경해서 반복
```

## 6. 실험 결과 비교하기 (CLI)

노트북 없이 빠르게 비교하고 싶다면:

```bash
# retriever 방식 3종 비교
python scripts/compare_rag_retrievers.py \
  --project-root . \
  --output reports/rag_retriever_comparison.csv

cat reports/rag_retriever_comparison.csv
```

## 7. Agent 모드 실행하기

RAG 파이프라인을 단일 검색/답변 대신 Agent 모드로 실행할 수 있습니다.

```bash
# Agent 모드로 단일 질문 실행
python scripts/run_rag_agent.py \
  --config configs/experiments/rag/agent/agent_lplus.yaml \
  --project-root . \
  --question "이 RFP를 요약하고 독소조항을 분석해줘"

# Agent 모드 평가
python scripts/run_rag_agent.py \
  --config configs/experiments/rag/agent/agent_lplus.yaml \
  --project-root . \
  --evaluate
```

Agent 모드는 `agent.enabled: true`일 때 활성화되며, Phase DAG에 따라 여러 Tool을
순차 실행합니다. 실행 trace는 `agent_trace.jsonl`, Tool 출력은 `tool_outputs.jsonl`,
최종 답변은 `agent_answers.jsonl`에 저장됩니다.

## 8. Ollama 모델로 업그레이드하기

기본 config는 local 모델을 써서 가볍지만 정확도가 낮습니다. Ollama를 쓰려면:

```bash
# 1. Ollama 모델 다운로드 (한 번만)
ollama pull nomic-embed-text
ollama pull gemma4:e2b

# 2. Ollama 예시 config 확인
cat configs/examples/rag/rag_langchain_ollama.yaml

# 3. 기존 config에 Ollama 설정 복사해서 새 config 만들기
cp configs/experiments/rag/rag_langchain.yaml \
   configs/experiments/rag/rag_ollama.yaml

# 4. nano로 다음 내용으로 수정:
#   embedding.provider: ollama
#   embedding.model_name: nomic-embed-text
#   answerer.provider: ollama
#   answerer.model_name: gemma4:e2b
#   output_dir: /shared/experiments/rag_ollama

# 5. 실행 (Ollama는 처음 실행 시 모델 로딩 시간이 걸림)
python scripts/run_rag_ingest.py --config configs/experiments/rag/rag_ollama.yaml --project-root .
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_ollama.yaml --project-root . --evaluate
```

## 9. 수동 실험 로그 남기기

`reports/experiment_log.csv` 파일에 실험 기록을 남기면 나중에 한눈에 비교할 수 있습니다:

```bash
nano reports/experiment_log.csv
```

```
exp_name,date,chunk_size,top_k,retriever,hit_rate,answer_rate,notes
rag_langchain,2026-06-19,500,5,similarity,0.72,0.58,기본 baseline
rag_chunk300,2026-06-19,300,5,similarity,0.78,0.62,chunk 줄이니 hit_rate 개선
rag_ollama,2026-06-19,500,5,similarity,0.82,0.75,Ollama로 업그레이드
```

## 문제가 생겼을 때

| 증상 | 확인할 것 | 해결 방법 |
|---|---|---|
| `No such file` | `raw_docs_dir` 경로가 실제로 존재하는지 | `ls /shared/data/raw_docs/` |
| 문서 0개 | config의 `file_types`에 csv/hwp 포함됐는지 | file_types에 `csv, hwp, pdf` 모두 있어야 함 |
| metrics 전부 0 | 평가질문 파일이 있는지 | `cat /shared/data/eval_questions.csv` |
| `ollama: command not found` | Ollama 설치 여부 | `ollama --version` |
| Ollama timeout | Ollama 서버 실행 중인지 | `ollama serve` (또는 PM에게 문의) |
| 결과가 이전과 같음 | checkpoint 때문에 재사용 중 | `rm -rf experiments/<name>/` 후 재실행 |
