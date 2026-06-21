# RAG Experiment Configs

`configs/experiments/rag/`는 실제 프로젝트에서 우선 사용하는 RAG 실험 config를 둡니다.

분류 모델이나 HuggingFace fine-tuning config는 이 폴더의 메인 흐름이 아닙니다. RAG 실험을 만들 때는 이 디렉터리의 YAML을 복사해서 시작합니다.

## 현재 Config

| config | 목적 | 먼저 바꿔볼 옵션 |
| --- | --- | --- |
| `rag_langchain.yaml` | LangChain 엔진 기반 기본 RAG 실험 | `rag.splitter`, `rag.embedding`, `rag.retriever.top_k` |
| `rag_realistic_docs.yaml` | DOCX/HWPX 준실제 RFP fixture E2E 검증 | `rag.loader.file_types`, `rag.splitter`, `rag.retriever.top_k` |
| `rag_semantic.yaml` | local semantic retriever 비교 실험 | `rag.chunk`, `rag.retriever.top_k` |
| `rag_keyword.yaml` | keyword retriever 비교 | `rag.retriever.method` |
| `rag_hybrid.yaml` | keyword + semantic hybrid 비교 | `rag.retriever.keyword_weight`, `rag.retriever.semantic_weight` |
| `rag_agent.yaml` | Agent 확장 참조 템플릿 (`agent.enabled: false` 기본) | `agent.enabled`, `agent.phases`, `agent.tools.*` |

## 실험 복사 규칙

새 실험은 기존 config를 복사하고 이름과 출력 경로를 먼저 바꿉니다.

```text
rag_langchain.yaml
-> rag_top5_chunk800.yaml
```

```yaml
experiment:
  name: rag_top5_chunk800

paths:
  output_dir: experiments/rag_top5_chunk800
```

같은 실험 이름으로 여러 조건을 반복한다면 `artifact_policy.run_id`를 사용합니다.

```yaml
artifact_policy:
  run_id: top5_run001
  on_existing: overwrite
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
| `rag.embedding` | local hashing과 LangChain embedding 후보 비교 |
| `rag.retriever` | similarity, keyword, semantic, hybrid 검색 방식 비교 |
| `rag.reranker` | 검색 결과 재정렬 후보 실험 |
| `rag.answerer` | extractive 답변과 LLM 답변 후보 비교 |
| `evaluation.questions_path` | 평가 질문 세트 교체 |
| `metric.monitor` | 대표 지표 지정 |

## 실행 순서

```bash
python scripts/check_rag_pipeline.py --config configs/experiments/rag/rag_langchain.yaml --project-root .
python scripts/run_rag_ingest.py --config configs/experiments/rag/rag_langchain.yaml --project-root .
python scripts/run_rag_retrieve.py --config configs/experiments/rag/rag_langchain.yaml --project-root . --question "예산은 얼마야?"
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_langchain.yaml --project-root . --evaluate
```

## 결과 확인

RAG 실험 결과는 `paths.output_dir` 아래에 남습니다.

```text
experiments/rag_langchain/
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
