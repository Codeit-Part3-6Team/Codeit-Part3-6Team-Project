# RAG Configs

`configs/rag/`는 RAG 문서 검색/답변 실험 config를 둡니다.

- `rag_smoke_test.yaml`: semantic retriever 기반 기본 RAG smoke test
- `rag_smoke_keyword.yaml`: keyword retriever 비교용
- `rag_smoke_hybrid.yaml`: keyword + semantic hybrid 비교용

주로 바꾸는 옵션은 `rag.chunk`, `rag.embedding`, `rag.retriever`, `rag.answerer`, `evaluation.questions_path`입니다.
