# HTML 문서

`docs/html/`은 팀원 공유와 설명을 위한 HTML 문서를 두는 곳입니다.

## 문서 종류

- Markdown 원본에서 변환한 HTML 문서
- 직접 디자인한 설명용 HTML 문서

## 대응 규칙

`docs/md/*.md` 파일은 같은 이름의 HTML을 가집니다.

```text
docs/md/PIPELINE_OVERVIEW.md
-> docs/html/PIPELINE_OVERVIEW.html
```

## Markdown 대응 HTML

- `COLAB_GUIDE.html`
- `DATA_CONTRACT.html`
- `EXPERIMENT_GUIDE.html`
- `GIT_WORKFLOW.html`
- `KICKOFF_GUIDE.html`
- `MODULE_ARCHITECTURE.html`
- `PIPELINE_INFRA_CHECKLIST.html`
- `PIPELINE_OVERVIEW.html`
- `RAG_PIPELINE_SPEC.html`
- `ROLE_GUIDE.html`
- `TEAM_WORKFLOW.html`

추가로 아래 HTML은 설명용으로 직접 작성한 문서입니다.

- `pipeline_explainer.html`
- `module_architecture.html`
- `kickoff.html`
