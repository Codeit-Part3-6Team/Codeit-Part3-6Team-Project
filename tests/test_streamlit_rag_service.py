from __future__ import annotations

import csv
import time
from pathlib import Path

from app.services import rag_service
from app.services import chat_jobs
from app.services import frontend_adapter
from src.rag.chatbot import ChatbotRunner
from src.rag.tool import ToolResult


def _write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _wait_for_chat_job(job_id: str, timeout: float = 2.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = chat_jobs.get_chat_job(job_id)
        if job and job["status"] != "running":
            return job
        time.sleep(0.01)
    raise AssertionError("chat job did not finish")


def test_chat_job_transitions_to_done(monkeypatch):
    monkeypatch.setattr(
        chat_jobs,
        "chat_ask",
        lambda question, run_id, selected_doc_ids, titles: ("답변입니다.", [("p.1", "본문")]),
    )

    job_id = chat_jobs.start_chat_job("사업 예산은?", "run-1", ["doc-1"], ["문서"])

    job = _wait_for_chat_job(job_id)

    assert job["status"] == "done"
    assert job["answer"] == "답변입니다."
    assert job["sources"] == [("p.1", "본문")]
    chat_jobs.clear_chat_job(job_id)
    assert chat_jobs.get_chat_job(job_id) is None


def test_chat_job_transitions_to_failed(monkeypatch):
    def fail_chat(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(chat_jobs, "chat_ask", fail_chat)

    job_id = chat_jobs.start_chat_job("질문", "run-1", ["doc-1"], ["문서"])

    job = _wait_for_chat_job(job_id)

    assert job["status"] == "failed"
    assert "boom" in job["error"]
    chat_jobs.clear_chat_job(job_id)


def test_chat_ask_fast_path_uses_metadata_without_rag_call(monkeypatch):
    monkeypatch.setattr(
        frontend_adapter,
        "internal_corpus",
        lambda: {
            "mode": "rag",
            "run_id": "run-1",
            "documents": [
                {
                    "document_id": "doc-1",
                    "title": "테스트 사업",
                    "org": "테스트 기관",
                    "amount": "780,230,000원",
                    "period": "계약일로부터 3개월",
                    "deadline": "",
                }
            ],
            "error": None,
        },
    )

    def fail_load_rag():
        raise AssertionError("fast path should not load rag")

    monkeypatch.setattr(frontend_adapter, "_load_rag", fail_load_rag)

    answer, sources = frontend_adapter.chat_ask("사업 예산은?", "run-1", ["doc-1"], ["테스트 사업"])

    assert answer == "사업예산은 780,230,000원입니다."
    assert sources == [("문서 메타데이터", "사전 추출")]


def test_chat_ask_slow_path_handles_missing_fast_metadata(monkeypatch):
    class FakeRag:
        def ask_with_document_filter(self, run_id, question, selected_doc_ids):
            return {"reply": "문서에서 제출 마감일 정보를 확인하지 못했습니다.", "citations": [], "error": None}

    monkeypatch.setattr(
        frontend_adapter,
        "internal_corpus",
        lambda: {
            "mode": "rag",
            "run_id": "run-1",
            "documents": [{"document_id": "doc-1", "title": "테스트 사업", "deadline": ""}],
            "error": None,
        },
    )
    monkeypatch.setattr(frontend_adapter, "_load_rag", lambda: FakeRag())

    answer, _ = frontend_adapter.chat_ask("제출 마감일은?", "run-1", ["doc-1"], ["테스트 사업"])

    assert answer == "문서에서 제출 마감일 정보를 확인하지 못했습니다."


def test_chat_ask_fast_path_returns_field_candidate_before_slow_rag(monkeypatch):
    class FakeRag:
        def find_field_candidates(self, run_id, selected_doc_ids, field, limit=3):
            assert field == "사업기간"
            return [
                {
                    "chunk_id": "chunk-1",
                    "source_path": "raw_docs/test.pdf",
                    "page": "4",
                    "section": "계약 조건",
                    "text": "사업기간은 계약체결일로부터 120일입니다.",
                }
            ]

        def ask_with_document_filter(self, run_id, question, selected_doc_ids):
            raise AssertionError("candidate fast path should not call slow rag")

    monkeypatch.setattr(
        frontend_adapter,
        "internal_corpus",
        lambda: {
            "mode": "rag",
            "run_id": "run-1",
            "documents": [{"document_id": "doc-1", "title": "테스트 사업", "period": ""}],
            "error": None,
        },
    )
    monkeypatch.setattr(frontend_adapter, "_load_rag", lambda: FakeRag())

    answer, sources = frontend_adapter.chat_ask("사업 기간은?", "run-1", ["doc-1"], ["테스트 사업"])

    assert "문서 메타데이터에는 사업 기간 정보가 없지만" in answer
    assert "- 사업기간은 계약체결일로부터 120일입니다." in answer
    assert sources == [("p.4", "계약 조건")]


def test_chat_ask_slow_path_keeps_reasoning_questions_on_rag(monkeypatch):
    class FakeRag:
        def ask_with_document_filter(self, run_id, question, selected_doc_ids):
            return {"reply": "정밀 분석 답변", "citations": [], "error": None}

    monkeypatch.setattr(
        frontend_adapter,
        "internal_corpus",
        lambda: {
            "mode": "rag",
            "run_id": "run-1",
            "documents": [{"document_id": "doc-1", "title": "테스트 사업"}],
            "error": None,
        },
    )
    monkeypatch.setattr(frontend_adapter, "_load_rag", lambda: FakeRag())

    answer, sources = frontend_adapter.chat_ask("이 사업 참여 가능할까?", "run-1", ["doc-1"], ["테스트 사업"])

    assert answer == "정밀 분석 답변"
    assert sources == []


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


def test_find_field_candidates_returns_period_sentence(tmp_path, monkeypatch):
    monkeypatch.setattr(rag_service, "_STREAMLIT_EXPERIMENTS", tmp_path)
    output_dir = tmp_path / "run-1" / "output"

    _write_csv(
        output_dir / "chunks.csv",
        [
            {
                "chunk_id": "chunk-1",
                "document_id": "doc-1",
                "source_path": "raw_docs/test.pdf",
                "page_start": "4",
                "page_end": "4",
                "section": "계약 조건",
                "text": "계약 조건입니다. 사업기간은 계약체결일로부터 120일입니다. 다른 문장입니다.",
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

    candidates = rag_service.find_field_candidates("run-1", ["doc-1"], "사업기간")

    assert candidates == [
        {
            "chunk_id": "chunk-1",
            "document_id": "doc-1",
            "source_path": "raw_docs/test.pdf",
            "page": "4",
            "section": "계약 조건",
            "text": "사업기간은 계약체결일로부터 120일입니다.",
        }
    ]


def test_get_documents_enriches_period_and_deadline(tmp_path, monkeypatch):
    monkeypatch.setattr(rag_service, "_STREAMLIT_EXPERIMENTS", tmp_path)
    output_dir = tmp_path / "run-1" / "output"

    _write_csv(
        output_dir / "parsed_documents.csv",
        [
            {
                "document_id": "doc-1",
                "title": "테스트 제안요청서",
                "source_path": "raw_docs/test.pdf",
                "meta_사업 요약": "- 사업기간: 계약일로부터 3개월\n- 제출마감: 2026-07-20 17:00",
            }
        ],
        ["document_id", "title", "source_path", "meta_사업 요약"],
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
                "text": "본문",
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

    document = rag_service.get_documents("run-1")[0]

    assert document["period"] == "계약일로부터 3개월"
    assert document["deadline"] == "2026-07-20 17:00"


def test_get_documents_reads_actual_bid_deadline_column(tmp_path, monkeypatch):
    monkeypatch.setattr(rag_service, "_STREAMLIT_EXPERIMENTS", tmp_path)
    output_dir = tmp_path / "run-1" / "output"

    _write_csv(
        output_dir / "parsed_documents.csv",
        [
            {
                "document_id": "doc-1",
                "title": "테스트 제안요청서",
                "source_path": "raw_docs/test.pdf",
                "meta_입찰 참여 시작일": "2026-07-01 09:00",
                "meta_입찰 참여 마감일": "2026-07-20 17:00",
            }
        ],
        [
            "document_id",
            "title",
            "source_path",
            "meta_입찰 참여 시작일",
            "meta_입찰 참여 마감일",
        ],
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
                "text": "본문",
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

    document = rag_service.get_documents("run-1")[0]

    assert document["deadline"] == "2026-07-20 17:00"


def test_labeled_summary_builds_fast_workspace_sections():
    summary = (
        "- 사업개요: 통합사회정보시스템 운영 지원 "
        "- 추진배경: 안정적인 서비스 제공 필요 "
        "- 사업범위: 시스템 유지관리 및 기능개선 "
        "- 기대효과: 업무 효율 제고 "
        "- 추진목표: 서비스 향상"
    )

    overview = frontend_adapter._parse_labeled_summary(summary)

    assert overview["사업개요"] == "통합사회정보시스템 운영 지원"
    assert overview["사업범위"] == "시스템 유지관리 및 기능개선"
    assert "주요 범위: 시스템 유지관리 및 기능개선" in frontend_adapter._build_summary_from_overview(overview)
    assert "[주요 과업] 시스템 유지관리 및 기능개선" in frontend_adapter._build_requirements_from_overview(overview)


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


def test_display_reply_prefers_natural_reply_over_structured_output():
    reply = "참가 자격은 소프트웨어사업자 신고와 중소기업 확인이 핵심입니다."
    structured = {"참가자격": ["소프트웨어사업자 신고", "중소기업확인서"]}

    assert rag_service._display_reply(reply, structured) == reply


def test_sanitize_chat_reply_removes_streamlit_chrome():
    reply = (
        "사업예산은 100원입니다.\n"
        "[IT'S MINE](http://localhost:8501/workspace)\n"
        "[서비스 소개](http://localhost:8501/about)\n"
        "근거는 문서 본문입니다."
    )

    sanitized = frontend_adapter._sanitize_chat_reply(reply)

    assert "localhost:8501" not in sanitized
    assert "사업예산은 100원입니다." in sanitized
    assert "근거는 문서 본문입니다." in sanitized


def test_chatbot_formats_structured_output_as_chat_reply():
    bot = ChatbotRunner(tools={})
    result = ToolResult(
        tool_name="extract_requirements",
        structured_output={
            "제출서류": ["제안서 1부", "가격제안서 1부"],
            "참가자격": ["소프트웨어사업자"],
        },
    )

    reply = bot._format_chat_result("제출 서류는?", result)

    assert "문서에서 확인한 목록" in reply
    assert "제출서류" in reply
    assert "| 제출서류 | 제안서 1부 |" in reply
    assert "참가자격" not in reply
    assert "['" not in reply


def test_chatbot_classifies_representative_question_types():
    bot = ChatbotRunner(tools={})

    assert bot._classify_chat_presentation("사업 예산은?").answer_type == "scalar"
    assert bot._classify_chat_presentation("제출 서류는?").answer_type == "list"
    assert bot._classify_chat_presentation("참가 자격은?").answer_type == "checklist"
    assert bot._classify_chat_presentation("평가 기준은?").answer_type == "evaluation"
    assert bot._classify_chat_presentation("참여 가능할까?").answer_type == "judgement"


def test_chatbot_scalar_projection_omits_unasked_fields():
    bot = ChatbotRunner(tools={})
    result = ToolResult(
        tool_name="extract_facts",
        structured_output={
            "사업예산": "133,812,000원",
            "발주기관": "경기도사회서비스원",
            "사업명": "2024년 통합사회정보시스템 운영지원",
        },
    )

    reply = bot._format_chat_result("사업 예산은?", result)

    assert reply == "사업예산은 133,812,000원입니다."
    assert "발주기관" not in reply
    assert "사업명" not in reply


def test_chatbot_scalar_projection_strips_embedded_label_and_sentence_ending():
    bot = ChatbotRunner(tools={})
    result = ToolResult(
        tool_name="extract_facts",
        structured_output={"사업예산": "사업 예산은 780,230,000원입니다."},
    )

    reply = bot._format_chat_result("사업 예산은?", result)

    assert reply == "사업예산은 780,230,000원입니다."
    assert "입니다.입니다" not in reply
    assert "사업예산은 사업 예산은" not in reply


def test_chatbot_splits_long_evaluation_text_into_bullets():
    bot = ChatbotRunner(tools={})
    result = ToolResult(
        tool_name="extract_requirements",
        structured_output={
            "평가기준": (
                "총점 100점(기술능력평가 90% + 입찰가격평가 10%). "
                "기술능력평가(90 = 정량 20 + 정성 70) "
                "정량평가(20점) a. 경영상태(6점) 기업신용평가등급에 따라 배점. "
                "사업수행실적(6점) 최근 3년 실적 비율에 따라 부여. "
                "정성평가(70점) 전략 및 방법론(15점) 등 세부배점에 따라 평가. "
                "입찰가격평가(10점) 입찰가격에 대한 정량적 평가. "
                "제안서 설명: 발표 20분 이내, 질의응답 10분 이내. "
                "명시되지 않음 항목 예: 입찰참가 자격의 국적·등록요건은 근거에 없음"
            )
        },
    )

    reply = bot._format_chat_result("평가 기준은?", result)

    assert "문서에서 확인한 평가 기준입니다." in reply
    assert "- 총점 100점" in reply
    assert "- 기술능력평가" in reply
    assert "- 정량평가" in reply
    assert "- 정성평가" in reply
    assert "- 입찰가격평가" in reply
    assert "명시되지 않음 항목 예" not in reply
    assert len([line for line in reply.splitlines() if line.startswith("- ")]) >= 4


def test_chatbot_splits_evaluation_sentences_without_tiny_fragments():
    bot = ChatbotRunner(tools={})
    result = ToolResult(
        tool_name="extract_requirements",
        structured_output={
            "평가기준": (
                "종합평가 = 기술평가(90%) + 가격평가(10%). "
                "기술평가는 전문가로 구성된 기술평가위원회가 실시하며, 각 위원이 평가한 점수에서 "
                "최고·최저 점수를 제외한 나머지 점수의 산술평균을 산출하여 90점 만점으로 환산한다. "
                "기술능력평가 분야에서 배점한도의 85% 이상 득점한 자를 협상 적격자로 선정한다. "
                "기술평가는 정량평가·정성평가로 구성되며 PT(발표15분, 질의응답10분)가 평가절차에 포함된다. "
                "신용평가등급에 따른 배점비율은 공고문에 제시된 등급구간표를 준용한다."
            )
        },
    )

    reply = bot._format_chat_result("평가 기준은?", result)
    bullets = [line for line in reply.splitlines() if line.startswith("- ")]

    assert any("종합평가 = 기술평가" in line for line in bullets)
    assert any("기술능력평가 분야" in line for line in bullets)
    assert any("정량평가" in line and "정성평가" in line for line in bullets)
    assert all(line.strip() not in {"- 정량평가·", "- 정성평가"} for line in bullets)


def test_chatbot_missing_scalar_reply_uses_natural_korean_label():
    bot = ChatbotRunner(tools={})
    result = ToolResult(
        tool_name="extract_facts",
        structured_output={
            "사업예산": "133,812,000원",
            "사업기간": "명시되지 않음",
            "제출마감": "명시되지 않음",
        },
    )

    period_reply = bot._format_chat_result("사업 기간은?", result)
    deadline_reply = bot._format_chat_result("제출 마감일은?", result)

    assert period_reply == "문서에서 사업 기간 정보를 확인하지 못했습니다."
    assert deadline_reply == "문서에서 제출 마감일 정보를 확인하지 못했습니다."
    assert "을(를)" not in period_reply
    assert "을(를)" not in deadline_reply


def test_chatbot_deadline_question_does_not_fall_back_to_project_period():
    bot = ChatbotRunner(tools={})
    result = ToolResult(
        tool_name="extract_facts",
        structured_output={
            "사업기간": "계약일로부터 3개월",
            "제출마감": "명시되지 않음",
        },
    )

    reply = bot._format_chat_result("제출 마감일은?", result)

    assert reply == "문서에서 제출 마감일 정보를 확인하지 못했습니다."
    assert "계약일로부터 3개월" not in reply


def test_chatbot_fast_router_skips_llm_selection_for_common_question():
    bot = ChatbotRunner(tools={"extract_facts": object(), "extract_requirements": object()})

    assert bot._select_tool_by_presentation("사업 예산은?") == "extract_facts"
    assert bot._select_tool_by_presentation("제출 서류는?") == "extract_requirements"


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
