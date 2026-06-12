# RAG 기반 RFP 문서 분석 파이프라인

입찰 공고, 제안요청서(RFP), 긴 업무 문서에서 필요한 정보를 찾고, 답변과 근거 citation을 함께 남기는 RAG 프로젝트입니다.

이 저장소의 목표는 완성된 앱을 바로 만드는 것이 아니라, 팀이 같은 방식으로 RAG 실험을 실행하고 결과를 비교할 수 있는 **config 기반 실험 파이프라인**을 준비하는 것입니다.

```text
raw docs -> chunk -> embedding/index -> retrieve -> answer -> citation/evaluate
```

## 이 저장소가 제공하는 것

| 영역 | 내용 |
| --- | --- |
| 실행 기준 | `configs/experiments/rag/rag_langchain.yaml` 하나로 기본 RAG 흐름 실행 |
| 엔진 | LangChain 기본 엔진, dependency-free local fallback |
| 문서 로딩 | `txt`, `pdf`, `docx`, `hwpx`, `hwp` |
| 검색 | LangChain similarity, local keyword/semantic/hybrid 비교 |
| 답변 | local extractive answer, LangChain Ollama/OpenAI answerer 후보 |
| 산출물 | retrieval, answer, citation, metric, 실패 분석 CSV |
| 문서화 | 팀 공유 문서, 세부 Markdown, 설명용 HTML, LLM 작업 컨텍스트 |

이 프로젝트는 LangChain 대체재가 아닙니다. LangChain을 계산 엔진으로 쓰더라도, 실험 조건과 산출물 형식은 이 저장소의 config와 artifact 계약으로 고정합니다.

## 빠른 시작

```bash
conda env create -f environment.yml
conda activate codeit-ml-pipeline
```

이미 Python 환경이 있다면:

```bash
pip install -r requirements.txt
```

기본 requirements는 `rag_langchain.yaml` 실행과 Ollama/OpenAI/Chroma 후보 검증을 우선합니다. HuggingFace LangChain integration은 현재 `transformers` 핀과 의존성 충돌이 날 수 있어 기본 설치에서 제외합니다.

테스트:

```bash
python -m pytest
```

## 기본 RAG 실행

실행 전 점검:

```bash
python scripts/check_rag_pipeline.py --config configs/experiments/rag/rag_langchain.yaml --project-root .
```

문서 ingest:

```bash
python scripts/run_rag_ingest.py --config configs/experiments/rag/rag_langchain.yaml --project-root .
```

질문 검색:

```bash
python scripts/run_rag_retrieve.py --config configs/experiments/rag/rag_langchain.yaml --project-root . --question "예산은 얼마야?"
```

답변 생성:

```bash
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_langchain.yaml --project-root . --question "예산은 얼마야?"
```

평가 질문 세트 실행:

```bash
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_langchain.yaml --project-root . --evaluate
```

DOCX/HWPX 준실제 문서 fixture까지 확인하려면:

```bash
python scripts/check_rag_pipeline.py --config configs/experiments/rag/rag_realistic_docs.yaml --project-root .
python scripts/run_rag_ingest.py --config configs/experiments/rag/rag_realistic_docs.yaml --project-root .
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_realistic_docs.yaml --project-root . --evaluate
```

retriever 비교:

```bash
python scripts/compare_rag_retrievers.py --project-root .
```

팀 공유 전 리허설:

```bash
python scripts/run_rag_rehearsal.py --project-root .
```

## RAG 산출물 계약

각 실험은 `experiments/{experiment.name}/` 아래에 산출물을 남깁니다.

