from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_HTML_DOCS = {
    Path("docs/html/kickoff/kickoff.html"),
    Path("docs/html/overview/module_architecture.html"),
    Path("docs/html/overview/pipeline_explainer.html"),
}


def test_docs_core_directories_exist() -> None:
    """팀 문서, 세부 문서, HTML 자료, LLM 문맥 디렉터리를 확인합니다."""
    required_dirs = [
        ROOT / "docs" / "team",
        ROOT / "docs" / "md",
        ROOT / "docs" / "html",
        ROOT / "docs" / "llm",
    ]

    missing = [str(path.relative_to(ROOT)) for path in required_dirs if not path.is_dir()]
    assert not missing, f"필수 문서 디렉터리가 없습니다: {missing}"


def test_key_directories_have_readme() -> None:
    required_dirs = [
        "app",
        "artifacts",
        "checkpoints",
        "configs",
        "configs/examples",
        "configs/examples/classification",
        "configs/experiments",
        "configs/experiments/rag",
        "configs/preprocess",
        "configs/smoke",
        "data",
        "docs",
        "docs/team",
        "docs/html",
        "docs/html/kickoff",
        "docs/html/overview",
        "docs/llm",
        "docs/md",
        "docs/md/data",
        "docs/md/experiments",
        "docs/md/overview",
        "docs/md/rag",
        "experiments",
        "models",
        "notebooks",
        "outputs",
        "reports",
        "scripts",
        "src",
        "src/models",
        "src/rag",
        "src/utils",
        "tests",
    ]

    missing = [
        directory
        for directory in required_dirs
        if not (ROOT / directory / "README.md").exists()
    ]
    assert not missing, f"README.md가 필요한 디렉터리에 없습니다: {missing}"


def test_html_docs_are_curated_explainers_only() -> None:
    """HTML 문서가 Markdown 백업본처럼 다시 불어나지 않도록 허용 목록을 확인합니다."""
    html_docs = {
        path.relative_to(ROOT)
        for path in (ROOT / "docs" / "html").rglob("*.html")
    }

    assert html_docs == ALLOWED_HTML_DOCS


def test_llm_prompts_preserve_langchain_harness_boundary() -> None:
    """LLM 요청 프롬프트가 LangChain 전환 후에도 산출물 계약을 먼저 설명하는지 확인합니다."""
    text = (ROOT / "docs" / "llm" / "TASK_PROMPTS.md").read_text(encoding="utf-8")
    required_phrases = [
        "LangChain 기반 RAG 실험/운영 harness",
        "프로젝트 표준 artifact",
        "retrieval_results.jsonl",
        "answers.jsonl",
        "metrics.json",
        "HTML은 모든 Markdown의 백업본이 아니라",
    ]

    missing = [phrase for phrase in required_phrases if phrase not in text]
    assert not missing, f"LLM 프롬프트 문서에 핵심 문구가 없습니다: {missing}"


def test_data_contract_is_rag_first() -> None:
    """데이터 계약 문서가 RAG 원본 문서와 평가 질문을 먼저 설명하는지 확인합니다."""
    text = (ROOT / "docs" / "md" / "data" / "DATA_CONTRACT.md").read_text(encoding="utf-8")
    required_phrases = [
        "# RAG Data Contract",
        "Raw Document",
        "Parsed Document",
        "Chunk 계약",
        "평가 질문 계약",
        "기존 분류 데이터 계약",
    ]

    missing = [phrase for phrase in required_phrases if phrase not in text]
    assert not missing, f"RAG 데이터 계약 문서에 핵심 문구가 없습니다: {missing}"
