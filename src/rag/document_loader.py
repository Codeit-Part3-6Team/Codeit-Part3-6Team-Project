from __future__ import annotations

import re
import zipfile
import zlib
from pathlib import Path
from typing import Callable
from xml.etree import ElementTree


SUPPORTED_FILE_TYPES = {"txt", "pdf", "docx", "hwpx", "hwp"}


def load_documents(
    project_root: str | Path,
    raw_docs_dir: str | Path,
    file_types: list[str] | None = None,
) -> list[dict[str, str]]:
    """RAG 원본 문서를 읽어 document row 목록으로 변환합니다."""
    root = Path(project_root)
    allowed_types = _normalize_file_types(file_types)
    docs_dir = _resolve_path(root, raw_docs_dir)
    if not docs_dir.exists():
        raise FileNotFoundError(f"RAG document directory not found: {docs_dir}")

    rows: list[dict[str, str]] = []
    for path in sorted(item for item in docs_dir.iterdir() if item.is_file()):
        suffix = path.suffix.lower().lstrip(".")
        if suffix not in allowed_types:
            continue
        rows.extend(_load_document_by_type(root, path, suffix))
    if not rows:
        raise ValueError(f"No supported RAG documents found in {docs_dir}: {sorted(allowed_types)}")
    return rows


def load_text_documents(project_root: str | Path, raw_docs_dir: str | Path) -> list[dict[str, str]]:
    """기존 테스트/호출부 호환을 위해 txt 문서만 읽습니다."""
    return load_documents(project_root, raw_docs_dir, ["txt"])


def _load_document_by_type(project_root: Path, path: Path, suffix: str) -> list[dict[str, str]]:
    loaders: dict[str, Callable[[Path, Path], list[dict[str, str]]]] = {
        "txt": _parse_txt_document,
        "pdf": _parse_pdf_document,
        "docx": _parse_docx_document,
        "hwpx": _parse_hwpx_document,
        "hwp": _parse_hwp_document,
    }
    try:
        return loaders[suffix](project_root, path)
    except KeyError as exc:
        raise ValueError(f"Unsupported RAG document type: {path.suffix}") from exc


def _parse_txt_document(project_root: Path, path: Path) -> list[dict[str, str]]:
    """Markdown에 가까운 txt 파일을 section 단위 document row로 나눕니다."""
    return _rows_from_section_text(project_root, path, path.read_text(encoding="utf-8"))


def _parse_pdf_document(project_root: Path, path: Path) -> list[dict[str, str]]:
    """pypdf로 PDF 페이지별 text를 추출합니다."""
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:
        raise ImportError("PDF loading requires pypdf. Install it with `pip install pypdf`.") from exc

    reader = PdfReader(str(path))
    rows: list[dict[str, str]] = []
    title = path.stem
    for index, page in enumerate(reader.pages, start=1):
        text = _normalize_text(page.extract_text() or "")
        if not text:
            continue
        _append_row(rows, project_root, path, path.stem, title, str(index), f"page {index}", text)
    return rows


def _parse_docx_document(project_root: Path, path: Path) -> list[dict[str, str]]:
    """DOCX 내부 XML에서 paragraph text를 추출합니다."""
    with zipfile.ZipFile(path) as archive:
        xml_text = archive.read("word/document.xml")
    paragraphs = _extract_xml_paragraphs(xml_text)
    return _rows_from_paragraphs(project_root, path, paragraphs)


def _parse_hwpx_document(project_root: Path, path: Path) -> list[dict[str, str]]:
    """HWPX는 zip 안의 XML 문단을 읽어 text를 추출합니다."""
    paragraphs: list[str] = []
    with zipfile.ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            if name.lower().endswith(".xml"):
                paragraphs.extend(_extract_xml_paragraphs(archive.read(name)))
    return _rows_from_paragraphs(project_root, path, paragraphs)


