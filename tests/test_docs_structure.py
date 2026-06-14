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
        "data",
        "data/examples",
        "data/examples/classification",
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
        "rag_realistic_docs.yaml",
        "retrieval_results.jsonl",
        "answers.jsonl",
        "metrics.json",
        "HTML은 모든 Markdown의 백업본이 아니라",
    ]

    missing = [phrase for phrase in required_phrases if phrase not in text]
    assert not missing, f"LLM 프롬프트 문서에 핵심 문구가 없습니다: {missing}"


def test_llm_context_mentions_realistic_rag_e2e_config() -> None:
    """LLM 작업 문서가 준실제 RFP 포맷 검증 config를 안내하는지 확인합니다."""
    context = (ROOT / "docs" / "llm" / "PROJECT_CONTEXT.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs" / "llm" / "ARCHITECTURE_MAP.md").read_text(encoding="utf-8")
    checklist = (ROOT / "docs" / "llm" / "WORKFLOW_CHECKLIST.md").read_text(encoding="utf-8")

    for text in [context, architecture, checklist]:
        assert "rag_realistic_docs.yaml" in text
        assert "DOCX/HWPX" in text


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


def test_rag_pipeline_spec_matches_langchain_runtime_boundary() -> None:
    """RAG 스펙이 현재 LangChain/vector store 구현 상태를 모호하게 설명하지 않는지 확인합니다."""
    text = (ROOT / "docs" / "md" / "rag" / "RAG_PIPELINE_SPEC.md").read_text(encoding="utf-8")
    required_phrases = [
        "`vector_store.type: memory`",
        "`vector_store.type: chroma`",
        "FAISS와 Elasticsearch는 아직 확장 후보",
        "`rag.retriever.method`: `similarity` for LangChain",
        "`rag.answerer.provider`: `local`, `openai`, `ollama` in LangChain runtime",
    ]
    forbidden_phrases = [
        "별도 vector DB/index는 아직 만들지 않고",
        "Chroma 후보",
        "index_dir:",
        "retriever:\n    method: semantic\n    top_k: 5",
        "reranker:\n    enabled: true",
    ]

    missing = [phrase for phrase in required_phrases if phrase not in text]
    forbidden = [phrase for phrase in forbidden_phrases if phrase in text]
    assert not missing, f"RAG 스펙에 현재 구현 상태 핵심 문구가 없습니다: {missing}"
    assert not forbidden, f"RAG 스펙에 오래되었거나 혼동되는 문구가 남아 있습니다: {forbidden}"


def test_root_readme_is_rag_first() -> None:
    """GitHub 첫 화면이 RAG 실행과 산출물 계약을 먼저 보여주는지 확인합니다."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    required_phrases = [
        "# RAG 기반 RFP 문서 분석 파이프라인",
        "raw docs -> chunk -> embedding/index -> retrieve -> answer -> citation/evaluate",
        "## 기본 RAG 실행",
        "## RAG 산출물 계약",
        "## 참고: 기존 ML/HuggingFace 예제",
    ]
    missing = [phrase for phrase in required_phrases if phrase not in text]
    assert not missing, f"README에 RAG-first 핵심 문구가 없습니다: {missing}"

    reference_index = text.index("## 참고: 기존 ML/HuggingFace 예제")
    first_training_reference = min(
        (text.find(phrase) for phrase in ["일반 ML", "epoch", "fine-tuning"] if text.find(phrase) != -1),
        default=-1,
    )
    assert first_training_reference == -1 or first_training_reference > reference_index


def test_default_requirements_exclude_conflicting_optional_huggingface_langchain() -> None:
    """기본 requirements가 현재 RAG E2E 환경에서 충돌나는 optional HF integration을 포함하지 않는지 확인합니다."""
    text = (ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert "langchain-huggingface" not in text
