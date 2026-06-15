# RAG 상세 문서

RAG 입력/출력 계약, 문서 처리, 검색, 답변, 평가 기준을 설명하는 Markdown 문서를 둡니다.

## 포함 문서

| 문서 | 용도 |
| --- | --- |
| [RAG_PIPELINE_SPEC.md](RAG_PIPELINE_SPEC.md) | RAG 파이프라인의 모든 입출력 계약을 정의합니다. 문서 loader, chunk, embedding, retrieval, answer, citation, 평가 산출물의 형식과 계약을 명시합니다. |

## 언제 보는가

- RAG 산출물이 계약에 맞는지 확인할 때
- 새로운 config를 만들 때 어떤 필드가 필요한지 확인할 때
- retrieval이나 answer 결과가 예상과 다를 때 계약을 다시 확인할 때

## 팀원이 먼저 볼 문서

- 처음 시작할 때는 [docs/team/README.md](../../team/README.md)부터 봅니다.
- RAG 실행 방법은 [docs/md/experiments/EXPERIMENT_GUIDE.md](../experiments/EXPERIMENT_GUIDE.md)를 봅니다.
