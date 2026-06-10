# RAG Experiment Configs

`configs/experiments/rag/`는 RAG 문서 검색, 답변, 평가 실험 config를 둡니다.

- `rag_smoke_test.yaml`: semantic retriever 기반 기본 RAG 실험
- `rag_smoke_keyword.yaml`: keyword retriever 비교용
- `rag_smoke_hybrid.yaml`: keyword + semantic hybrid 비교용

주로 바꾸는 옵션은 `rag.chunk`, `rag.embedding`, `rag.retriever`, `rag.answerer`, `evaluation.questions_path`입니다.

실험을 반복할 때는 같은 config를 덮어쓰기보다 복사본을 만들고 `experiment.name` 또는 `artifact_policy.run_id`를 바꿔 결과 폴더를 분리하는 편이 안전합니다.
