# RAG Experiment Configs

`configs/experiments/rag/`는 실제 프로젝트에서 우선 사용하는 RAG 실험 config를 둡니다.

분류 모델이나 HuggingFace fine-tuning config는 이 폴더의 메인 흐름이 아닙니다. RAG 실험을 만들 때는 이 디렉터리의 YAML을 복사해서 시작합니다.

## 현재 Config

| config | 목적 | 먼저 바꿔볼 옵션 |
| --- | --- | --- |
| `rag-baseline.yaml` | **Phase A 베이스라인** (nomic-embed-text + gpt-5-mini) | `rag.retriever.top_k`, `rag.splitter.chunk_size` |
| `rag_langchain.yaml` | LangChain 엔진 기반 기본 RAG 실험 | `rag.splitter`, `rag.embedding`, `rag.retriever.top_k` |
| `rag_realistic_docs.yaml` | DOCX/HWPX 준실제 RFP fixture E2E 검증 | `rag.loader.file_types`, `rag.splitter`, `rag.retriever.top_k` |
| `rag_semantic.yaml` | local semantic retriever 비교 실험 | `rag.chunk`, `rag.retriever.top_k` |
| `rag_keyword.yaml` | keyword retriever 비교 | `rag.retriever.method` |
| `rag_hybrid.yaml` | keyword + semantic hybrid 비교 | `rag.retriever.keyword_weight`, `rag.retriever.semantic_weight` |
| `rag_agent.yaml` | Agent 확장 참조 템플릿 (`agent.enabled: false` 기본) | `agent.enabled`, `agent.phases`, `agent.tools.*` |
| `agent/agent_lplus.yaml` | L+ 시나리오 예시 (`agent.enabled: true` + `chatbot`) | `agent.phases`, `agent.tools.*`, `chatbot.*` |
| `rag_agent_demo.yaml` | Agent + Chatbot 데모 config |
| `streamlit.yaml` | **Streamlit 서비스 전용** — agent_lplus.yaml 상속, 업로드 loader + 챗봇 활성화, `create_and_ingest()`가 paths 동적 override |

## 실험 명명 규칙

### 1. 베이스라인

첫 번째 실험은 `rag-baseline.yaml`로 복사해 시작합니다.

```yaml
experiment:
  name: rag-baseline
paths:
  output_dir: /shared/experiments/rag-baseline
```

### 2. 베이스라인 동결

베이스라인 Phase A 목표(→ `docs/md/PERFORMANCE_TARGETS.md`)를 충족하면 동결.
이후 실험은 베이스라인을 복사하고 이름에 변경 내역을 요약해 붙입니다.

### 3. 변경 실험 명명

```
rag-baseline-{변경항목1}-{변경항목2}-...
```

**예시**:

| config 파일명 | 변경 내용 |
|---|---|
| `rag-baseline-ret60-ans50.yaml` | retriever top_k 조정, answerer temperature 조정 |
| `rag-baseline-chunk800.yaml` | chunk_size 800 |
| `rag-baseline-hybrid-top10.yaml` | hybrid retriever, top_k 10 |
| `rag-baseline-openai-embed.yaml` | embedding OpenAI 교체 |

**약어**:

| 약어 | 의미 |
|------|------|
| `ret` | retriever (top_k 값 붙임) |
| `ans` | answerer (temperature 등) |
| `chunk` | chunk_size |
| `emb` | embedding 모델 변경 |
| `hyb` | hybrid retriever |
| `rr` | reranker 도입 |

### 4. 경로 규칙

```yaml
experiment:
  name: rag-baseline-chunk800           # config명과 동일
paths:
  output_dir: /shared/experiments/rag-baseline-chunk800  # 실험명과 동일
```

`experiment.name`과 `paths.output_dir`은 항상 일치시킵니다.

`evaluation.questions_path`는 VM 기준 `/shared/data/eval_questions.csv`를 기본으로 씁니다.

## /shared 경로 참조 (VM)

모든 실험 산출물과 데이터는 `/shared/` 아래에 둡니다.

| 경로 | 용도 |
|------|------|
| `/shared/data/raw_docs/` | 원본 문서 + data_list.csv |
| `/shared/data/eval_questions.csv` | 평가 질문 |
| `/shared/experiments/` | 실험 산출물 (config별 하위 디렉터리) |
| `/shared/cache/` | HuggingFace 모델 캐시 |

