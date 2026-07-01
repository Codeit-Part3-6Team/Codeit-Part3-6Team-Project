from __future__ import annotations

import csv
from pathlib import Path

from app.services import rag_service


def _write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def test_get_documents_uses_parsed_document_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(rag_service, "_STREAMLIT_EXPERIMENTS", tmp_path)
    output_dir = tmp_path / "run-1" / "output"

    _write_csv(
        output_dir / "parsed_documents.csv",
        [
            {
                "document_id": "doc-1",
                "title": "테스트 제안요청서",
                "source_path": "raw_docs/test.pdf",
                "page": "1",
                "section": "",
                "text": "본문",
            }
        ],
        ["document_id", "title", "source_path", "page", "section", "text"],
    )
    _write_csv(
        output_dir / "chunks.csv",
        [
            {
                "chunk_id": "chunk-1",
                "document_id": "doc-1",
                "source_path": "raw_docs/test.pdf",
                "page_start": "1",
                "page_end": "1",
                "section": "",
                "text": "첫 번째 청크",
                "token_count": "10",
            },
            {
                "chunk_id": "chunk-2",
                "document_id": "doc-1",
                "source_path": "raw_docs/test.pdf",
                "page_start": "2",
                "page_end": "2",
                "section": "",
                "text": "두 번째 청크",
                "token_count": "12",
            },
        ],
        [
            "chunk_id",
            "document_id",
            "source_path",
            "page_start",
            "page_end",
            "section",
            "text",
            "token_count",
        ],
    )

    assert rag_service.get_documents("run-1") == [
        {
            "document_id": "doc-1",
            "title": "테스트 제안요청서",
            "source_path": "raw_docs/test.pdf",
            "chunk_count": 2,
        }
    ]


def test_get_citation_returns_chunk_text(tmp_path, monkeypatch):
    monkeypatch.setattr(rag_service, "_STREAMLIT_EXPERIMENTS", tmp_path)
    output_dir = tmp_path / "run-1" / "output"

    _write_csv(
        output_dir / "chunks.csv",
        [
            {
                "chunk_id": "chunk-1",
                "document_id": "doc-1",
                "source_path": "raw_docs/test.pdf",
                "page_start": "3",
                "page_end": "3",
                "section": "사업 개요",
                "text": "근거 원문입니다.",
                "token_count": "10",
            }
        ],
        [
            "chunk_id",
            "document_id",
            "source_path",
            "page_start",
            "page_end",
            "section",
            "text",
            "token_count",
        ],
    )

    citation = rag_service.get_citation("run-1", "chunk-1")

    assert citation is not None
    assert citation["text"] == "근거 원문입니다."
    assert citation["section"] == "사업 개요"


def test_strip_source_block_removes_inline_citations():
    reply = "답변입니다.\n\n[출처]\n문서 1\n문서 2"

    assert rag_service._strip_source_block(reply) == "답변입니다."


def test_format_structured_output_keeps_fields_readable():
    structured = {
        "발주기관": "한국농어촌공사",
        "사업기간": "명시되지 않음",
        "자격요건": ["PM은 ODA 유경험자", "중복투입 불가"],
    }

    formatted = rag_service._format_structured_output(structured)

    assert "발주기관: 한국농어촌공사" in formatted
    assert "사업기간: 명시되지 않음" in formatted
    assert "자격요건\n- PM은 ODA 유경험자\n- 중복투입 불가" in formatted


def test_dedupe_citations_by_chunk_id():
    citations = [
        {"chunk_id": "c1", "source_path": "a.pdf", "page": "1", "section": "본문"},
        {"chunk_id": "c2", "source_path": "a.pdf", "page": "1", "section": "본문"},
        {"chunk_id": "c3", "source_path": "a.pdf", "page": "2", "section": "본문"},
    ]

    assert rag_service._dedupe_citations(citations) == [
        {"chunk_id": "c1", "source_path": "a.pdf", "page": "1", "section": "본문"},
        {"chunk_id": "c3", "source_path": "a.pdf", "page": "2", "section": "본문"},
    ]


def test_compare_selected_documents_includes_every_selected_doc(monkeypatch):
    docs = [
        {"document_id": "doc-a", "title": "문서 A", "source_path": "a.pdf", "chunk_count": 3},
        {"document_id": "doc-b", "title": "문서 B", "source_path": "b.pdf", "chunk_count": 3},
        {"document_id": "doc-c", "title": "문서 C", "source_path": "c.pdf", "chunk_count": 3},
    ]
    monkeypatch.setattr(rag_service, "get_documents", lambda run_id: docs)

    def fake_summarize(run_id: str, selected_doc_ids: list[str] | None = None) -> dict:
        doc_id = selected_doc_ids[0]
        return {
            "reply": "",
            "structured_output": {
                "사업명": f"{doc_id} 사업",
                "발주기관": f"{doc_id} 기관",
                "사업예산": "100원",
                "사업기간": "1개월",
                "제출마감": "명시되지 않음",
                "자격요건": [f"{doc_id} 요건"],
            },
            "citations": [{"source_path": f"{doc_id}.pdf", "page": "1", "section": "본문"}],
            "error": None,
        }

    monkeypatch.setattr(rag_service, "summarize", fake_summarize)

    result = rag_service.compare("run-1", ["doc-a", "doc-b", "doc-c"])

    assert result["status"] == "ok"
    assert result["structured_output"]["문서목록"] == ["문서 A", "문서 B", "문서 C"]
    assert "doc-a 사업" in result["reply"]
    assert "doc-b 사업" in result["reply"]
    assert "doc-c 사업" in result["reply"]
