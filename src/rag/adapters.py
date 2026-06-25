from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from src.rag.answerer import build_answer
from src.rag.embedder import DEFAULT_EMBEDDING_MODEL, embed_chunks
from src.rag.embedder import embed_text as local_embed_text
from src.rag.retriever import retrieve_chunks
from src.rag.scoring import score as _score, tokenize as _tokenize


class RagEmbeddingAdapter(Protocol):
    """chunk 목록을 embedding artifact row로 변환하는 adapter 계약입니다."""

    def embed_chunks(self, chunks: list[dict[str, str]]) -> list[dict[str, Any]]:
        ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...


class RagRetrieverAdapter(Protocol):
    """질문과 저장된 산출물로 top-k chunk를 반환하는 adapter 계약입니다."""

    def retrieve(
        self,
        question: str,
        chunks: list[dict[str, str]],
        embeddings: list[dict[str, Any]],
    ) -> list[dict[str, str | float | int]]:
        ...


class RagAnswererAdapter(Protocol):
    """검색 결과를 답변/citation payload로 바꾸는 adapter 계약입니다."""

    def answer(self, question: str, retrieved_chunks: list[dict[str, Any]]) -> dict[str, Any]:
        ...


@dataclass
class LocalHashingEmbeddingAdapter:
    """현재 smoke pipeline에서 실제 동작하는 local hashing embedding 구현체입니다."""

    dimension: int = 64
    model_name: str = DEFAULT_EMBEDDING_MODEL

    def embed_chunks(self, chunks: list[dict[str, str]]) -> list[dict[str, Any]]:
        return embed_chunks(chunks, dimension=self.dimension, model_name=self.model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [local_embed_text(text, dimension=self.dimension) for text in texts]


@dataclass
class HuggingFaceEmbeddingAdapter:
    """transformers AutoModel로 mean pooling embedding을 생성하는 구현체입니다."""

    model_name: str
    device: str = "auto"
    normalize: bool = True

    def embed_chunks(self, chunks: list[dict[str, str]]) -> list[dict[str, Any]]:
        vectors = self.embed_texts([chunk["text"] for chunk in chunks])
        return [
            {
                "chunk_id": chunk["chunk_id"],
                "embedding_model": self.model_name,
                "vector": vector,
            }
            for chunk, vector in zip(chunks, vectors)
        ]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """문장 목록을 HuggingFace embedding vector로 변환합니다."""
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as exc:
            raise ImportError(
                "HuggingFace embedding을 사용하려면 transformers와 torch가 필요합니다. "
                "`pip install -r requirements.txt`를 먼저 실행하세요."
            ) from exc

        device = self._resolve_device(torch)
        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModel.from_pretrained(self.model_name).to(device)
        model.eval()
        encoded = tokenizer(texts, padding=True, truncation=True, return_tensors="pt")
        encoded = {key: value.to(device) for key, value in encoded.items()}
        with torch.no_grad():
            outputs = model(**encoded)
            pooled = _mean_pool(outputs.last_hidden_state, encoded["attention_mask"], torch)
            if self.normalize:
                pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
        return pooled.detach().cpu().tolist()

    def _resolve_device(self, torch: Any) -> Any:
        if self.device == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return torch.device(self.device)


@dataclass
class KeywordRetrieverAdapter:
    """token overlap 기반 keyword retriever 구현체입니다."""

    top_k: int = 3
    score_threshold: float = 0.0
    scoring_kwargs: dict[str, Any] = field(default_factory=dict)

    def retrieve(
        self,
        question: str,
        chunks: list[dict[str, str]],
        embeddings: list[dict[str, Any]],
    ) -> list[dict[str, str | float | int]]:
        return retrieve_chunks(
            question, chunks,
            top_k=self.top_k,
            score_threshold=self.score_threshold,
            scoring_kwargs=self.scoring_kwargs or None,
        )


@dataclass
class MemorySemanticRetrieverAdapter:
    """JSONL embedding을 메모리에 올려 cosine 기반으로 검색하는 구현체입니다."""

    top_k: int = 3
    score_threshold: float = 0.0
    embedding_adapter: RagEmbeddingAdapter | None = None

    def retrieve(
        self,
        question: str,
        chunks: list[dict[str, str]],
        embeddings: list[dict[str, Any]],
    ) -> list[dict[str, str | float | int]]:
        if self.embedding_adapter is None:
            raise ValueError("MemorySemanticRetrieverAdapter requires an embedding_adapter")
        query_vector = self.embedding_adapter.embed_texts([question])[0]
        return _retrieve_by_query_vector(
            question,
            chunks,
            embeddings,
            top_k=self.top_k,
            score_threshold=self.score_threshold,
            query_vector=query_vector,
        )


@dataclass
class HybridRetrieverAdapter:
    """keyword 점수와 vector 점수를 합쳐 검색하는 local hybrid retriever 구현체입니다."""

    top_k: int = 3
    score_threshold: float = 0.0
    embedding_adapter: RagEmbeddingAdapter | None = None
    keyword_weight: float = 0.4
    semantic_weight: float = 0.6

    def retrieve(
        self,
        question: str,
        chunks: list[dict[str, str]],
        embeddings: list[dict[str, Any]],
    ) -> list[dict[str, str | float | int]]:
        if self.embedding_adapter is None:
            raise ValueError("HybridRetrieverAdapter requires an embedding_adapter")
        keyword_rows = retrieve_chunks(question, chunks, top_k=len(chunks), score_threshold=0.0)
        semantic_rows = _retrieve_by_query_vector(
            question,
            chunks,
            embeddings,
            top_k=len(chunks),
            score_threshold=0.0,
            query_vector=self.embedding_adapter.embed_texts([question])[0],
        )
        merged = _merge_retrieval_scores(
            keyword_rows,
            semantic_rows,
            keyword_weight=self.keyword_weight,
            semantic_weight=self.semantic_weight,
        )
        filtered = [row for row in merged if float(row["score"]) > self.score_threshold]
        return [_with_rank(row, rank) for rank, row in enumerate(filtered[: self.top_k], start=1)]


@dataclass
class ExtractiveAnswererAdapter:
    """검색된 chunk에서 답변 문장을 뽑아 citation과 함께 반환하는 구현체입니다."""

    fallback_message: str

    def answer(self, question: str, retrieved_chunks: list[dict[str, Any]]) -> dict[str, Any]:
        return build_answer(question, retrieved_chunks, fallback_message=self.fallback_message)


@dataclass
class HuggingFaceLLMAnswererAdapter:
    """HuggingFace transformers pipeline으로 근거 기반 답변을 생성합니다."""

    model_name: str
    task: str = "text-generation"
    device: str = "auto"
    temperature: float = 0.2
    max_new_tokens: int = 256
    require_citations: bool = True
    fallback_message: str = "문서에서 확인하지 못했습니다."
    _pipeline: Any = field(default=None, init=False, repr=False)

    def answer(self, question: str, retrieved_chunks: list[dict[str, Any]]) -> dict[str, Any]:
        """검색된 chunk를 프롬프트 근거로 묶어 LLM 답변과 citation을 반환합니다."""
        if not retrieved_chunks:
            return {
                "question": question,
                "answer": self.fallback_message,
                "citations": [],
                "status": "not_found",
            }

        prompt = _build_rag_prompt(question, retrieved_chunks)
        generation_kwargs: dict[str, Any] = {
            "max_new_tokens": self.max_new_tokens,
            "do_sample": self.temperature > 0,
            "return_full_text": False,
        }
        if self.temperature > 0:
            generation_kwargs["temperature"] = self.temperature
        generated = self._get_pipeline()(prompt, **generation_kwargs)
        answer_text = _extract_generated_text(generated, prompt).strip() or self.fallback_message
        citations = _citations_from_chunks(retrieved_chunks) if self.require_citations else []
        return {
            "question": question,
            "answer": answer_text,
            "citations": citations,
            "status": "answered" if answer_text != self.fallback_message else "not_found",
        }

    def _get_pipeline(self) -> Any:
        if self._pipeline is None:
            try:
                from transformers import pipeline
            except ImportError as exc:
                raise ImportError(
                    "HuggingFace LLM answerer를 사용하려면 transformers가 필요합니다. "
                    "`pip install -r requirements.txt`를 먼저 실행하세요."
                ) from exc
            self._pipeline = pipeline(
                self.task,
                model=self.model_name,
                tokenizer=self.model_name,
                device=_resolve_hf_pipeline_device(self.device),
            )
        return self._pipeline


@dataclass
class OpenAIChatAnswererAdapter:
    """LangChain ChatOpenAI 기반 답변 생성 adapter입니다.

    config에서 rag.answerer.prompt로 프롬프트 템플릿을 오버라이드할 수 있습니다.
    output_schema가 주어지면 with_structured_output()을 통해 Structured Output으로 응답받습니다.
    """

    model_name: str
    temperature: float = 0.2
    max_tokens: int | None = None
    api_key_env: str = "OPENAI_API_KEY"
    prompt_template: str | None = None
    output_schema: Any = None  # Pydantic model (schema_parser로 생성)
    fallback_message: str = "문서에서 확인하지 못했습니다."
    _model: Any = field(default=None, init=False, repr=False)

    def answer(self, question: str, retrieved_chunks: list[dict[str, Any]]) -> dict[str, Any]:
        if not retrieved_chunks:
            return {
                "question": question,
                "answer": self.fallback_message,
                "citations": [],
                "status": "not_found",
            }

        prompt = _build_answer_prompt(question, retrieved_chunks, self.prompt_template)
        model = self._get_model()
        if self.output_schema is not None:
            response = model.with_structured_output(self.output_schema).invoke(prompt)
            if isinstance(response, dict):
                answer_text = "\n".join(f"{k}: {v}" for k, v in response.items())
            else:
                answer_text = str(response)
        else:
            response = model.invoke(prompt)
            answer_text = getattr(response, "content", str(response)).strip()
        if not answer_text:
            answer_text = self.fallback_message

        used_chunk_ids = _parse_used_chunks(answer_text)
        is_fallback = "확인하지 못했습니다" in answer_text or "찾을 수 없습니다" in answer_text

        return {
            "question": question,
            "answer": answer_text,
            "citations": _citations_from_chunks(retrieved_chunks, used_chunk_ids),
            "status": "not_found" if is_fallback else "answered",
        }

    def _get_model(self) -> Any:
        if self._model is None:
            import os

            try:
                from langchain_openai import ChatOpenAI
            except ImportError as exc:
                raise ImportError(
                    "OpenAI answerer를 사용하려면 langchain-openai가 필요합니다. "
                    "`pip install langchain-openai`를 먼저 실행하세요."
                ) from exc
            kwargs: dict[str, Any] = {"model": self.model_name, "temperature": self.temperature}
            if self.max_tokens:
                kwargs["max_tokens"] = self.max_tokens
            api_key = os.environ.get(self.api_key_env)
            if api_key:
                kwargs["api_key"] = api_key
            self._model = ChatOpenAI(**kwargs)
        return self._model


@dataclass
class OllamaChatAnswererAdapter:
    """LangChain ChatOllama 기반 답변 생성 adapter입니다.

    OpenAI adapter와 동일한 인터페이스로, provider만 ollama로 교체합니다.
    """

    model_name: str
    temperature: float = 0.2
    max_tokens: int | None = None
    base_url: str | None = None
    prompt_template: str | None = None
    output_schema: Any = None
    fallback_message: str = "문서에서 확인하지 못했습니다."
    _model: Any = field(default=None, init=False, repr=False)

    def answer(self, question: str, retrieved_chunks: list[dict[str, Any]]) -> dict[str, Any]:
        if not retrieved_chunks:
            return {
                "question": question,
                "answer": self.fallback_message,
                "citations": [],
                "status": "not_found",
            }

        prompt = _build_answer_prompt(question, retrieved_chunks, self.prompt_template)
        model = self._get_model()
        if self.output_schema is not None:
            response = model.with_structured_output(self.output_schema).invoke(prompt)
            if isinstance(response, dict):
                answer_text = "\n".join(f"{k}: {v}" for k, v in response.items())
            else:
                answer_text = str(response)
        else:
            response = model.invoke(prompt)
            answer_text = getattr(response, "content", str(response)).strip()
        if not answer_text:
            answer_text = self.fallback_message

        used_chunk_ids = _parse_used_chunks(answer_text)
        is_fallback = "확인하지 못했습니다" in answer_text or "찾을 수 없습니다" in answer_text

        return {
            "question": question,
            "answer": answer_text,
            "citations": _citations_from_chunks(retrieved_chunks, used_chunk_ids),
            "status": "not_found" if is_fallback else "answered",
        }

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                from langchain_ollama import ChatOllama
            except ImportError as exc:
                raise ImportError(
                    "Ollama answerer를 사용하려면 langchain-ollama가 필요합니다. "
                    "`pip install langchain-ollama`를 먼저 실행하세요."
                ) from exc
            kwargs: dict[str, Any] = {"model": self.model_name, "temperature": self.temperature}
            if self.max_tokens:
                kwargs["num_predict"] = self.max_tokens
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._model = ChatOllama(**kwargs)
        return self._model


def build_embedding_adapter(config: dict[str, Any]) -> RagEmbeddingAdapter:
    """rag.embedding config에 맞는 embedding adapter를 반환합니다."""
    provider = config.get("provider", "local")
    # 외부 embedding provider를 붙일 때도 이 factory만 확장하면 pipeline 호출부는 그대로 유지됩니다.
    if provider == "local":
        return LocalHashingEmbeddingAdapter(
            dimension=int(config.get("dimension", 64)),
            model_name=config.get("model_name", DEFAULT_EMBEDDING_MODEL),
        )
    if provider == "huggingface":
        return HuggingFaceEmbeddingAdapter(
            model_name=str(config["model_name"]),
            device=str(config.get("device", "auto")),
            normalize=bool(config.get("normalize", True)),
        )
    raise NotImplementedError(f"RAG embedding provider is not implemented yet: {provider}")


def build_retriever_adapter(config: dict[str, Any], embedding_config: dict[str, Any]) -> RagRetrieverAdapter:
    """rag.retriever config에 맞는 retriever adapter를 반환합니다."""
    method = config.get("method", "keyword")
    top_k = int(config.get("top_k", 3))
    score_threshold = float(config.get("score_threshold", 0.0))
    # semantic/hybrid 검색은 질문도 같은 embedding adapter로 벡터화해야 검색 기준이 맞습니다.
    embedding_adapter = build_embedding_adapter(embedding_config)
    if method == "keyword":
        return KeywordRetrieverAdapter(
            top_k=top_k,
            score_threshold=score_threshold,
            scoring_kwargs=_build_scoring_kwargs_from_config(config),
        )
    if method in {"semantic", "similarity"}:
        return MemorySemanticRetrieverAdapter(
            top_k=top_k,
            score_threshold=score_threshold,
            embedding_adapter=embedding_adapter,
        )
    if method in {"hybrid", "mmr"}:
        return HybridRetrieverAdapter(
            top_k=top_k,
            score_threshold=score_threshold,
            embedding_adapter=embedding_adapter,
            keyword_weight=float(config.get("keyword_weight", 0.4)),
            semantic_weight=float(config.get("semantic_weight", 0.6)),
        )
    raise NotImplementedError(f"RAG retriever method is not implemented yet: {method}")


def build_answerer_adapter(config: dict[str, Any]) -> RagAnswererAdapter:
    """rag.answerer config에 맞는 answerer adapter를 반환합니다."""
    mode = config.get("mode", "extractive")
    provider = config.get("provider", "local")
    fallback_msg = str(config.get("fallback_message", "문서에서 확인하지 못했습니다."))
    if mode == "extractive" and provider == "local":
        return ExtractiveAnswererAdapter(fallback_message=fallback_msg)
    if mode == "llm" and provider == "huggingface":
        return HuggingFaceLLMAnswererAdapter(
            model_name=str(config["model_name"]),
            task=str(config.get("task", "text-generation")),
            device=str(config.get("device", "auto")),
            temperature=float(config.get("temperature", 0.2)),
            max_new_tokens=int(config.get("max_new_tokens", config.get("max_tokens", 256))),
            require_citations=bool(config.get("require_citations", True)),
            fallback_message=fallback_msg,
        )
    if provider in {"openai", "ollama"} and mode in {"llm", "generative", ""}:
        model_name = str(config.get("model_name", "") or "")
        temperature = float(config.get("temperature", 0.2))
        max_tokens = int(config["max_tokens"]) if config.get("max_tokens") else None
        prompt_template = config.get("prompt") or config.get("prompt_template") or None
        if provider == "openai":
            return OpenAIChatAnswererAdapter(
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                prompt_template=prompt_template,
                fallback_message=fallback_msg,
                api_key_env=str(config.get("api_key_env", "OPENAI_API_KEY") or "OPENAI_API_KEY"),
            )
        if provider == "ollama":
            return OllamaChatAnswererAdapter(
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                prompt_template=prompt_template,
                fallback_message=fallback_msg,
                base_url=config.get("base_url") or None,
            )
    raise NotImplementedError(f"RAG answerer is not implemented yet: mode={mode}, provider={provider}")


def describe_rag_implementations() -> dict[str, list[dict[str, str]]]:
    """현재 RAG 엔진과 local adapter 기준으로 구현/확장 후보 옵션을 분류합니다."""
    return {
        "implemented": [
            {"type": "engine", "key": "langchain", "description": "LangChain-based RAG engine"},
            {"type": "engine", "key": "local", "description": "dependency-free smoke/fallback engine"},
            {"type": "embedding", "key": "local", "description": "hashing-char-ngram smoke embedding"},
            {"type": "embedding", "key": "huggingface", "description": "transformers mean-pooling embedding"},
            {"type": "embedding", "key": "ollama", "description": "LangChain OllamaEmbeddings"},
            {"type": "embedding", "key": "openai", "description": "validated LangChain embedding provider"},
            {"type": "vector_store", "key": "memory", "description": "embeddings.jsonl in-memory retrieval"},
            {"type": "vector_store", "key": "chroma", "description": "LangChain Chroma vector store"},
            {"type": "retriever", "key": "similarity", "description": "LangChain/vector similarity search"},
            {"type": "retriever", "key": "keyword", "description": "token overlap keyword search"},
            {"type": "retriever", "key": "semantic", "description": "local hashing vector semantic search"},
            {"type": "retriever", "key": "hybrid", "description": "weighted keyword + semantic search"},
            {"type": "answerer", "key": "extractive/local", "description": "chunk sentence extraction"},
            {"type": "answerer", "key": "llm/huggingface", "description": "transformers generation pipeline"},
            {"type": "answerer", "key": "llm/openai", "description": "LangChain ChatOpenAI answerer"},
            {"type": "answerer", "key": "llm/ollama", "description": "LangChain ChatOllama answerer"},
        ],
        "contract_only": [
            {"type": "vector_store", "key": "faiss", "description": "validated config contract only"},
            {"type": "vector_store", "key": "elasticsearch", "description": "validated config contract only"},
            {"type": "reranker", "key": "enabled", "description": "validated config contract only"},
        ],
    }


def resolve_vector_store_artifact_path(output_dir: str | Path, vector_store_config: dict[str, Any]) -> Path:
    """현재 memory vector store가 사용하는 embedding artifact 경로를 반환합니다."""
    store_type = vector_store_config.get("type", "memory")
    if store_type != "memory":
        raise NotImplementedError(f"RAG vector_store type is not implemented yet: {store_type}")
    return Path(output_dir) / "embeddings.jsonl"


def _mean_pool(last_hidden_state: Any, attention_mask: Any, torch: Any) -> Any:
    """padding token을 제외하고 token embedding 평균을 계산합니다."""
    mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    summed = torch.sum(last_hidden_state * mask, dim=1)
    counts = torch.clamp(mask.sum(dim=1), min=1e-9)
    return summed / counts


def _retrieve_by_query_vector(
    question: str,
    chunks: list[dict[str, str]],
    embeddings: list[dict[str, Any]],
    *,
    top_k: int,
    score_threshold: float,
    query_vector: list[float],
) -> list[dict[str, str | float | int]]:
    chunk_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    scored: list[tuple[float, dict[str, str]]] = []
    query_tokens = _tokenize(question)
    for row in embeddings:
        chunk = chunk_by_id.get(str(row["chunk_id"]))
        if not chunk:
            continue
        score = _dot(query_vector, row["vector"]) + (_score(query_tokens, question, chunk["text"]) * 0.5)
        if score > score_threshold:
            scored.append((score, chunk))
    scored.sort(key=lambda item: (-item[0], item[1]["chunk_id"]))
    return [_to_retrieval_row(rank, score, chunk) for rank, (score, chunk) in enumerate(scored[:top_k], start=1)]


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _to_retrieval_row(rank: int, score: float, chunk: dict[str, str]) -> dict[str, str | float | int]:
    return {
        "rank": rank,
        "score": round(score, 4),
        "chunk_id": chunk["chunk_id"],
        "document_id": chunk["document_id"],
        "source_path": chunk["source_path"],
        "page": chunk["page_start"],
        "section": chunk["section"],
        "text": chunk["text"],
    }


def _merge_retrieval_scores(
    keyword_rows: list[dict[str, str | float | int]],
    semantic_rows: list[dict[str, str | float | int]],
    *,
    keyword_weight: float,
    semantic_weight: float,
) -> list[dict[str, str | float | int]]:
    rows: dict[str, dict[str, str | float | int]] = {}
    scores: dict[str, float] = {}
    for row in keyword_rows:
        chunk_id = str(row["chunk_id"])
        rows[chunk_id] = row
        scores[chunk_id] = scores.get(chunk_id, 0.0) + _normalize_score(row, keyword_rows) * keyword_weight
    for row in semantic_rows:
        chunk_id = str(row["chunk_id"])
        rows[chunk_id] = row
        scores[chunk_id] = scores.get(chunk_id, 0.0) + _normalize_score(row, semantic_rows) * semantic_weight

    merged = []
    for chunk_id, row in rows.items():
        merged_row = dict(row)
        merged_row["score"] = round(scores[chunk_id], 4)
        merged.append(merged_row)
    merged.sort(key=lambda row: (-float(row["score"]), str(row["chunk_id"])))
    return merged


def _normalize_score(row: dict[str, str | float | int], rows: list[dict[str, str | float | int]]) -> float:
    max_score = max((float(item["score"]) for item in rows), default=0.0)
    if max_score <= 0:
        return 0.0
    return float(row["score"]) / max_score


def _with_rank(row: dict[str, str | float | int], rank: int) -> dict[str, str | float | int]:
    ranked = dict(row)
    ranked["rank"] = rank
    return ranked


def _build_rag_prompt(question: str, retrieved_chunks: list[dict[str, Any]]) -> str:
    context_blocks = []
    for index, chunk in enumerate(retrieved_chunks, start=1):
        context_blocks.append(
            "\n".join(
                [
                    f"[근거 {index}]",
                    f"chunk_id: {chunk.get('chunk_id', '')}",
                    f"source: {chunk.get('source_path', '')} / page {chunk.get('page', '')} / {chunk.get('section', '')}",
                    str(chunk.get("text", "")),
                ]
            )
        )
    context = "\n\n".join(context_blocks)
    return (
        "너는 RFP 문서 분석 도우미다. 아래 근거에 있는 내용만 사용해서 한국어로 짧게 답하라.\n"
        "근거에 없는 내용은 추측하지 말고 '문서에서 확인하지 못했습니다.'라고 답하라.\n\n"
        f"{context}\n\n"
        f"질문: {question}\n"
        "답변:"
    )


def _extract_generated_text(generated: Any, prompt: str) -> str:
    if isinstance(generated, list) and generated:
        first = generated[0]
        if isinstance(first, dict):
            text = str(first.get("generated_text", first.get("summary_text", "")))
        else:
            text = str(first)
    else:
        text = str(generated)
    if text.startswith(prompt):
        text = text[len(prompt) :]
    return text.strip()


def _citations_from_chunks(retrieved_chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    citations = []
    seen = set()
    for chunk in retrieved_chunks:
        chunk_id = str(chunk.get("chunk_id", ""))
        if not chunk_id or chunk_id in seen:
            continue
        seen.add(chunk_id)
        citations.append(
            {
                "chunk_id": chunk_id,
                "document_id": chunk.get("document_id", ""),
                "source_path": chunk.get("source_path", ""),
                "page": chunk.get("page", ""),
                "section": chunk.get("section", ""),
            }
        )
    return citations


def _parse_used_chunks(answer_text: str) -> set[str]:
    """LLM 응답에서 [사용근거: 1,3] 표시를 파싱합니다."""
    import re

    match = re.search(r"\[사용근거:\s*([\d,\s]+)\]", answer_text)
    if match:
        return {n.strip() for n in match.group(1).split(",") if n.strip()}
    return set()


def _build_answer_prompt(
    question: str,
    retrieved_chunks: list[dict[str, Any]],
    template: str | None = None,
) -> str:
    """prompt.py의 build_prompt를 호출하는 얇은 wrapper입니다."""
    from src.rag.prompt import build_prompt

    return build_prompt(question, retrieved_chunks, template)


def _build_scoring_kwargs_from_config(config: dict[str, Any]) -> dict[str, Any]:
    from src.rag.scoring import build_scoring_kwargs

    return build_scoring_kwargs({"rag": {"scoring": config}})


def _resolve_hf_pipeline_device(device: str) -> int:
    if device == "cuda":
        return 0
    if device == "auto":
        try:
            import torch
        except ImportError:
            return -1
        return 0 if torch.cuda.is_available() else -1
    return -1
