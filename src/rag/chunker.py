from __future__ import annotations


def chunk_documents(
    documents: list[dict[str, str]],
    chunk_size: int = 500,
    overlap: int = 80,
) -> list[dict[str, str]]:
    """document row를 검색 가능한 chunk row 목록으로 변환합니다."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be zero or positive")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[dict[str, str]] = []
    counters: dict[str, int] = {}
    for document in documents:
        document_id = document["document_id"]
        counters.setdefault(document_id, 0)
        preamble = document.get("preamble", "")
        for body in _split_text(document["text"], chunk_size, overlap):
            counters[document_id] += 1
            chunk_id = f"{document_id}_chunk_{counters[document_id]:04d}"
            text = f"[{preamble}]  {body}" if preamble else body
            # source/page metadata를 chunk에 복사해야 답변 단계에서 citation을 만들 수 있습니다.
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "source_path": document["source_path"],
                    "page_start": document["page"],
                    "page_end": document["page"],
                    "section": document["section"],
                    "text": text,
                    "token_count": str(len(text.split())),
                }
            )
    return chunks


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    clean_text = " ".join(text.split())
    if len(clean_text) <= chunk_size:
        return [clean_text]

    chunks: list[str] = []
    start = 0
    while start < len(clean_text):
        end = min(start + chunk_size, len(clean_text))
        chunks.append(clean_text[start:end].strip())
        if end == len(clean_text):
            break
        start = end - overlap
    return [chunk for chunk in chunks if chunk]
