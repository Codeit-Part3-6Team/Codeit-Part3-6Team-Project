from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from src.rag.engines import build_rag_engine


class FakeDocument:
    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}


class FakeSplitter:
    def __init__(self, chunk_size, chunk_overlap):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_documents(self, documents):
        return documents


class FakeEmbeddings:
    def __init__(self, model=None, model_name=None):
        self.model = model or model_name

    def embed_documents(self, texts):
        return [[float(len(text)), 1.0] for text in texts]

    def embed_query(self, text):
        return [float(len(text)), 1.0]


class FakeChroma:
    saved_documents = []

    def __init__(self, persist_directory=None, embedding_function=None):
        self.persist_directory = persist_directory
        self.embedding_function = embedding_function
        self.documents = self.__class__.saved_documents

    @classmethod
    def from_documents(cls, documents, embeddings, persist_directory=None):
        cls.saved_documents = list(documents)
        return cls(persist_directory=persist_directory, embedding_function=embeddings)

    def similarity_search_with_score(self, question, k):
        return [(document, 0.25) for document in self.documents[:k]]


def test_langchain_engine_uses_standard_artifact_contract(monkeypatch, tmp_path: Path):
    monkeypatch.setitem(sys.modules, "langchain_core.documents", SimpleNamespace(Document=FakeDocument))
    monkeypatch.setitem(
        sys.modules,
        "langchain_text_splitters",
        SimpleNamespace(RecursiveCharacterTextSplitter=FakeSplitter),
    )
    monkeypatch.setitem(sys.modules, "langchain_ollama", SimpleNamespace(OllamaEmbeddings=FakeEmbeddings))
    config = {
        "rag": {
            "engine": "langchain",
            "splitter": {"type": "recursive_character", "chunk_size": 500, "chunk_overlap": 80},
            "embedding": {"provider": "ollama", "model_name": "nomic-embed-text"},
            "vector_store": {"type": "memory"},
            "retriever": {"method": "similarity", "top_k": 1},
            "answerer": {"mode": "extractive", "provider": "local", "fallback_message": "없음"},
        }
    }
    engine = build_rag_engine(config, tmp_path)
    documents = [
        {
            "document_id": "doc",
            "title": "sample",
            "source_path": "sample.txt",
            "page": "1",
            "section": "예산",
            "text": "본 사업의 예산은 5천만 원입니다.",
        }
    ]

    chunks = engine.chunk_documents(documents)
    embeddings = engine.embed_chunks(chunks)
    retrieved = engine.retrieve("예산이 얼마야?", chunks, embeddings)
    answer = engine.answer("예산이 얼마야?", retrieved)

    assert chunks[0]["chunk_id"] == "doc_chunk_0001"
    assert embeddings[0]["chunk_id"] == "doc_chunk_0001"
    assert isinstance(retrieved[0], dict)
    assert retrieved[0]["chunk_id"] == "doc_chunk_0001"
    assert not hasattr(retrieved[0], "page_content")
    assert answer["status"] == "answered"
    assert answer["citations"][0]["chunk_id"] == "doc_chunk_0001"


def test_langchain_vector_store_results_are_project_dicts(monkeypatch, tmp_path: Path):
    monkeypatch.setitem(sys.modules, "langchain_core.documents", SimpleNamespace(Document=FakeDocument))
    monkeypatch.setitem(
        sys.modules,
        "langchain_text_splitters",
        SimpleNamespace(RecursiveCharacterTextSplitter=FakeSplitter),
    )
    monkeypatch.setitem(sys.modules, "langchain_ollama", SimpleNamespace(OllamaEmbeddings=FakeEmbeddings))
    monkeypatch.setitem(sys.modules, "langchain_chroma", SimpleNamespace(Chroma=FakeChroma))
    config = {
        "rag": {
            "engine": "langchain",
            "splitter": {"type": "recursive_character", "chunk_size": 500, "chunk_overlap": 80},
            "embedding": {"provider": "ollama", "model_name": "nomic-embed-text"},
            "vector_store": {"type": "chroma", "path": "vector_store"},
            "retriever": {"method": "similarity", "top_k": 1},
            "answerer": {"provider": "local", "fallback_message": "없음"},
        }
    }
    engine = build_rag_engine(config, tmp_path)
    documents = [
        {
            "document_id": "doc",
            "title": "sample",
            "source_path": "sample.txt",
            "page": "2",
            "section": "자격",
            "text": "참가 자격은 중소기업 확인서를 보유한 업체입니다.",
        }
    ]

    chunks = engine.chunk_documents(documents)
    embeddings = engine.embed_chunks(chunks)
    retrieved = engine.retrieve("참가 자격은?", chunks, embeddings)

    assert retrieved == [
        {
            "rank": 1,
            "score": 0.25,
            "chunk_id": "doc_chunk_0001",
            "document_id": "doc",
            "source_path": "sample.txt",
            "page": "2",
            "section": "자격",
            "text": "참가 자격은 중소기업 확인서를 보유한 업체입니다.",
        }
    ]
