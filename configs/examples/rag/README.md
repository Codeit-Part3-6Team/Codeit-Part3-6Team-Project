# RAG 예제 config

기본 실행 config가 아니라, 프로젝트에서 특정 기능을 켜고 싶을 때 참고할 config를 둡니다.
Agent/Chatbot 설정은 `configs/experiments/rag/agent/`를 참고하세요.

- `rag_hf_llm_answerer.yaml`: HuggingFace `transformers.pipeline` 기반 LLM answerer 예시
- `rag_langchain_ollama.yaml`: LangChain splitter/embedding/retriever/answerer 기반 Ollama 실행 예시
- `rag_langchain_openai.yaml`: LangChain retriever와 OpenAI answerer를 연결하는 opt-in 예시

주의: HuggingFace LLM answerer는 실제 실행 시 모델 다운로드와 추론 시간이 필요합니다. 빠른 파이프라인 검증은 `configs/experiments/rag/rag_langchain.yaml`처럼 local embedding/local answerer를 쓰는 config를 먼저 사용합니다.

Ollama/OpenAI 예시는 직접 해당 config를 선택해 `run_rag_chat.py --evaluate` 또는 질문 실행을 할 때만 외부 모델을 호출합니다. 기본 RAG config와 테스트는 local provider를 사용하므로 비용이 발생하지 않습니다.
