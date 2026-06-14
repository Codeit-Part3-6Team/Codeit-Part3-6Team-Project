# Classification Fixture

이 디렉터리는 기존 분류/HuggingFace 파이프라인과 smoke test를 보존하기 위한 참고 데이터입니다.

## 구조

```text
classification/
|-- image_processed/  # 작은 PPM 이미지와 train/valid/test CSV
`-- text_processed/   # 작은 텍스트 분류 CSV와 샘플 txt
```

현재 프로젝트의 기본 방향은 RAG입니다. 새 팀원에게는 이 데이터를 메인 예제로 안내하지 않고, RAG 문서 fixture인 `data/rag_sample/`과 `data/rag_realistic/`을 먼저 안내합니다.
