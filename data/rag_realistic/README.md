# RAG Realistic Sample

`data/rag_realistic/`은 TXT 샘플보다 실제 프로젝트 입력에 가까운 RAG E2E 검증용 fixture입니다.

## 포함 파일

| 파일 | 용도 |
| --- | --- |
| `rfp_realistic_sample.docx` | Word 계열 문서 로딩 검증 |
| `rfp_realistic_sample.hwpx` | HWPX 계열 문서 로딩 검증 |
| `eval_questions.csv` | 검색, 답변, citation 평가 질문 |

이 문서는 외부 기관의 실제 RFP 원문이 아니라, 테스트를 위해 직접 만든 작은 준실제 샘플입니다. 실제 데이터가 들어오기 전에도 파일 포맷, chunk, retrieval, answer, evaluation 산출물 계약을 확인하는 용도로 사용합니다.

## 실행 Config

```bash
python scripts/check_rag_pipeline.py --config configs/experiments/rag/rag_realistic_docs.yaml --project-root .
python scripts/run_rag_ingest.py --config configs/experiments/rag/rag_realistic_docs.yaml --project-root .
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_realistic_docs.yaml --project-root . --evaluate
```

결과는 `experiments/rag_realistic_docs/` 아래에 생성됩니다.
