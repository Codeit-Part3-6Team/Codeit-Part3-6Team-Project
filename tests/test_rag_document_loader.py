from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from src.rag.document_loader import load_documents


def test_load_documents_reads_txt_docx_and_hwpx(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "sample.txt").write_text("# TXT 문서\n## 예산\n예산은 1억 원입니다.", encoding="utf-8")
    _write_docx(docs_dir / "sample.docx", ["DOCX 문서입니다.", "제출 마감은 금요일입니다."])
    _write_hwpx(docs_dir / "sample.hwpx", ["HWPX 문서입니다.", "참가 자격은 유사 사업 경험입니다."])

    rows = load_documents(tmp_path, "docs", ["txt", "docx", "hwpx"])

    assert {row["source_path"] for row in rows} == {
        "docs/sample.txt",
        "docs/sample.docx",
        "docs/sample.hwpx",
    }
    assert any(row["section"] == "예산" and "1억 원" in row["text"] for row in rows)
    assert any("DOCX 문서" in row["text"] for row in rows)
    assert any("HWPX 문서" in row["text"] for row in rows)


def test_load_documents_reads_pdf(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    _write_pdf(docs_dir / "sample.pdf", "PDF TEST BUDGET 123")

    rows = load_documents(tmp_path, "docs", ["pdf"])

    assert rows[0]["source_path"] == "docs/sample.pdf"
    assert rows[0]["page"] == "1"
    assert "PDF TEST BUDGET 123" in rows[0]["text"]


def test_load_documents_respects_file_type_filter(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "sample.txt").write_text("txt만 읽습니다.", encoding="utf-8")
    _write_docx(docs_dir / "sample.docx", ["읽히면 안 됩니다."])

    rows = load_documents(tmp_path, "docs", ["txt"])

    assert len(rows) == 1
    assert rows[0]["source_path"] == "docs/sample.txt"


def test_load_documents_rejects_unknown_file_type(tmp_path: Path):
    with pytest.raises(ValueError, match="Unsupported RAG file types"):
        load_documents(tmp_path, "docs", ["pptx"])


def test_load_documents_reports_invalid_hwp(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "invalid.hwp").write_bytes(b"not a real hwp file")

    with pytest.raises(ValueError, match="not a valid HWP/OLE file"):
        load_documents(tmp_path, "docs", ["hwp"])


def test_load_documents_reports_invalid_docx_structure(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    with zipfile.ZipFile(docs_dir / "invalid.docx", "w") as archive:
        archive.writestr("wrong/document.xml", "<xml />")

    with pytest.raises(ValueError, match="missing an expected internal document entry"):
        load_documents(tmp_path, "docs", ["docx"])


def _write_pdf(path: Path, text: str) -> None:
    stream = f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream",
    ]
    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{index} 0 obj\n".encode("latin-1"))
        content.extend(obj)
        content.extend(b"\nendobj\n")
    xref_offset = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1"))
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    content.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "latin-1"
        )
    )
    path.write_bytes(content)


def _write_docx(path: Path, paragraphs: list[str]) -> None:
    paragraph_xml = "".join(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in paragraphs)
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{paragraph_xml}</w:body>"
        "</w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document_xml)


def _write_hwpx(path: Path, paragraphs: list[str]) -> None:
    paragraph_xml = "".join(f"<hp:p><hp:t>{text}</hp:t></hp:p>" for text in paragraphs)
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hp:section xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">'
        f"{paragraph_xml}"
        "</hp:section>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Contents/section0.xml", document_xml)
