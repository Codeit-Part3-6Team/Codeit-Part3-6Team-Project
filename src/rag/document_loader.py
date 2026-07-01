from __future__ import annotations

import re
import zipfile
import zlib
from pathlib import Path
from typing import Callable
from xml.etree import ElementTree


SUPPORTED_FILE_TYPES = {"txt", "pdf", "docx", "hwpx", "hwp", "csv"}


def load_documents(
    project_root: str | Path,
    raw_docs_dir: str | Path,
    file_types: list[str] | None = None,
    csv_file: str | None = None,
) -> list[dict[str, str]]:
    """RAG 원본 문서를 읽어 document row 목록으로 변환합니다.
    csv_file가 지정되면 해당 CSV 파일만 읽습니다 (중복 방지).
    """
    root = Path(project_root)
    allowed_types = _normalize_file_types(file_types)
    docs_dir = _resolve_path(root, raw_docs_dir)
    if not docs_dir.exists():
        raise FileNotFoundError(f"RAG document directory not found: {docs_dir}")

    rows: list[dict[str, str]] = []
    if csv_file and "csv" in allowed_types:
        csv_path = docs_dir / csv_file
        if csv_path.exists():
            rows.extend(_parse_csv_document(root, csv_path))
    else:
        for path in sorted(item for item in docs_dir.rglob("*") if item.is_file()):
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
        "csv": _parse_csv_document,
    }
    loader = loaders.get(suffix)
    if loader is None:
        raise ValueError(f"Unsupported RAG document type: {path.suffix}")
    try:
        return loader(project_root, path)
    except KeyError as exc:
        raise ValueError(f"{path} is missing an expected internal document entry: {exc}") from exc


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


def _parse_csv_document(project_root: Path, path: Path) -> list[dict[str, str]]:
    """CSV 메타데이터 파일을 읽어 각 행을 document row로 변환합니다.
    data_list.csv 컬럼 매핑:
      공고 번호 -> document_id
      사업명 -> title
      텍스트 -> text
      사업 금액, 발주 기관 등 -> 추가 metadata 컬럼
    """
    import csv
    csv.field_size_limit(int(1e9))

    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for entry in reader:
            doc_id = entry.get("공고 번호", "").strip()
            title = entry.get("사업명", "").strip()
            text = entry.get("텍스트", "").strip()
            if not doc_id or not text:
                continue
            row: dict[str, str] = {
                "document_id": doc_id,
                "title": title or doc_id,
                "source_path": _relative_path(project_root, path),
                "page": "1",
                "section": "본문",
                # preamble은 chunker가 각 청크마다 삽입하므로 text에서 분리한다.
                # text에는 목차 제거 후 정규화된 본문만 담는다.
                "preamble": _build_meta_preamble(entry, title),
                "text": _normalize_text(_remove_toc(text)),
            }
            for meta_key in ("사업 금액", "발주 기관", "공고 차수", "파일형식", "파일명", "사업 요약"):
                value = entry.get(meta_key, "").strip()
                if value:
                    row[f"meta_{meta_key}"] = value
            rows.append(row)
    return rows


def _build_meta_preamble(entry: dict[str, str], title: str) -> str:
    parts = [f"사업명: {title}"] if title else []
    기관 = entry.get("발주 기관", "").strip()
    if 기관:
        parts.append(f"발주기관: {기관}")
    금액 = entry.get("사업 금액", "").strip()
    if 금액:
        parts.append(f"사업금액: {_format_amount(금액)}")
    차수 = entry.get("공고 차수", "").strip()
    if 차수:
        parts.append(f"공고차수: {차수}")
    return " | ".join(parts)


def _format_amount(value: str) -> str:
    try:
        return f"{int(float(value)):,}원"
    except ValueError:
        return value


def _parse_hwp_document(project_root: Path, path: Path) -> list[dict[str, str]]:
    """olefile + HWP5 레코드 파싱으로 BodyText section의 문단 텍스트를 추출합니다."""
    try:
        import olefile  # type: ignore
    except ImportError as exc:
        raise ImportError("HWP loading requires olefile. Install it with `pip install olefile`.") from exc

    rows: list[dict[str, str]] = []
    try:
        ole = olefile.OleFileIO(str(path))
    except olefile.olefile.NotOleFileError as exc:
        raise ValueError(f"{path} is not a valid HWP/OLE file.") from exc

    with ole:
        section_items = sorted(
            (
                item
                for item in ole.listdir()
                if len(item) == 2 and item[0] == "BodyText" and item[1].startswith("Section")
            ),
            key=lambda item: int(item[1].removeprefix("Section")),
        )
        for index, item in enumerate(section_items, start=1):
            section_name = "/".join(item)
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


