from __future__ import annotations

from pathlib import Path


def load_text_documents(project_root: str | Path, raw_docs_dir: str | Path) -> list[dict[str, str]]:
    """txt RFP 문서를 읽어 RAG 파이프라인의 document row 목록으로 변환합니다."""
    root = Path(project_root)
    docs_dir = _resolve_path(root, raw_docs_dir)
    if not docs_dir.exists():
        raise FileNotFoundError(f"RAG document directory not found: {docs_dir}")

    rows: list[dict[str, str]] = []
    for path in sorted(docs_dir.glob("*.txt")):
        rows.extend(_parse_txt_document(root, path))
    if not rows:
        raise ValueError(f"No txt documents found in {docs_dir}")
    return rows


def _parse_txt_document(project_root: Path, path: Path) -> list[dict[str, str]]:
    """Markdown에 가까운 txt 파일을 section 단위 document row로 나눕니다."""
    document_id = path.stem
    title = path.stem
    section = "본문"
    buffer: list[str] = []
    rows: list[dict[str, str]] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
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


def _append_section_row(
    rows: list[dict[str, str]],
    project_root: Path,
    path: Path,
    document_id: str,
    title: str,
    section: str,
    buffer: list[str],
) -> None:
    text = " ".join(buffer).strip()
    if not text:
        return
    rows.append(
        {
            "document_id": document_id,
            "title": title,
            "source_path": _relative_path(project_root, path),
            "page": "1",
            "section": section,
            "text": text,
        }
    )


def _resolve_path(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
