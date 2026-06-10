# Docs 디렉터리

`docs/`는 프로젝트 설명과 팀 운영 문서를 관리하는 곳입니다.

## 구조

```text
docs/
|-- md/      # 원본/관리용 Markdown 문서
`-- html/    # 공유/설명용 HTML 문서
```

Markdown 문서는 수정과 리뷰가 쉬운 원본입니다.
HTML 문서는 팀원에게 공유하거나 발표/킥오프에서 보여주기 위한 문서입니다.

## 원칙

- 새 문서를 만들 때는 가능하면 `docs/md/`에 Markdown 원본을 먼저 둡니다.
- 팀 공유용 문서는 `docs/html/`에 같은 주제의 HTML을 둡니다.
- README의 링크가 깨지지 않도록 파일 이동 시 함께 수정합니다.

## 대표 HTML 문서

- `html/pipeline_explainer.html`: 처음 보는 팀원을 위한 쉬운 파이프라인 설명
- `html/module_architecture.html`: 모듈 관계와 RAG 구조 다이어그램
- `html/kickoff.html`: 킥오프 설명용 문서