HWPTAG_PARA_TEXT = 0x10 + 51  # 67: BodyText section 레코드 중 문단 텍스트 레코드


def _extract_hwp_text(data: bytes) -> str:
    """BodyText section bytes(압축 여부 무관)에서 문단 텍스트만 추출합니다.

    section 전체를 단순히 UTF-16으로 디코딩하면 표/그림/스타일 등 비텍스트
    레코드의 바이너리가 노이즈로 섞여 본문이 묻힌다. 레코드 헤더를 읽어
    HWPTAG_PARA_TEXT 레코드만 디코딩해야 깨끗한 본문을 얻을 수 있다.
    """
    decompressed = _try_zlib_decompress(data)
    return _normalize_text(_parse_hwp_records(decompressed or data))


def _try_zlib_decompress(data: bytes) -> bytes:
    try:
        return zlib.decompress(data, -15)
    except zlib.error:
        return b""


def _parse_hwp_records(data: bytes) -> str:
    paragraphs: list[str] = []
    pos, size_of_data = 0, len(data)
    while pos + 4 <= size_of_data:
        header = int.from_bytes(data[pos : pos + 4], "little")
        tag_id = header & 0x3FF
        size = (header >> 20) & 0xFFF
        pos += 4
        if size == 0xFFF:
            if pos + 4 > size_of_data:
                break
            size = int.from_bytes(data[pos : pos + 4], "little")
            pos += 4
        record_data = data[pos : pos + size]
        pos += size
        if tag_id == HWPTAG_PARA_TEXT:
            text = _decode_hwp_para_text(record_data)
            if text.strip():
                paragraphs.append(text)
    return "\n".join(paragraphs)


def _decode_hwp_para_text(data: bytes) -> str:
    """문단 텍스트 레코드를 디코딩합니다.

    코드값 32 미만의 제어문자는 표/필드 등 인라인 컨트롤을 가리키며, 뒤따르는
    WCHAR 7개(14바이트)는 텍스트가 아니라 컨트롤 부가정보이므로 함께 건너뛴다.
    surrogate pair로 표현되는 문자가 끊기지 않도록, 일반 텍스트 구간은
    바이트 버퍼에 모아 한 번에 utf-16-le로 디코딩한다.
    """
    parts: list[str] = []
    buffer = bytearray()
    i, n = 0, len(data) - (len(data) % 2)
    while i < n:
        code = int.from_bytes(data[i : i + 2], "little")
        if code in (9, 10, 13) or code >= 32:
            buffer += data[i : i + 2]
            i += 2
            continue
        if buffer:
            parts.append(buffer.decode("utf-16-le", errors="ignore"))
            buffer.clear()
        i += 2 + 14
    if buffer:
        parts.append(buffer.decode("utf-16-le", errors="ignore"))
    return "".join(parts)


def _normalize_file_types(file_types: list[str] | None) -> set[str]:
    allowed = {item.lower().lstrip(".") for item in (file_types or ["txt"])}
    unknown = allowed - SUPPORTED_FILE_TYPES
    if unknown:
        raise ValueError(f"Unsupported RAG file types: {sorted(unknown)}")
    return allowed


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# HWP 페이지번호 특수문자(袏請畏裗 등)는 U+4E00-U+9FFF (CJK 통합 한자) 범위에 있다.
# 한글 음절(U+AC00-U+D7A3)은 이 범위 밖이므로 오탐 없음.
_HWP_PAGE_CHAR = re.compile(r"[\u4E00-\u9FFF\uF900-\uFAFF]")
_TOC_HEADER = re.compile(r"목\s+차")


def _remove_toc(text: str) -> str:
    """목차 항목 줄을 개별 제거한다.

    범위 삭제 대신 줄 단위 필터를 사용해 목차와 본문이 혼재된 문서에서
    본문이 지워지는 문제를 방지한다.
    """
    lines = text.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()
        if _TOC_HEADER.search(line) and len(stripped) < 20:
            continue
        if stripped and _HWP_PAGE_CHAR.search(stripped) and "\t" in line and len(stripped) < 80:
            continue
        result.append(line)
    return "\n".join(result)


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
