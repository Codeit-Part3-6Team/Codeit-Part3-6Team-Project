# 팀 공유 설명 흐름

이 문서는 팀원에게 프로젝트를 처음 설명할 때 사용할 설명 순서입니다.

## 설명 목표

- 비전공자도 RAG 프로젝트의 목적을 이해합니다.
- 팀원이 자신이 맡을 역할과 첫 작업을 이해합니다.
- 파이프라인, 문서, 실험 산출물이 왜 필요한지 납득합니다.
- 킥오프 이후 바로 Issue와 Kanban으로 작업을 시작할 수 있습니다.

## 설명 순서

1. 문제 상황
   - RFP/입찰 문서는 길고, 필요한 정보를 찾기 어렵습니다.
   - 우리는 문서를 검색하고 근거와 함께 답하는 RAG 파이프라인을 준비합니다.

2. RAG를 쉬운 말로 설명
   - 문서를 작은 조각으로 나눕니다.
   - 질문과 관련 있는 조각을 찾습니다.
   - 찾은 조각을 근거로 답변합니다.
   - 답변에는 citation을 함께 남깁니다.

3. 현재 준비된 것
   - 문서 loader: txt, pdf, docx, hwpx, hwp
   - chunking, embedding, retrieval, answer, evaluation 흐름
   - config 기반 실험 실행
   - 실험 산출물과 실패 로그
   - local/Colab 노트북 템플릿

4. 아직 나중에 붙일 것
   - 실제 외부 RFP 문서 검증
   - FAISS/Chroma/Elasticsearch 같은 저장형 검색 인프라
   - OpenAI/Ollama answerer
   - API 또는 웹앱 데모

5. 역할별 첫 책임
   - PM: 일정, 보드, 의사결정, merge 기준
   - Data Engineer: 실제 데이터 후보, 데이터 계약, 평가 질문
   - Experiment Lead: config 실험, metric 해석, 결과 비교
   - Application Engineer: 입출력 계약, 데모/API 후보
   - Presentation Lead: 설명 자료, 용어 정리, 발표 흐름

6. 첫 주 작업 방식
   - 모든 작업은 Issue로 시작합니다.
   - 진행 상황은 Kanban에서 이동합니다.
   - 막힌 점은 Daily Report에 남깁니다.
   - PR에는 테스트 결과와 산출물 경로를 남깁니다.

## 설명할 때 피할 것

- 처음부터 모델 성능 수치만 강조하지 않습니다.
- FastAPI나 앱 구현을 최종 목표처럼 설명하지 않습니다.
- RAG 용어를 정의 없이 계속 사용하지 않습니다.
- 실제 데이터가 없는 상태에서 parser 품질을 확정된 것처럼 말하지 않습니다.

## 함께 열어두면 좋은 문서

- `docs/html/overview/pipeline_explainer.html`
- `docs/html/overview/module_architecture.html`
- `docs/md/workflow/FIRST_WEEK_KANBAN.md`
- `docs/md/workflow/GITHUB_OPERATIONS.md`
- `docs/md/rag/RAG_PIPELINE_SPEC.md`
