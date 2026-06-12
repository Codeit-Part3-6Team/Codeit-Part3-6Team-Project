# RAG 기반 RFP 문서 분석 파이프라인

입찰 공고, 제안요청서(RFP), 긴 업무 문서에서 필요한 정보를 찾고, 답변과 근거 citation을 함께 남기는 RAG 프로젝트입니다.

이 저장소의 현재 목표는 거대한 앱을 바로 만드는 것이 아닙니다. 팀이 공통으로 사용할 **config 기반 RAG 실험 파이프라인**, **산출물 구조**, **문서화 규칙**을 먼저 안정적으로 준비하는 것입니다.

## 핵심 관점

이 프로젝트는 일반적인 모델 학습 프로젝트와 다르게 봅니다.

```text
일반 ML:
dataset -> train -> epoch -> checkpoint -> predict

RAG:
raw docs -> chunk -> embedding/index -> retrieve -> answer -> citation/evaluate
```

따라서 기본 RAG 실험에서 중요한 값은 `epoch`가 아니라 `chunk.size`, `retriever.method`, `top_k`, `embedding`, `reranker`, `answerer`, `evaluation.questions_path`입니다.

## 현재 구현 상태

| 영역 | 상태 |
| --- | --- |
| 문서 로딩 | `txt`, `pdf`, `docx`, `hwpx`, `hwp` |
| Chunking | 문자 기준 size/overlap config |
| Embedding | local hashing, HuggingFace mean pooling |
| Retrieval | keyword, semantic, hybrid |
| Answer | local extractive answer, HuggingFace LLM answerer 후보 |
| Evaluation | retrieval hit rate, citation correctness, 실패 질문 CSV |
| Resume | parsed/chunks/embeddings 단계별 재사용 |
| Config Validation | RAG 실행 전 config와 입력 경로 점검 |
| HTML | 킥오프, 파이프라인 설명, 모듈 구조만 유지 |

## 프로젝트 구조

```text
.
|-- configs/
|   |-- experiments/rag/   # 실제 RAG 실험 config
|   `-- examples/          # 참고용 config
|-- data/
|   `-- rag_sample/        # RAG config 실행용 샘플 문서와 평가 질문
|-- docs/
|   |-- team/              # 팀원이 처음 볼 문서
|   |-- md/                # 세부 참고 문서
|   |-- html/              # 설명용 HTML 3개만 유지
|   `-- llm/               # LLM 작업용 컨텍스트
|-- experiments/           # RAG 실험 산출물
|-- reports/               # 비교 리포트와 공유 자료
|-- scripts/               # 실행 진입점
|-- src/
|   `-- rag/               # RAG 구현체
`-- tests/
```

기존 분류/HuggingFace 학습 코드는 참고용으로 남아 있습니다. 현재 프로젝트의 기본 흐름은 `scripts/run_rag_*`와 `src/rag/`입니다.

## 빠른 시작

```bash
conda env create -f environment.yml
conda activate codeit-ml-pipeline
```

이미 Python 환경이 있다면:

```bash
pip install -r requirements.txt
```

테스트:

```bash
python -m pytest
```

## RAG 기본 실행

기본 config:

```text
configs/experiments/rag/rag_semantic.yaml
```

실행:

```bash
python scripts/check_rag_pipeline.py --config configs/experiments/rag/rag_semantic.yaml --project-root .
python scripts/run_rag_ingest.py --config configs/experiments/rag/rag_semantic.yaml --project-root .
python scripts/run_rag_retrieve.py --config configs/experiments/rag/rag_semantic.yaml --project-root . --question "예산은 얼마야?"
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_semantic.yaml --project-root . --question "예산은 얼마야?"
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_semantic.yaml --project-root . --evaluate
python scripts/compare_rag_retrievers.py --project-root .
```

## RAG 산출물

```text
experiments/rag_semantic/
|-- config.yaml
|-- parsed_documents.csv
|-- chunks.csv
|-- embeddings.jsonl
|-- retrieval_results.jsonl
|-- answers.jsonl
|-- evaluation_results.csv
|-- metrics.json
|-- bad_retrievals.csv
|-- unsupported_answers.csv
|-- failed_questions.csv
|-- run_status.json
|-- run_info.json
`-- rag_ingest_checkpoint.json
```

RAG에서는 모델 weight보다 위 산출물이 더 중요합니다. 답변이 맞는지 보려면 `answers.jsonl`만 보지 말고 `retrieval_results.jsonl`, citation, 실패 CSV를 함께 봅니다.

## 주요 Config

```yaml
rag:
  chunk:
    size: 500
    overlap: 80
  embedding:
    provider: local
    model_name: hashing-char-ngram-v1
  retriever:
    method: hybrid
    top_k: 3
  answerer:
    mode: extractive
    provider: local
  checkpoint:
    enabled: true
    resume: true
```

자세한 config 설명은 [configs/README.md](configs/README.md)를 봅니다.

## 주요 문서

| 문서 | 용도 |
| --- | --- |
| [docs/team/README.md](docs/team/README.md) | 팀원이 처음 볼 문서 입구 |
| [docs/md/rag/RAG_PIPELINE_SPEC.md](docs/md/rag/RAG_PIPELINE_SPEC.md) | RAG 입력, chunk, 검색, 답변, 평가 계약 |
| [docs/md/experiments/EXPERIMENT_GUIDE.md](docs/md/experiments/EXPERIMENT_GUIDE.md) | RAG 실험 실행과 결과 확인 |
| [docs/md/experiments/COLAB_GUIDE.md](docs/md/experiments/COLAB_GUIDE.md) | Colab/Drive RAG 실행 |
| [docs/html/overview/pipeline_explainer.html](docs/html/overview/pipeline_explainer.html) | 쉬운 파이프라인 설명 |
| [docs/html/overview/module_architecture.html](docs/html/overview/module_architecture.html) | 모듈 구조 다이어그램 |
| [docs/html/kickoff/kickoff.html](docs/html/kickoff/kickoff.html) | 킥오프 설명용 HTML |

## 운영 원칙

- RAG 실험 config는 `configs/experiments/rag/`에 둡니다.
- 분류/HuggingFace fine-tuning config는 참고 예제로만 봅니다.
- 원본 문서는 직접 수정하지 않습니다.
- 실험 결과에는 config snapshot, metric, retrieval 결과, answer, citation, 실패 사례를 남깁니다.
- HTML은 필요한 설명 자료만 유지하고, 세부 문서는 Markdown을 원본으로 관리합니다.
