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
