# HTML Docs Mind Map

`docs/html/`은 팀원 설명, 킥오프, 발표, 브라우저 공유에 쓰는 HTML 문서 모음입니다.

## 한눈에 보기

```text
HTML Docs
|-- overview/      큰 그림과 모듈 구조
|-- rag/           RAG 파이프라인 계약
|-- experiments/   실험 실행과 Colab
|-- data/          데이터 계약
|-- workflow/      Git, 역할, 팀 운영
`-- kickoff/       킥오프 설명 자료
```

## 추천 진입점

- `overview/pipeline_explainer.html`: 처음 보는 팀원에게 설명할 때
- `overview/module_architecture.html`: 모듈과 RAG 흐름을 다이어그램으로 설명할 때
- `overview/PIPELINE_OVERVIEW.html`: 전체 실행 구조를 설명할 때
- `rag/RAG_PIPELINE_SPEC.html`: RAG 입력/출력 계약을 확인할 때
- `experiments/EXPERIMENT_GUIDE.html`: 실험 실행 방법을 확인할 때
- `kickoff/kickoff.html`: 킥오프 발표 자료로 사용할 때

## Markdown 대응 규칙

`docs/md/`의 Markdown 문서는 같은 상대 경로의 HTML 문서를 가집니다.

```text
docs/md/overview/PIPELINE_OVERVIEW.md
-> docs/html/overview/PIPELINE_OVERVIEW.html
```