```yaml
artifact_policy:
  run_id: top5_run001
  on_existing: overwrite
```

## LLM-as-Judge 평가

`answer_contains_expected`(substring exact match)의 표현 차이로 인한 과소평가를 보완합니다.
LLM이 의미 기반으로 "2억원 = 200,000,000원" 같은 표현 차이를 판단합니다.

### 활성화

```yaml
evaluation:
  questions_path: /shared/data/eval_questions.csv
  llm_judge:
    enabled: true
    model_name: gpt-5-mini
```

### 산출물

`metrics.json`에 `judge_correct_rate`가 추가됩니다.
`evaluation_results.csv`에 `judge_correct` 컬럼이 추가됩니다.

### 프롬프트 커스터마이징 (선택)

```yaml
evaluation:
  llm_judge:
    enabled: true
    model_name: gpt-5-mini
    prompt: |
      expected와 actual이 의미상 같으면 true, 다르면 false. 숫자 단위 차이는 무시.
      expected: {expected}
      actual: {actual}
      결과:
```

`prompt`를 생략하면 기본 binary template을 사용합니다.

## Answerer 프롬프트 커스터마이징

`rag.answerer.prompt`로 LLM에게 전달할 프롬프트를 오버라이드할 수 있습니다.
`{context}`와 `{question}`이 자동 치환됩니다.
생략 시 아래 기본값이 사용됩니다:

```
너는 RFP 문서 분석 도우미다. 아래 근거에 있는 내용만 사용해서 한국어로 답하라.
근거에 없는 내용은 추측하지 말고 '문서에서 확인하지 못했습니다.'라고 답하라.
답변 말미에는 반드시 사용한 근거 번호를 [사용근거: 1,3] 형식으로 표기하라.

{context}

질문: {question}
```

### 커스텀 예시

```yaml
rag:
  answerer:
    prompt: |
      너는 입찰 제안서 작성 전문가다. 아래 근거를 참고해 자연스럽게 한국어로 답하라.
      {context}
      질문: {question}
```

## 실험자가 주로 만질 영역

```yaml
rag:
  engine: langchain
  splitter:
    type: recursive_character
    chunk_size: 500
    chunk_overlap: 80
  embedding:
    provider: local
    model_name: hashing-char-ngram-v1
  retriever:
    method: similarity
    top_k: 3
  answerer:
    mode: extractive
    provider: local
```

| 영역 | 바꾸는 이유 |
| --- | --- |
| `rag.splitter` 또는 `rag.chunk` | 문서 조각 크기와 문맥 유지 정도 비교 |
| `rag.loader.csv_file` | 디렉터리 내 특정 CSV만 지정 (중복 방지. 예: `data_list.csv`) |
| `rag.embedding` | local hashing과 LangChain embedding 후보 비교 |
| `rag.retriever` | similarity, keyword, semantic, hybrid 검색 방식 비교 |
| `rag.reranker` | 검색 결과 재정렬 후보 실험 |
| `rag.answerer` | extractive 답변과 LLM 답변 후보 비교 |
| `rag.answerer.prompt` | 답변 생성 프롬프트 오버라이드 (`{context}`, `{question}` 치환) |
| `evaluation.questions_path` | 평가 질문 세트 교체 |
| `metric.monitor` | 대표 지표 지정 |
| `evaluation.llm_judge` | LLM-as-Judge 의미 기반 평가 활성화 |

## 실행 순서

```bash
python scripts/check_rag_pipeline.py --config configs/experiments/rag/rag-baseline.yaml --project-root .
python scripts/run_rag_ingest.py --config configs/experiments/rag/rag-baseline.yaml --project-root .
python scripts/run_rag_retrieve.py --config configs/experiments/rag/rag-baseline.yaml --project-root . --question "예산은 얼마야?"
python scripts/run_rag_chat.py --config configs/experiments/rag/rag-baseline.yaml --project-root . --evaluate
```

## 결과 확인

RAG 실험 결과는 `paths.output_dir` 아래에 남습니다.

