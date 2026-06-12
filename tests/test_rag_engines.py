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
    def __init__(self, model=None, model_name=None, **kwargs):
        self.model = model or model_name
        self.kwargs = kwargs

    def embed_documents(self, texts):
        return [[float(len(text)), 1.0] for text in texts]

    def embed_query(self, text):
        return [float(len(text)), 1.0]


class FakeChroma:
    saved_by_directory = {}
    init_calls = []

    def __init__(self, persist_directory=None, embedding_function=None):
        self.persist_directory = persist_directory
        self.embedding_function = embedding_function
        self.__class__.init_calls.append(
            {"persist_directory": persist_directory, "embedding_function": embedding_function}
        )
        self.documents = self.__class__.saved_by_directory.get(str(persist_directory), [])

    @classmethod
    def from_documents(cls, documents, embeddings, persist_directory=None):
        cls.saved_by_directory[str(persist_directory)] = list(documents)
        return cls(persist_directory=persist_directory, embedding_function=embeddings)

    def similarity_search_with_score(self, question, k):
        return [(document, 0.25) for document in self.documents[:k]]


class FakeChatResponse:
    def __init__(self, content):
        self.content = content


class FakeChatOllama:
    calls = []
    last_prompt = ""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.__class__.calls.append(kwargs)

    def invoke(self, prompt):
        self.__class__.last_prompt = prompt
        return FakeChatResponse("answer from ollama")


class FakeChatOpenAI:
    calls = []
    last_prompt = ""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.__class__.calls.append(kwargs)

    def invoke(self, prompt):
        self.__class__.last_prompt = prompt
        return FakeChatResponse("answer from openai")


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
    FakeChroma.saved_by_directory = {}
    FakeChroma.init_calls = []
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

    persist_directory = str(tmp_path / "vector_store")
    assert FakeChroma.init_calls[0]["persist_directory"] == persist_directory
    assert FakeChroma.init_calls[-1]["persist_directory"] == persist_directory
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


def test_langchain_openai_embedding_provider_uses_configured_model(monkeypatch, tmp_path: Path):
    monkeypatch.setitem(sys.modules, "langchain_openai", SimpleNamespace(OpenAIEmbeddings=FakeEmbeddings))
    config = {
        "rag": {
            "engine": "langchain",
            "embedding": {"provider": "openai", "model_name": "text-embedding-3-small"},
            "vector_store": {"type": "memory"},
            "answerer": {"provider": "local"},
        }
    }
    engine = build_rag_engine(config, tmp_path)

    rows = engine.embed_chunks([{"chunk_id": "c1", "text": "budget"}])

    assert rows[0]["embedding_model"] == "text-embedding-3-small"
    assert rows[0]["vector"] == [6.0, 1.0]


def test_langchain_ollama_answerer_returns_standard_payload(monkeypatch, tmp_path: Path):
    FakeChatOllama.calls = []
    FakeChatOllama.last_prompt = ""
    monkeypatch.setitem(
        sys.modules,
        "langchain_ollama",
        SimpleNamespace(ChatOllama=FakeChatOllama, OllamaEmbeddings=FakeEmbeddings),
    )
    config = {
        "rag": {
            "engine": "langchain",
            "embedding": {"provider": "ollama", "model_name": "nomic-embed-text"},
            "vector_store": {"type": "memory"},
            "answerer": {
                "provider": "ollama",
                "model_name": "llama3.1",
                "temperature": 0.1,
                "max_tokens": 128,
                "base_url": "http://localhost:11434",
            },
        }
    }
    engine = build_rag_engine(config, tmp_path)
    retrieved = [
        {
            "chunk_id": "doc_chunk_0001",
            "document_id": "doc",
            "source_path": "sample.txt",
            "page": "1",
            "section": "budget",
            "text": "The budget is 50 million KRW.",
        }
    ]

    answer = engine.answer("What is the budget?", retrieved)

    assert answer["answer"] == "answer from ollama"
    assert answer["status"] == "answered"
    assert answer["citations"][0]["chunk_id"] == "doc_chunk_0001"
    assert FakeChatOllama.calls[-1] == {
        "model": "llama3.1",
        "temperature": 0.1,
        "base_url": "http://localhost:11434",
        "num_predict": 128,
    }
    assert "chunk_id: doc_chunk_0001" in FakeChatOllama.last_prompt


def test_langchain_openai_answerer_returns_standard_payload(monkeypatch, tmp_path: Path):
    FakeChatOpenAI.calls = []
    FakeChatOpenAI.last_prompt = ""
    monkeypatch.setenv("TEST_OPENAI_API_KEY", "sk-test")
    monkeypatch.setitem(sys.modules, "langchain_openai", SimpleNamespace(ChatOpenAI=FakeChatOpenAI))
    config = {
        "rag": {
            "engine": "langchain",
            "embedding": {"provider": "local"},
            "vector_store": {"type": "memory"},
            "answerer": {
                "provider": "openai",
                "model_name": "gpt-4.1-mini",
                "api_key_env": "TEST_OPENAI_API_KEY",
                "temperature": 0.2,
                "max_tokens": 256,
            },
        }
    }
    engine = build_rag_engine(config, tmp_path)
    retrieved = [
        {
            "chunk_id": "doc_chunk_0002",
            "document_id": "doc",
            "source_path": "sample.txt",
            "page": "3",
            "section": "qualification",
            "text": "The vendor must have certification.",
        }
    ]

    answer = engine.answer("What is required?", retrieved)

    assert answer["answer"] == "answer from openai"
    assert answer["status"] == "answered"
    assert answer["citations"][0] == {
        "chunk_id": "doc_chunk_0002",
        "document_id": "doc",
        "source_path": "sample.txt",
        "page": "3",
        "section": "qualification",
    }
    assert FakeChatOpenAI.calls[-1] == {
        "model": "gpt-4.1-mini",
        "temperature": 0.2,
        "max_tokens": 256,
        "api_key": "sk-test",
    }
    assert "chunk_id: doc_chunk_0002" in FakeChatOpenAI.last_prompt
