# HTML 문서

`docs/html/`은 팀원 공유와 설명을 위한 HTML 문서를 두는 곳입니다.

## 문서 종류

- Markdown 원본에서 변환한 HTML 문서
- 직접 디자인한 설명용 HTML 문서

## 대응 규칙

`docs/md/*.md` 파일은 같은 이름의 HTML을 가집니다.

```text
docs/md/overview/PIPELINE_OVERVIEW.md
-> docs/html/overview/PIPELINE_OVERVIEW.html
```

## Markdown 대응 HTML

- `overview/PIPELINE_OVERVIEW.html`
- `overview/PIPELINE_INFRA_CHECKLIST.html`
- `overview/MODULE_ARCHITECTURE.html`
- `rag/RAG_PIPELINE_SPEC.html`
- `data/DATA_CONTRACT.html`
- `experiments/EXPERIMENT_GUIDE.html`
- `experiments/COLAB_GUIDE.html`
- `workflow/GIT_WORKFLOW.html`
- `workflow/ROLE_GUIDE.html`
- `workflow/TEAM_WORKFLOW.html`
- `kickoff/KICKOFF_GUIDE.html`

추가로 아래 HTML은 설명용으로 직접 작성한 문서입니다.

- `overview/pipeline_explainer.html`
- `overview/module_architecture.html`
- `kickoff/kickoff.html`
