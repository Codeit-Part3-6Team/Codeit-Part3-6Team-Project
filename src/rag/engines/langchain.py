from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.rag.answerer import build_answer
from src.rag.chunker import chunk_documents as local_chunk_documents
from src.rag.embedder import DEFAULT_EMBEDDING_MODEL, embed_text


@dataclass
class LangChainRagEngine:
    """LangChain 컴포넌트로 RAG를 실행하고 프로젝트 표준 산출물로 변환하는 엔진입니다."""

    config: dict[str, Any]
    output_dir: Path

    @property
    def rag_config(self) -> dict[str, Any]:
        return self.config.get("rag", {})

    def chunk_documents(self, documents: list[dict[str, str]]) -> list[dict[str, str]]:
        splitter_cfg = self.rag_config.get("splitter", self.rag_config.get("chunk", {}))
        splitter_type = splitter_cfg.get("type", splitter_cfg.get("provider", "recursive_character"))
        if splitter_type not in {"recursive_character", "langchain", "recursive"}:
            raise NotImplementedError(f"unsupported LangChain splitter type: {splitter_type}")
        chunk_size = int(splitter_cfg.get("chunk_size", splitter_cfg.get("size", 500)))
        chunk_overlap = int(splitter_cfg.get("chunk_overlap", splitter_cfg.get("overlap", 80)))
        try:
            from langchain_core.documents import Document
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError as exc:
            if self._can_use_dependency_free_fallback():
                return local_chunk_documents(documents, chunk_size=chunk_size, overlap=chunk_overlap)
            raise ImportError(
                "LangChain splitter를 사용하려면 langchain-core와 langchain-text-splitters가 필요합니다. "
                "`pip install -r requirements.txt`를 실행하세요."
            ) from exc

        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        lc_docs = [
            Document(
                page_content=document["text"],
                metadata={
                    "document_id": document["document_id"],
                    "source_path": document["source_path"],
                    "page": document["page"],
                    "section": document["section"],
                },
            )
            for document in documents
        ]
        split_docs = splitter.split_documents(lc_docs)
        counters: dict[str, int] = {}
        chunks: list[dict[str, str]] = []
        for doc in split_docs:
            document_id = str(doc.metadata["document_id"])
            counters[document_id] = counters.get(document_id, 0) + 1
            chunk_id = f"{document_id}_chunk_{counters[document_id]:04d}"
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "source_path": str(doc.metadata.get("source_path", "")),
                    "page_start": str(doc.metadata.get("page", "")),
                    "page_end": str(doc.metadata.get("page", "")),
                    "section": str(doc.metadata.get("section", "")),
                    "text": doc.page_content,
                    "token_count": str(len(doc.page_content.split())),
                }
            )
        return chunks

    def embed_chunks(self, chunks: list[dict[str, str]]) -> list[dict[str, Any]]:
        embeddings = self._build_embeddings()
        vectors = embeddings.embed_documents([chunk["text"] for chunk in chunks])
        self._persist_vector_store(chunks, embeddings)
        return [
            {
                "chunk_id": chunk["chunk_id"],
                "embedding_model": self._embedding_model_name(),
                "vector": vector,
            }
            for chunk, vector in zip(chunks, vectors)
        ]

    def retrieve(
        self,
        question: str,
        chunks: list[dict[str, str]],
        embeddings: list[dict[str, Any]],
    ) -> list[dict[str, str | float | int]]:
        store = self._load_vector_store()
        retriever_cfg = self.rag_config.get("retriever", {})
        top_k = int(retriever_cfg.get("top_k", retriever_cfg.get("k", 3)))
        if store is not None:
            rows = store.similarity_search_with_score(question, k=top_k)
            return _retrieval_rows_from_documents(rows)
        query_vector = self._build_embeddings().embed_query(question)
        return _retrieve_from_artifact(question, chunks, embeddings, query_vector, top_k)

    def answer(self, question: str, retrieved_chunks: list[dict[str, Any]]) -> dict[str, Any]:
        answerer_cfg = self.rag_config.get("answerer", self.rag_config.get("llm", {}))
        provider = str(answerer_cfg.get("provider", answerer_cfg.get("type", "local")) or "local")
        if provider == "local":
            return build_answer(
                question,
                retrieved_chunks,
                fallback_message=answerer_cfg.get("fallback_message", "문서에서 확인하지 못했습니다."),
            )
        if not retrieved_chunks:
            return {
                "question": question,
                "answer": answerer_cfg.get("fallback_message", "문서에서 확인하지 못했습니다."),
                "citations": [],
                "status": "not_found",
            }
        prompt = _build_prompt(question, retrieved_chunks)
        model = self._build_chat_model(answerer_cfg)
        response = model.invoke(prompt)
        answer_text = getattr(response, "content", str(response)).strip()
        if not answer_text:
            answer_text = answerer_cfg.get("fallback_message", "문서에서 확인하지 못했습니다.")
        return {
            "question": question,
            "answer": answer_text,
            "citations": _citations_from_chunks(retrieved_chunks),
            "status": "answered" if retrieved_chunks else "not_found",
        }

    def _build_embeddings(self) -> Any:
        embedding_cfg = self.rag_config.get("embedding", {})
        provider = str(embedding_cfg.get("provider", embedding_cfg.get("type", "huggingface")) or "huggingface")
        model_name = str(embedding_cfg.get("model_name", "") or "")
        if provider == "local":
            return LocalLangChainEmbeddings(
                dimension=int(embedding_cfg.get("dimension", 64)),
                model_name=model_name or DEFAULT_EMBEDDING_MODEL,
            )
        if provider == "huggingface":
            try:
                from langchain_huggingface import HuggingFaceEmbeddings
            except ImportError as exc:
                raise ImportError(
                    "HuggingFaceEmbeddings를 사용하려면 langchain-huggingface가 필요합니다. "
                    "현재 기본 requirements.txt에는 포함하지 않으므로 별도 호환 환경에서 설치하세요."
                ) from exc
            return HuggingFaceEmbeddings(model_name=model_name)
        if provider == "ollama":
            try:
                from langchain_ollama import OllamaEmbeddings
            except ImportError as exc:
                raise ImportError("OllamaEmbeddings를 사용하려면 langchain-ollama가 필요합니다.") from exc
            return OllamaEmbeddings(model=model_name)
        if provider == "openai":
            try:
                from langchain_openai import OpenAIEmbeddings
            except ImportError as exc:
                raise ImportError("OpenAIEmbeddings를 사용하려면 langchain-openai가 필요합니다.") from exc
            return OpenAIEmbeddings(model=model_name)
        raise NotImplementedError(f"unsupported LangChain embedding provider: {provider}")

    def _build_chat_model(self, answerer_cfg: dict[str, Any]) -> Any:
        provider = str(answerer_cfg.get("provider", answerer_cfg.get("type", "ollama")) or "ollama")
        model_name = str(answerer_cfg.get("model_name", "") or "")
        temperature = float(answerer_cfg.get("temperature", 0.2))
        if provider == "ollama":
            try:
                from langchain_ollama import ChatOllama
            except ImportError as exc:
                raise ImportError("ChatOllama를 사용하려면 langchain-ollama가 필요합니다.") from exc
            kwargs: dict[str, Any] = {"model": model_name, "temperature": temperature}
            if answerer_cfg.get("base_url"):
                kwargs["base_url"] = answerer_cfg["base_url"]
            if answerer_cfg.get("max_tokens"):
                kwargs["num_predict"] = int(answerer_cfg["max_tokens"])
            return ChatOllama(**kwargs)
        if provider == "openai":
            try:
                from langchain_openai import ChatOpenAI
            except ImportError as exc:
                raise ImportError("ChatOpenAI를 사용하려면 langchain-openai가 필요합니다.") from exc
            kwargs = {"model": model_name, "temperature": temperature}
            if answerer_cfg.get("max_tokens"):
                kwargs["max_tokens"] = int(answerer_cfg["max_tokens"])
            api_key_env = str(answerer_cfg.get("api_key_env", "OPENAI_API_KEY") or "OPENAI_API_KEY")
            api_key = os.environ.get(api_key_env)
            if api_key:
                kwargs["api_key"] = api_key
            return ChatOpenAI(**kwargs)
        raise NotImplementedError(f"unsupported LangChain answerer provider: {provider}")

    def _embedding_model_name(self) -> str:
        embedding_cfg = self.rag_config.get("embedding", {})
        return str(embedding_cfg.get("model_name", embedding_cfg.get("provider", "langchain")))

    def _persist_vector_store(self, chunks: list[dict[str, str]], embeddings: Any) -> None:
        vector_store_cfg = self.rag_config.get("vector_store", {})
        store_type = str(vector_store_cfg.get("type", vector_store_cfg.get("provider", "memory")) or "memory")
        if store_type != "chroma":
            return
        try:
            from langchain_core.documents import Document
            from langchain_chroma import Chroma
        except ImportError as exc:
            raise ImportError("Chroma vector store를 사용하려면 langchain-chroma가 필요합니다.") from exc
        persist_dir = self._vector_store_path(vector_store_cfg)
        docs = [_document_from_chunk(chunk) for chunk in chunks]
        Chroma.from_documents(docs, embeddings, persist_directory=str(persist_dir))

    def _load_vector_store(self) -> Any | None:
        vector_store_cfg = self.rag_config.get("vector_store", {})
        store_type = str(vector_store_cfg.get("type", vector_store_cfg.get("provider", "memory")) or "memory")
        if store_type == "memory":
            return None
        if store_type != "chroma":
            raise NotImplementedError(f"unsupported LangChain vector_store type: {store_type}")
        try:
            from langchain_chroma import Chroma
        except ImportError as exc:
            raise ImportError("Chroma vector store를 사용하려면 langchain-chroma가 필요합니다.") from exc
        return Chroma(persist_directory=str(self._vector_store_path(vector_store_cfg)), embedding_function=self._build_embeddings())

    def _vector_store_path(self, vector_store_cfg: dict[str, Any]) -> Path:
        path = vector_store_cfg.get("path") or vector_store_cfg.get("persist_dir") or "vector_store"
        candidate = Path(path)
        return candidate if candidate.is_absolute() else self.output_dir / candidate

    def _can_use_dependency_free_fallback(self) -> bool:
        embedding_provider = self.rag_config.get("embedding", {}).get("provider", "local")
        answerer_provider = self.rag_config.get("answerer", {}).get("provider", "local")
        vector_store_type = self.rag_config.get("vector_store", {}).get("type", "memory")
        return embedding_provider == "local" and answerer_provider == "local" and vector_store_type == "memory"


