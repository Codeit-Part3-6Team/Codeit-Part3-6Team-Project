# Data 디렉터리

`data/`는 RAG 프로젝트에서 사용할 원본 문서, 샘플 fixture, 평가 질문을 관리하는 곳입니다.

현재 메인 데이터는 RFP/입찰 문서 RAG 흐름을 확인하기 위한 `rag_sample/`과 `rag_realistic/`입니다. 기존 분류 파이프라인 검증용 데이터는 `examples/classification/` 아래에 참고 fixture로만 둡니다.

## 구조

```text
data/
|-- raw/                         # 실제 원본 문서. Git에 올리지 않음
|-- interim/                     # 중간 변환 결과. Git에 올리지 않음
|-- external/                    # 외부 참고 데이터. 출처와 라이선스 확인 필요
|-- rag_sample/                  # 기본 RAG 실행용 TXT 샘플과 평가 질문
|-- rag_realistic/               # DOCX/HWPX 준실제 RFP fixture와 평가 질문
`-- examples/
    `-- classification/          # 예전 분류 smoke test용 참고 fixture
```

## RAG 데이터

| 경로 | 용도 | Git 포함 여부 |
| --- | --- | --- |
| `rag_sample/` | `rag_langchain.yaml` 기본 실행용 작은 TXT fixture | 포함 |
| `rag_realistic/` | DOCX/HWPX 문서 포맷과 artifact 점검용 fixture | 포함 |
| `raw/` | 실제 외부 RFP 원문 | 제외 |
| `interim/` | 파싱, 변환 중간 결과 | 제외 |
| `external/` | 외부에서 받은 참고 데이터 | 기본 제외 |

실제 RFP 원문은 크기, 라이선스, 개인정보 여부를 확인한 뒤 별도 스토리지나 Drive로 관리합니다. Git에는 재현 가능한 작은 fixture와 평가 질문만 남깁니다.

## 평가 질문

RAG 평가 질문은 CSV로 관리합니다.

```text
question,expected_answer,expected_chunk_ids
```

질문은 답변만 맞추기 위한 것이 아니라, retrieval이 정답 근거 chunk를 찾는지 확인하기 위한 기준입니다.

## 참고 fixture

`examples/classification/` 아래 데이터는 현재 RAG 프로젝트의 메인 데이터가 아닙니다.

이 데이터는 `src/train.py`, `src/predict.py`, `src/validate_data.py`와 artifact 정책 테스트를 보존하기 위한 작은 fixture입니다. 새 RAG 작업을 시작할 때는 이 경로가 아니라 `rag_sample/`, `rag_realistic/`, 실제 외부 RFP 원문 위치를 먼저 봅니다.