```text
experiments/rag_langchain/
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

RAG에서는 답변만 보는 것이 아니라, 답변이 어떤 근거 chunk에서 나왔는지 함께 봅니다.

- `retrieval_results.jsonl`: 질문별 검색된 근거 chunk
- `answers.jsonl`: 답변, citation, status
- `metrics.json`: retrieval/citation/answer 지표
- `bad_retrievals.csv`: 기대 근거를 찾지 못한 질문
- `unsupported_answers.csv`: 근거가 약한 답변
- `failed_questions.csv`: 실행 실패 또는 답변 실패 질문

## 주요 Config

기본 config:

```text
configs/experiments/rag/rag_langchain.yaml
```

핵심 옵션:

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
  vector_store:
    type: memory
  retriever:
    method: similarity
    top_k: 3
  answerer:
    mode: extractive
    provider: local
  checkpoint:
    enabled: true
    resume: true
```

Ollama/OpenAI 같은 생성형 답변 후보는 `configs/examples/rag/rag_langchain_ollama.yaml`, `configs/examples/rag/rag_langchain_openai.yaml`에서 확인합니다.
해당 예시를 직접 실행할 때만 로컬 Ollama 서버나 OpenAI API를 호출하며, 기본 config와 테스트는 비용이 들지 않는 local provider를 사용합니다.
자세한 config 설명은 [configs/README.md](configs/README.md)를 봅니다.

## 프로젝트 구조

```text
.
|-- configs/
|   |-- experiments/rag/   # 실제 RAG 실험 config
|   `-- examples/          # 참고용 config
|-- data/
|   |-- rag_sample/        # RAG config 실행용 TXT 샘플 문서와 평가 질문
|   `-- rag_realistic/     # DOCX/HWPX 준실제 RFP fixture
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

## 주요 문서

| 문서 | 용도 |
| --- | --- |
| [docs/team/README.md](docs/team/README.md) | 팀원이 처음 볼 문서 입구 |
| [docs/team/rehearsal.md](docs/team/rehearsal.md) | 팀 공유 전 RAG 파이프라인 리허설 |
| [docs/md/rag/RAG_PIPELINE_SPEC.md](docs/md/rag/RAG_PIPELINE_SPEC.md) | RAG 입력, chunk, 검색, 답변, 평가 계약 |
| [docs/md/data/DATA_CONTRACT.md](docs/md/data/DATA_CONTRACT.md) | RAG 원본 문서, chunk metadata, 평가 질문 계약 |
| [docs/md/experiments/EXPERIMENT_GUIDE.md](docs/md/experiments/EXPERIMENT_GUIDE.md) | RAG 실험 실행과 결과 확인 |
| [docs/md/overview/RAG_QUALITY_CHECKLIST.md](docs/md/overview/RAG_QUALITY_CHECKLIST.md) | 품질 검증 체크리스트 |
| [docs/html/overview/pipeline_explainer.html](docs/html/overview/pipeline_explainer.html) | 쉬운 파이프라인 설명 |
| [docs/html/overview/module_architecture.html](docs/html/overview/module_architecture.html) | 모듈 구조 다이어그램 |

## 참고: 기존 ML/HuggingFace 예제

이 저장소에는 초기 파이프라인 검증을 위해 만든 분류/HuggingFace fine-tuning 코드와 config가 참고용으로 남아 있습니다.

```text
configs/examples/classification/
configs/smoke/
src/models/
scripts/run_train.py
scripts/run_predict.py
```

새 RAG 작업을 시작할 때는 위 경로가 아니라 아래 경로를 먼저 봅니다.

```text
configs/experiments/rag/
scripts/run_rag_*.py
src/rag/
docs/md/rag/RAG_PIPELINE_SPEC.md
```

## 운영 원칙

- RAG 실험 config는 `configs/experiments/rag/`에 둡니다.
- 실험 결과에는 config snapshot, metric, retrieval 결과, answer, citation, 실패 사례를 남깁니다.
- LangChain 객체는 엔진 내부에서 프로젝트 표준 dict로 변환합니다.
- 원본 문서는 직접 수정하지 않습니다.
- 대용량 모델 weight, checkpoint, 원본 데이터, 임시 산출물은 Git에 올리지 않습니다.
- HTML은 필요한 설명 자료만 유지하고, 세부 문서는 Markdown을 원본으로 관리합니다.
