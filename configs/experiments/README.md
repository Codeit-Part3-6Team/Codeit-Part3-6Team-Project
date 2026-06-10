# Experiment Configs

`configs/experiments/`는 실제 프로젝트 실험 후보 config를 두는 곳입니다.

현재 프로젝트 방향은 RAG이므로 기본 실험 config는 `rag/` 아래에서 관리합니다.

- `rag/rag_smoke_test.yaml`: semantic retriever 기반 기본 RAG 실험
- `rag/rag_smoke_keyword.yaml`: keyword retriever 비교 실험
- `rag/rag_smoke_hybrid.yaml`: keyword + semantic hybrid 비교 실험

새 RAG 실험을 만들 때는 기존 config를 복사한 뒤 최소한 `experiment.name`, `paths.output_dir`, `rag.retriever`, `rag.chunk`, `artifact_policy.run_id`를 확인합니다.

분류 모델이나 HuggingFace fine-tuning 예시는 RAG 프로젝트의 기본 흐름이 아니므로 `configs/examples/classification/`에 보관합니다.
