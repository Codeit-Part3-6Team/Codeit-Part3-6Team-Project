# LLM Workflow Checklist

## 작업 전

- [ ] 현재 브랜치를 확인합니다.
- [ ] 워킹트리가 깨끗한지 확인합니다.
- [ ] 관련 README를 읽습니다.
- [ ] RAG 작업이면 `docs/md/rag/RAG_PIPELINE_SPEC.md`를 확인합니다.
- [ ] config 작업이면 `configs/README.md`를 확인합니다.
- [ ] 실행 스크립트 작업이면 `scripts/README.md`를 확인합니다.
- [ ] 테스트 파일 위치를 확인합니다.

## 작업 중

- [ ] config로 조정할 수 있는 값인지 먼저 판단합니다.
- [ ] `scripts/`에는 얇은 CLI만 둡니다.
- [ ] 실제 로직은 `src/`에 둡니다.
- [ ] 실패 시 `run_status.json`이나 `failure.log` 같은 artifact 흐름이 깨지지 않는지 확인합니다.
- [ ] RAG 작업에서는 answer뿐 아니라 retrieval result와 citation도 확인합니다.
- [ ] public 함수/클래스에는 한국어 docstring을 둡니다.
- [ ] 처음 보는 팀원을 위한 짧은 주석이 필요한지 확인합니다.

## 작업 후

- [ ] 관련 테스트를 실행합니다.
- [ ] README 또는 `docs/md/` 갱신이 필요한지 확인합니다.
- [ ] HTML 설명 문서와 대응되는 내용이면 `docs/html/`도 확인합니다.
- [ ] 실험 산출물, 모델 weight, 원본 데이터가 Git에 들어가지 않았는지 확인합니다.
- [ ] 변경 내용을 커밋 단위로 분리할 수 있는지 확인합니다.

## 테스트 선택 기준

| 변경 범위 | 권장 테스트 |
| --- | --- |
| 문서만 변경 | `python -m pytest tests/test_docs_structure.py` |
| config 경로/계약 | `python -m pytest tests/test_config.py tests/test_rag_validation.py` |
| scripts 변경 | `python -m pytest tests/test_scripts.py` |
| RAG 구현 변경 | `python -m pytest tests/test_rag_pipeline.py tests/test_rag_adapters.py tests/test_rag_document_loader.py` |
| 모델/학습 변경 | `python -m pytest tests/test_models.py tests/test_pipeline_smoke.py` |
| 노트북 변경 | `python -m pytest tests/test_notebooks.py` |
| 넓은 변경 | `python -m pytest` |

## 커밋 전 확인 문장

커밋 메시지를 쓰기 전에 아래 문장을 스스로 채웁니다.

```text
이번 변경은 무엇을 가능하게 하는가?
어떤 파일을 주로 바꿨는가?
어떤 테스트로 확인했는가?
문서나 config 경로도 같이 갱신했는가?
```

