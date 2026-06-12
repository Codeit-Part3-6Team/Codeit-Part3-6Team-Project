# Example Configs

`configs/examples/`는 메인 실험이 아니라 참고용 config를 보관하는 곳입니다.

현재 프로젝트의 기본 실험은 `configs/experiments/rag/`에서 시작합니다. 이 디렉터리는 외부 모델 후보, 분류 파이프라인 예시, Colab 경로 예시처럼 당장 본 실험은 아니지만 나중에 참고할 수 있는 설정을 둡니다.

## 구성

```text
configs/examples/
|-- rag/             # RAG에서 외부 구현체를 붙일 때 참고할 config
`-- classification/  # 분류/HuggingFace fine-tuning 참고 예제
```

## RAG 참고 예제

- `rag/rag_hf_llm_answerer.yaml`: RAG answerer를 HuggingFace LLM으로 바꾸는 예시
- `rag/rag_langchain_ollama.yaml`: LangChain 기반 Ollama embedding/answerer 예시
- `rag/rag_langchain_openai.yaml`: LangChain 기반 OpenAI answerer opt-in 예시

이 예제는 RAG 프로젝트와 직접 관련이 있지만, smoke 기본값은 아닙니다. 실제 모델 다운로드와 추론 비용이 생길 수 있으므로 기본 실험이 통과한 뒤 사용합니다.

## 분류/HuggingFace 참고 예제

`classification/` 아래의 config는 예전 ML 파이프라인과 HuggingFace fine-tuning 구조를 설명하기 위한 참고 자료입니다.

RAG 프로젝트에서 HuggingFace를 쓰고 싶다면 우선 아래 RAG 옵션을 봅니다.

```yaml
rag:
  embedding:
    provider: huggingface
  reranker:
    provider: huggingface
  answerer:
    provider: huggingface
```

분류 파인튜닝 config를 RAG 실험 config처럼 사용하지 않습니다.
