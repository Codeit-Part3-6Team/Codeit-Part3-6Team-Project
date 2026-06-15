# HTML Docs

`docs/html/`은 발표와 설명에 바로 쓰는 HTML만 둡니다.

Markdown 문서를 HTML로 전부 백업하지 않습니다. 세부 계약, 실험 방법, config 설명은 `docs/md/`와 `configs/`의 Markdown을 원본으로 관리합니다.

## 남기는 HTML

| 문서 | 용도 |
| --- | --- |
| `kickoff/kickoff.html` | 킥오프에서 프로젝트와 역할을 설명할 때 |
| `overview/pipeline_explainer.html` | 팀원에게 RAG 파이프라인 흐름을 빠르게 설명할 때 |
| `overview/module_architecture.html` | 모듈 관계와 RAG 흐름을 다이어그램으로 보여줄 때 |

## HTML로 만들지 않는 것

- config 설명
- RAG 입출력 계약
- 데이터 계약
- 실험 실행 가이드
- GCP VM 설정 가이드
- 인프라 체크리스트

위 문서들은 바뀔 가능성이 높으므로 Markdown 원본만 유지합니다.
