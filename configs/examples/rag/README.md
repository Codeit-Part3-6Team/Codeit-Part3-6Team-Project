# RAG 예제 config

기본 실행 config가 아니라, 프로젝트에서 특정 기능을 켜고 싶을 때 참고할 config를 둡니다.

- `rag_hf_llm_answerer.yaml`: HuggingFace `transformers.pipeline` 기반 LLM answerer 예시

주의: HuggingFace LLM answerer는 실제 실행 시 모델 다운로드와 추론 시간이 필요합니다. 빠른 파이프라인 검증은 `configs/experiments/rag/`의 local extractive config를 먼저 사용합니다.
