from __future__ import annotations

import pytest

from src.rag.adapters import (
    build_answerer_adapter,
    build_embedding_adapter,
    build_retriever_adapter,
    describe_rag_implementations,
)


def test_rag_adapter_registry_describes_implemented_and_contract_only_options():
    registry = describe_rag_implementations()

    implemented = {(item["type"], item["key"]) for item in registry["implemented"]}
    contract_only = {(item["type"], item["key"]) for item in registry["contract_only"]}

    assert ("embedding", "local") in implemented
    assert ("vector_store", "memory") in implemented
    assert ("retriever", "keyword") in implemented
    assert ("retriever", "semantic") in implemented
    assert ("retriever", "hybrid") in implemented
    assert ("answerer", "extractive/local") in implemented
    assert ("embedding", "huggingface") in implemented
    assert ("vector_store", "faiss") in contract_only
    assert ("answerer", "llm/openai") in contract_only


def test_local_embedding_adapter_embeds_chunks():
    adapter = build_embedding_adapter(
        {"provider": "local", "model_name": "hashing-char-ngram-v1", "dimension": 8}
    )

    rows = adapter.embed_chunks([{"chunk_id": "c1", "text": "예산은 5천만 원입니다."}])

    assert rows[0]["chunk_id"] == "c1"
    assert rows[0]["embedding_model"] == "hashing-char-ngram-v1"
    assert len(rows[0]["vector"]) == 8


def test_retriever_adapters_select_keyword_and_semantic_implementations():
    chunks = [
        {
            "chunk_id": "c1",
            "document_id": "doc",
            "source_path": "doc.txt",
            "page_start": "1",
            "section": "예산",
            "text": "사업 예산은 5천만 원입니다.",
        }
    ]
    embeddings = build_embedding_adapter({"provider": "local", "dimension": 8}).embed_chunks(chunks)

    keyword = build_retriever_adapter({"method": "keyword", "top_k": 1}, {"dimension": 8})
    semantic = build_retriever_adapter({"method": "semantic", "top_k": 1}, {"dimension": 8})

    assert keyword.retrieve("예산이 얼마야?", chunks, embeddings)[0]["chunk_id"] == "c1"
    assert semantic.retrieve("예산이 얼마야?", chunks, embeddings)[0]["chunk_id"] == "c1"


def test_extractive_answerer_adapter_builds_answer():
    answerer = build_answerer_adapter(
        {"mode": "extractive", "provider": "local", "fallback_message": "문서에서 확인하지 못했습니다."}
    )

    answer = answerer.answer("예산이 얼마야?", [])

    assert answer["status"] == "not_found"
    assert answer["answer"] == "문서에서 확인하지 못했습니다."


def test_hybrid_retriever_adapter_combines_keyword_and_semantic_scores():
    chunks = [
        {
            "chunk_id": "c1",
            "document_id": "doc",
            "source_path": "doc.txt",
            "page_start": "1",
            "section": "budget",
            "text": "The project budget is fifty million won.",
        },
        {
            "chunk_id": "c2",
            "document_id": "doc",
            "source_path": "doc.txt",
            "page_start": "1",
            "section": "docs",
            "text": "The required document is a business registration certificate.",
        },
    ]
    embeddings = build_embedding_adapter({"provider": "local", "dimension": 8}).embed_chunks(chunks)
    hybrid = build_retriever_adapter(
        {"method": "hybrid", "top_k": 1, "keyword_weight": 0.5, "semantic_weight": 0.5},
        {"dimension": 8},
    )

    rows = hybrid.retrieve("What is the project budget?", chunks, embeddings)

    assert rows[0]["chunk_id"] == "c1"
    assert rows[0]["rank"] == 1


def test_huggingface_embedding_adapter_is_registered_without_loading_model():
    adapter = build_embedding_adapter(
        {
            "provider": "huggingface",
            "model_name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "device": "cpu",
            "normalize": True,
        }
    )

    assert adapter.model_name == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def test_contract_only_adapters_raise_clear_errors():
    with pytest.raises(NotImplementedError, match="answerer"):
        build_answerer_adapter({"mode": "llm", "provider": "openai"})