```text
/shared/experiments/rag_langchain/
|-- config.yaml
|-- parsed_documents.csv
|-- chunks.csv
|-- embeddings.jsonl
|-- retrieval_results.jsonl
|-- answers.jsonl
|-- metrics.json
|-- bad_retrievals.csv
|-- unsupported_answers.csv
|-- failed_questions.csv
|-- run_status.json
`-- README.md
```

## 비교할 때 보는 것

- 정답 근거 chunk가 top-k 안에 들어왔는지
- 답변이 검색된 근거를 벗어나지 않는지
- citation이 기대 chunk와 맞는지
- 실패 질문이 어떤 유형으로 몰리는지
- config 변경이 metric과 실패 사례에 어떤 영향을 줬는지

## 참고 Config

외부 모델이나 무거운 구현체 후보는 `configs/examples/rag/`에 둡니다.

- `configs/examples/rag/rag_hf_llm_answerer.yaml`: HuggingFace LLM answerer 예시
- `configs/examples/rag/rag_langchain_ollama.yaml`: Ollama embedding/answerer 기반 LangChain 예시
- `configs/examples/rag/rag_langchain_openai.yaml`: OpenAI answerer 기반 LangChain 예시

분류/HuggingFace fine-tuning 예시는 `configs/examples/classification/`에만 보관합니다.

## Agent Config 확장 구조

`rag_agent.yaml`은 기존 RAG config 위에 `agent:` 섹션을 추가해 확장한다. 핵심 설계 원칙:

### 1. `agent.enabled: false` → 기본값, 기존과 완전히 동일하게 동작

```yaml
agent:
  enabled: false   # 지금처럼 rag.* 설정으로 단일 파이프라인 실행
```

### 2. `agent.enabled: true` → Tool 기반 Phase 순차 실행

```yaml
agent:
  enabled: true
  phases:
    - name: extract
      tools: [extract_facts]
    - name: decide
      tools: [recommend]
      depends_on: [extract]
```

### 3. Tool별 retriever/answerer 오버라이드

각 Tool은 `rag.retriever`와 `rag.answerer`를 기본값으로 상속받고, 필요한 항목만 오버라이드한다:

```yaml
tools:
  extract_facts:
    description: "핵심 정보 추출"
    retriever:
      top_k: 10           # 기본값 3 → 10으로 덮어씀
    answerer:
      output_schema: facts_schema   # StructuredOutput 지시
      temperature: 0.1

  recommend:
    description: "전략 판단"
    answerer:
      provider: openai    # 이 Tool만 OpenAI 사용
      model_name: gpt-4o-mini
      output_schema: decision_schema
```

### 4. `depends_on`으로 Phase 간 선후관계 지정

```yaml
phases:
  - name: scan
    tools: [scan_clauses]
    depends_on: [extract]    # extract가 끝나야 scan 시작

  - name: decide
    tools: [recommend]
    depends_on: [extract, scan, compete]  # 셋 다 끝나야 시작
```

### 5. 붙어 있지만 사용 안 하는 Tool

`depends_on`을 빼면 다른 Phase와 독립적으로 병렬 실행할 수 있다. Phase 자체를 삭제하거나 Tool만 빼서 실험 범위를 축소할 수도 있다.

```yaml
# L 수준(비교 분석기)만 실험한다면
phases:
  - name: extract
    tools: [extract_facts]
  - name: compare
    tools: [compare_budget, compare_requirements]
    depends_on: [extract]
  - name: report
    tools: [format_comparison]
    depends_on: [compare]
```

### 6. 실험 단위: Tool 조합 → Phase 순서 → 페르소나/프롬프트

| 실험 대상 | config에서 바꾸는 곳 |
|-----------|---------------------|
| "retriever top_k 몇이 최적?" | `agent.tools.<tool>.retriever.top_k` |
| "이 Tool 조합으로도 충분한가?" | `agent.phases`에서 Tool 추가/제거 |
| "Phase 순서 바꾸면 좋아지나?" | `agent.phases` 재배열 |
| "OpenAI가 Ollama보다 판단 잘하나?" | `agent.tools.<tool>.answerer.provider` |
| "프롬프트 페르소나 변경 효과" | `agent.tools.<tool>.answerer`에 프롬프트 키 추가 (향후)
