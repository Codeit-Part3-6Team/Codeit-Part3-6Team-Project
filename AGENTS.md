# AGENTS.md

이 문서는 이 저장소에서 LLM 기반 코딩 에이전트가 작업할 때 먼저 읽어야 하는 운영 지침입니다.

## 프로젝트 한 줄 요약

이 저장소는 RFP/입찰 공고 문서를 읽고, chunk로 나누고, 관련 근거를 검색한 뒤, 답변과 citation을 함께 남기는 RAG 파이프라인 프로젝트입니다.

현재 목표는 config 기반 RAG 실험 파이프라인과 산출물 규칙을 안정적으로 준비하고, 실험으로 검증된 최적 설정을 바탕으로 RFP 문서 분석 서비스를 완성하는 것입니다.

## 반드시 지킬 원칙

- RAG 프로젝트를 기본 방향으로 봅니다. 분류/HuggingFace config와 모델은 참고 예제입니다.
- 실험 조건은 가능하면 코드가 아니라 `configs/`에서 조정합니다.
- 실행 진입점은 `scripts/`에 둡니다. `src/`는 재사용 가능한 구현체를 둡니다.
- 실험 산출물은 `experiments/`에 남깁니다.
- 공유용 요약과 리포트는 `reports/`에 남깁니다.
- 원본 데이터는 직접 수정하지 않습니다.
- 대용량 모델 weight, checkpoint, 원본 데이터, 임시 산출물은 Git에 올리지 않습니다.
- 팀원에게 처음 보여줄 문서는 `docs/team/`에서 확인합니다.
- 세부 참고 문서는 `docs/md/`에서 확인합니다.
- 설명용 HTML이 따로 있는 주제라면 `docs/html/`도 함께 확인합니다.
- public 함수와 클래스의 docstring은 한국어로 작성합니다.
- 주석은 처음 보는 팀원이 흐름을 이해하는 데 도움이 되는 위치에 짧게 남깁니다.

## 주요 경로

```text
configs/                 실험 조건과 실행 정책
configs/experiments/rag/ RAG 실험 config
configs/examples/        분류/HuggingFace 참고 config
scripts/                 사람이 실행하는 공식 명령
src/                     실제 구현 코드
src/rag/                 RAG 문서 처리, 검색, 답변, 평가 (README 참조)
experiments/             실험 산출물
reports/                 실험 요약과 팀 공유 자료
notebooks/               로컬/Colab 실험 템플릿
docs/team/               팀원이 처음 볼 킥오프, 운영, 역할 문서
docs/md/                 세부 참고 Markdown 문서
docs/html/               공유/설명용 HTML 문서
docs/llm/                LLM 작업용 컨텍스트 문서 (PROJECT_CONTEXT, ARCHITECTURE_MAP, TASK_PROMPTS, WORKFLOW_CHECKLIST)
docs/html/               공유/설명용 HTML 문서
docs/llm/                LLM 작업용 컨텍스트 문서
tests/                   단위 테스트와 smoke test
```

## 작업 전 확인

1. 현재 브랜치와 워킹트리를 확인합니다.
2. 관련 README를 먼저 읽습니다.
3. 팀 공유 문서 작업이면 `docs/team/README.md`를 확인합니다.
4. RAG 작업이면 `docs/llm/PROJECT_CONTEXT.md`, `docs/llm/ARCHITECTURE_MAP.md`, `docs/md/rag/RAG_PIPELINE_SPEC.md`를 확인합니다.
5. config 변경이면 `configs/README.md`와 관련 YAML을 확인합니다.
6. 실행 스크립트 변경이면 `scripts/README.md`와 `tests/test_scripts.py`를 확인합니다.

## 작업 후 확인

작업 범위에 맞춰 테스트를 실행합니다.

```bash
python -m pytest
```

RAG 파이프라인을 건드렸다면 아래 테스트를 우선 확인합니다.

```bash
python -m pytest tests/test_rag_pipeline.py tests/test_rag_validation.py tests/test_rag_adapters.py
```

## 자주 하는 실수

- `configs/experiments/rag/` 대신 예전 `configs/rag/` 경로를 사용하는 것
- `scripts/`에 비즈니스 로직을 많이 넣는 것
- `src/` 구현을 바꾸고 테스트나 README를 갱신하지 않는 것
- 실험 산출물을 Git에 추가하는 것
- RAG 답변만 보고 citation, retrieval 결과, failure artifact를 놓치는 것
- 팀원이 처음 볼 문서와 세부 참고 문서를 같은 위치에 섞어두는 것