def _parse_hwp_document(project_root: Path, path: Path) -> list[dict[str, str]]:
    """olefile로 HWP BodyText section을 best-effort로 추출합니다."""
    try:
        import olefile  # type: ignore
    except ImportError as exc:
        raise ImportError("HWP loading requires olefile. Install it with `pip install olefile`.") from exc

    rows: list[dict[str, str]] = []
    with olefile.OleFileIO(str(path)) as ole:
        section_names = sorted(
            "/".join(item)
            for item in ole.listdir()
            if len(item) == 2 and item[0] == "BodyText" and item[1].startswith("Section")
        )
        for index, section_name in enumerate(section_names, start=1):
            data = ole.openstream(section_name).read()
            text = _extract_hwp_text(data)
            if text:
                _append_row(rows, project_root, path, path.stem, path.stem, str(index), section_name, text)
    return rows


def _rows_from_section_text(project_root: Path, path: Path, content: str) -> list[dict[str, str]]:
    document_id = path.stem
    title = path.stem
    section = "본문"
    buffer: list[str] = []
    rows: list[dict[str, str]] = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            title = line.lstrip("#").strip()
            continue
        if line.startswith("## "):
            _append_section_row(rows, project_root, path, document_id, title, section, buffer)
            section = line.lstrip("#").strip()
            buffer = []
            continue
        buffer.append(line)

    _append_section_row(rows, project_root, path, document_id, title, section, buffer)
    return rows


def _rows_from_paragraphs(project_root: Path, path: Path, paragraphs: list[str]) -> list[dict[str, str]]:
    title = path.stem
    content = "\n".join(paragraph for paragraph in paragraphs if paragraph.strip())
    if not content.strip():
        return []
    return _rows_from_section_text(project_root, path, f"# {title}\n## 본문\n{content}")


def _append_section_row(
    rows: list[dict[str, str]],
    project_root: Path,
    path: Path,
    document_id: str,
    title: str,
    section: str,
    buffer: list[str],
) -> None:
    text = _normalize_text(" ".join(buffer))
    if text:
        _append_row(rows, project_root, path, document_id, title, "1", section, text)


def _append_row(
    rows: list[dict[str, str]],
    project_root: Path,
    path: Path,
    document_id: str,
    title: str,
    page: str,
    section: str,
    text: str,
) -> None:
    rows.append(
        {
            "document_id": document_id,
            "title": title,
            "source_path": _relative_path(project_root, path),
            "page": page,
            "section": section,
            "text": text,
        }
    )


def _extract_xml_paragraphs(xml_bytes: bytes) -> list[str]:
    root = ElementTree.fromstring(xml_bytes)
    paragraphs: list[str] = []
    for element in root.iter():
        if _local_name(element.tag) not in {"p", "paragraph"}:
            continue
        text = _normalize_text("".join(element.itertext()))
        if text:
            paragraphs.append(text)
    if paragraphs:
        return paragraphs
    text = _normalize_text("".join(root.itertext()))
    return [text] if text else []


def _extract_hwp_text(data: bytes) -> str:
    for candidate in (data, _try_zlib_decompress(data)):
        if not candidate:
            continue
        text = _decode_hwp_text(candidate)
        if text:
            return text
    return ""


def _try_zlib_decompress(data: bytes) -> bytes:
    try:
        return zlib.decompress(data, -15)
    except zlib.error:
        return b""


def _decode_hwp_text(data: bytes) -> str:
    decoded = data.decode("utf-16le", errors="ignore")
    decoded = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]+", " ", decoded)
    return _normalize_text(decoded)


def _normalize_file_types(file_types: list[str] | None) -> set[str]:
    allowed = {item.lower().lstrip(".") for item in (file_types or ["txt"])}
    unknown = allowed - SUPPORTED_FILE_TYPES
    if unknown:
        raise ValueError(f"Unsupported RAG file types: {sorted(unknown)}")
    return allowed


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _resolve_path(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