@dataclass
class LocalLangChainEmbeddings:
    """외부 모델 없이 LangChain 엔진을 검증하기 위한 local embedding wrapper입니다."""

    dimension: int = 64
    model_name: str = DEFAULT_EMBEDDING_MODEL

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [embed_text(text, dimension=self.dimension) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return embed_text(text, dimension=self.dimension)


def _document_from_chunk(chunk: dict[str, str]) -> Any:
    from langchain_core.documents import Document

    return Document(page_content=chunk["text"], metadata=_metadata_from_chunk(chunk))


def _metadata_from_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    return {
        "chunk_id": chunk["chunk_id"],
        "document_id": chunk["document_id"],
        "source_path": chunk["source_path"],
        "page": chunk.get("page", chunk.get("page_start", "")),
        "section": chunk["section"],
    }


def _retrieval_row_from_document(rank: int, document: Any, score: float) -> dict[str, str | float | int]:
    metadata = dict(getattr(document, "metadata", {}) or {})
    chunk_id = str(metadata.get("chunk_id", ""))
    if not chunk_id:
        raise ValueError("LangChain Document metadata must include chunk_id")
    return {
        "rank": rank,
        "score": round(float(score), 4),
        "chunk_id": chunk_id,
        "document_id": str(metadata.get("document_id", "")),
        "source_path": str(metadata.get("source_path", "")),
        "page": str(metadata.get("page", "")),
        "section": str(metadata.get("section", "")),
        "text": str(getattr(document, "page_content", "")),
    }


def _retrieval_rows_from_documents(rows: list[tuple[Any, float]]) -> list[dict[str, str | float | int]]:
    """LangChain 검색 결과를 retrieval_results.jsonl에 저장 가능한 표준 dict로 변환합니다."""
    return [_retrieval_row_from_document(rank, document, score) for rank, (document, score) in enumerate(rows, start=1)]


def _retrieve_from_artifact(
    question: str,
    chunks: list[dict[str, str]],
    embeddings: list[dict[str, Any]],
    query_vector: list[float],
    top_k: int,
) -> list[dict[str, str | float | int]]:
    chunk_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    scored = []
    for row in embeddings:
        chunk = chunk_by_id.get(str(row["chunk_id"]))
        if not chunk:
            continue
        score = _dot(query_vector, row["vector"])
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


def _build_prompt(question: str, retrieved_chunks: list[dict[str, Any]]) -> str:
    context = "\n\n".join(
        f"[근거 {index}]\nchunk_id: {chunk.get('chunk_id', '')}\n{chunk.get('text', '')}"
        for index, chunk in enumerate(retrieved_chunks, start=1)
    )
    return (
        "너는 RFP 문서 분석 도우미다. 아래 근거에 있는 내용만 사용해서 한국어로 답하라.\n"
        "근거에 없는 내용은 추측하지 말고 '문서에서 확인하지 못했습니다.'라고 답하라.\n\n"
        f"{context}\n\n질문: {question}"
    )


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
