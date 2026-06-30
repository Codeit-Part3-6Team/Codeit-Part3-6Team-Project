"""RAG 서비스 어댑터 사용 예시.

이 파일은 최종 UI가 아니라 프론트엔드 연결 참고용입니다.
Streamlit 화면에서는 아래 흐름을 버튼/세션 상태에 맞게 옮기면 됩니다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = PROJECT_ROOT / "app"
for path in (PROJECT_ROOT, APP_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from services.rag_service import (
    ask_with_document_filter,
    create_and_ingest,
    extract_requirements,
    get_documents,
    summarize,
)


def _print_response(title: str, response: dict) -> None:
    print(f"\n## {title}")
    if response.get("error"):
        print(f"ERROR: {response['error']}")
        return

    structured = response.get("structured_output")
    if structured:
        print("\nstructured_output:")
        for key, value in structured.items():
            print(f"- {key}: {value}")

        print("\nUI 카드 예시:")
        print("  data = response['structured_output']")
        print("  st.metric('발주기관', data.get('발주기관', '명시되지 않음'))")
        print("  st.metric('사업예산', data.get('사업예산', '명시되지 않음'))")

    print("\nreply:")
    print(response.get("reply") or "(empty reply)")

    citations = response.get("citations") or []
    if citations:
        print("\n근거:")
        seen = set()
        for citation in citations:
            source = Path(str(citation.get("source_path") or "")).name or "원문"
            page = citation.get("page") or citation.get("page_start")
            label = f"{source} p.{page}" if page not in (None, "", "?") else source
            if label in seen:
                continue
            seen.add(label)
            print(f"- {label}")


def run_example(raw_docs_dir: str, question: str) -> None:
    """업로드 디렉토리를 RAG run으로 만들고 기본 분석/질의를 실행합니다."""
    ingest = create_and_ingest(raw_docs_dir)
    if ingest.get("status") != "ready":
        raise RuntimeError(ingest.get("error") or "RAG ingest failed")

    run_id = ingest["run_id"]
    print(f"run_id={run_id}")
    print(f"documents={ingest['documents']} chunks={ingest['chunks']} embeddings={ingest['embeddings']}")

    documents = get_documents(run_id)
    print("\n문서 목록:")
    for document in documents:
        print(f"- {document['document_id']} | {document.get('title') or document['document_id']}")

    selected_doc_ids = [documents[0]["document_id"]] if documents else None

    _print_response("핵심 요약", summarize(run_id, selected_doc_ids))
    _print_response("참가 자격/제출 서류", extract_requirements(run_id, selected_doc_ids))
    _print_response("사용자 질문", ask_with_document_filter(run_id, question, selected_doc_ids))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_docs_dir", help="업로드된 원본 문서가 들어 있는 디렉토리")
    parser.add_argument(
        "--question",
        default="사업 예산과 기간은?",
        help="챗봇에 전달할 예시 질문",
    )
    args = parser.parse_args()
    run_example(args.raw_docs_dir, args.question)


if __name__ == "__main__":
    main()
