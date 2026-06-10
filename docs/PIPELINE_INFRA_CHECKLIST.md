# 파이프라인 인프라 체크리스트

이 문서는 현재 프로젝트 파이프라인에 어떤 운영 기능이 있고, 무엇이 아직 없는지 점검하기 위한 기준표입니다.
목적은 기능을 무작정 늘리는 것이 아니라, 실제 프로젝트 시작 전에 깨지기 쉬운 지점을 먼저 확인하는 것입니다.

## 한 줄 요약

현재 파이프라인은 **실험을 config로 실행하고 산출물을 남기는 기본 구조, RAG용 validation/failure artifact, HuggingFace 학습 제어(checkpoint/resume/early stopping/scheduler)까지 갖춘 상태입니다.** 남은 보강은 step 단위 checkpoint, RAG 산출물 백업, 실제 검색 인프라 연결처럼 프로젝트 주제가 확정된 뒤 붙여도 되는 영역입니다.

## 현재 갖춘 것

| 항목 | 상태 | 근거 |
|---|---|---|
| config 기반 실행 | 있음 | `configs/*.yaml`, `scripts/run_*.py` |
| 프로젝트 루트 기준 경로 처리 | RAG는 있음 | RAG config path와 내부 경로를 `project_root` 기준으로 처리 |
| 데이터 검증 | 있음 | `scripts/run_validate.py`, `src/validate_data.py` |
| 이미지/text smoke test | 있음 | `configs/smoke_test.yaml`, `configs/smoke_test_text.yaml` |
| HuggingFace smoke test | 있음 | `configs/smoke_test_hf_tiny.yaml` |
| RAG smoke test | 있음 | `configs/rag_smoke_test.yaml`, `scripts/run_rag_*.py` |
| 다중 문서 loader | 있음 | txt/pdf/docx/hwpx/hwp 대상 loader |
| RAG embedding 산출물 | 있음 | `embeddings.jsonl` |
| RAG 검색 비교 | 있음 | `scripts/compare_rag_retrievers.py` |
| RAG 평가 metric | 있음 | `retrieval_hit_rate`, `citation_correct_rate` 등 |
| RAG 오답 분석 | 있음 | `bad_retrievals.csv`, `unsupported_answers.csv`, `failed_questions.csv` |
| RAG config validation | 있음 | `scripts/check_rag_pipeline.py` |
| RAG dry-run/check 명령 | 있음 | 산출물 생성 전 경로/설정/문서 수 점검 |
| RAG 실전 config 계약 | 있음 | embedding/vector_store/reranker/answerer provider validation |
| RAG adapter registry | 있음 | local/HF embedding, memory vector store, keyword/semantic/hybrid retriever, extractive answerer 분류 |
| RAG ingest checkpoint/resume | 있음 | parsed_documents/chunks/embeddings 단계별 artifact 재사용 |
| RAG failure artifact | 있음 | `run_status.json`, 실패 시 `failure.log` |
| artifact run_id | 있음 | `artifact_policy.run_id`로 실험 하위 run 폴더 분리 |
| overwrite 방지 | 있음 | `artifact_policy.on_existing: fail` |
| 실험 산출물 저장 | 있음 | `experiments/{experiment.name}/` |
| 실험 요약 리포트 | 있음 | `scripts/summarize_experiments.py` |
| Colab/Drive 실행 가이드 | 있음 | `docs/COLAB_GUIDE.md` |
| 기본 테스트 | 있음 | `pytest` 기반 smoke/unit tests |

## 일부만 갖춘 것

| 항목 | 현재 상태 | 보강 방향 |
|---|---|---|
| 백업 | `on_finish` 중심 | 중간 백업, 실패 시 백업, RAG 산출물 백업 정책 추가 |
| best model 저장 | 분류/HF 중심 | RAG에서는 best retriever/index 기준을 별도 정의 |
| 로그 | RAG/train/predict 실패 artifact는 있음 | 기타 스크립트에도 같은 패턴 적용 |
| metric | accuracy/RAG 기본 metric 중심 | macro f1, confusion matrix, retrieval@k, answer faithfulness 후보 추가 |
| 문서 loader 품질 | 입구는 있음 | 실제 PDF/HWP/HWPX 샘플 기반 보정 필요 |
| HuggingFace trainer 기능 | 있음 | early stopping, scheduler, checkpoint save/resume config 반영 |

## 아직 없는 것

| 항목 | 의미 | 우선순위 |
|---|---|---|
| step checkpoint | step 단위 checkpoint 저장 | 낮음 |
| RAG fine-grained resume | 문서/배치 중간 지점부터 이어서 실행 | 낮음 |
| Elasticsearch | 키워드/하이브리드 검색 엔진 구현 | 낮음 |
| FAISS/Chroma | 실제 vector index 저장/로드 구현 | 중간 |
| LLM answerer | 검색 근거 기반 생성형 답변 구현 | 중간 |
| 실제 샘플 문서 E2E | 실제 RFP PDF/HWPX/HWP로 전체 흐름 검증 | 높음 |

## 다음 보강 순서 추천

1. **RAG check 명령을 실제 샘플 문서에 적용**
   예시:

   ```bash
   python scripts/check_rag_pipeline.py --config configs/rag_smoke_test.yaml --project-root .
   ```

   실제 산출물을 만들기 전에 어떤 문서를 읽고, 어떤 output dir을 쓰고, 어떤 retriever를 사용할지 점검합니다.

2. **실제 샘플 문서 E2E**
   실제 RFP 문서 하나를 기준으로 loader, chunk, retrieval, answer, evaluation 산출물 품질을 확인합니다.

3. **RAG/검색 인프라 선택**
   FAISS, Chroma, Elasticsearch 중 실제 프로젝트 범위에 맞는 검색 저장소를 선택하고 config 계약을 확장합니다.

## 판단 기준

새 기능을 추가할 때는 아래 질문을 먼저 확인합니다.

- 팀원이 실행 전에 실수를 발견할 수 있는가?
- 실패했을 때 원인을 파일로 확인할 수 있는가?
- 실험을 다시 실행하거나 비교할 수 있는가?
- 산출물이 발표/보고에 바로 쓸 수 있는가?
- 실제 프로젝트 데이터가 들어와도 같은 계약을 유지하는가?

이 질문에 직접 답하는 기능부터 우선 보강합니다.
## 백업 정책 현재 상태

- 학습 성공 후 백업: `backup.enabled: true`와 `backup.on_finish: true`로 제어합니다.
- 학습 실패 후 백업: `backup.on_failure: true`로 `failure.log`, `run_status.json` 같은 원인 분석 파일을 남깁니다.
- 로그 포함 여부: `backup.include_logs`로 `*.log` 백업 여부를 조정합니다.
- 체크포인트 포함 여부: `backup.include_checkpoints`로 `hf_model/`, `checkpoints/`, `*.pt`, `*.ckpt` 같은 큰 모델 산출물 백업 여부를 조정합니다.
- HF 학습 제어: `checkpoint`, `early_stopping`, `scheduler` config가 HuggingFace 학습 루프에 반영됩니다.
- 아직 남은 영역: step 단위 checkpoint, RAG 산출물 백업 정책, RAG index resume은 별도 보강 대상입니다.
