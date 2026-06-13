## 변경 개요

이 PR에서 무엇을 바꿨는지 한 문장으로 요약해 주세요.

-

## 변경 유형

- [ ] 코드 / RAG 파이프라인
- [ ] Config / 실행 스크립트
- [ ] 데이터 / EDA / 전처리
- [ ] Notebook
- [ ] 문서
- [ ] GitHub 운영 / 템플릿
- [ ] 버그 수정 / 리팩토링

## 확인한 것

- [ ] 필요한 테스트 또는 실행 확인을 했습니다.
- [ ] config 변경 시 프로젝트 루트 기준 상대 경로가 동작하는지 확인했습니다.
- [ ] RAG 변경 시 retrieval / answer / citation 중 영향 범위를 확인했습니다.
- [ ] 데이터, API key, 대용량 산출물, 임시 파일이 커밋에 포함되지 않았습니다.
- [ ] 문서 업데이트 필요 여부를 확인했습니다.

## 실행 / 검증 결과

실행한 명령, 노트북, 또는 확인 방법을 적어 주세요.

```bash
# 예시
python -m pytest
python scripts/check_rag_pipeline.py --config configs/experiments/rag/rag_langchain.yaml --project-root .
```

- 실행 환경: 로컬 / WSL / Colab / 기타
- 사용 config:
- 산출물 경로:

## 실험 결과 / 산출물

RAG 품질이나 데이터 변경에 영향이 있을 때만 작성합니다. 해당 없으면 `해당 없음`으로 남겨 주세요.

- 주요 결과:
- 확인한 산출물:
- 관련 Issue / Discussion / Daily Report:

## 리뷰어가 봐야 할 부분

특히 봐줬으면 하는 부분, 고민 중인 선택지, 아직 확신이 없는 부분을 적어 주세요.

-
