# Data Engineer — 데이터 관리 규칙

이 문서는 Data Engineer가 원본 RFP 문서를 수집·정리·공유하는 기준을 정리합니다.

## 데이터 보관 원칙

| 위치 | 용도 | 규칙 |
|---|---|---|
| **Google Drive** (`공유폴더/data/raw_docs/`) | **원본 정본**. 절대 직접 수정 금지 | PDF/HWP/HWPX 원본 그대로 업로드 |
| **GCP VM** (`data/raw_docs/`) | 실험용 사본. `sync_data.sh pull`로 가져옴 | VM 초기화되면 다시 pull |
| **GitHub** | 코드, Config, 문서만 | 원본 데이터 절대 금지 |

## Google Drive 폴더 구조

```
MyDrive/codeit_rag_project/
├── data/
│   ├── raw_docs/           ← 원본 RFP 문서 (DE가 여기에 업로드)
│   │   ├── rfp_001.pdf
│   │   ├── rfp_002.hwp
│   │   └── ...
│   ├── eval_questions.csv  ← 평가 질문 CSV (DE + Experiment Lead 협업)
│   └── data_list.csv       ← 제공된 메타데이터 (있는 경우)
├── experiments/            ← 실험 결과 백업 (자동)
├── reports/                ← 리포트 백업 (자동)
└── backups/                ← 수동 전체 백업
```

## DE 첫 주 작업 흐름

### 1. Drive에 원본 문서 업로드

코드잇에서 제공받은 RFP 문서 100건을 Drive의 `codeit_rag_project/data/raw_docs/` 폴더에 그대로 업로드합니다.

- 파일명은 원본 그대로 유지
- PDF, HWP, HWPX, DOCX 등 어떤 포맷이든 그대로
- 폴더 구조가 있다면 유지 (예: `raw_docs/2025/1분기/rfp_001.pdf`)

### 2. VM에 데이터 가져오기

```bash
# VM에서 한 번만 실행
bash scripts/sync_data.sh pull
```

이 명령어는 Drive → VM으로 모든 문서를 복사합니다.
문서가 추가될 때마다 다시 실행하면 새 문서만 가져옵니다.

### 3. 문서 로딩 확인

```bash
python scripts/check_rag_pipeline.py \
  --config configs/experiments/rag/rag_langchain.yaml \
  --project-root .
```

Config의 `paths.raw_docs_dir`가 Drive에서 pull한 경로를 가리키는지 확인하세요.
기본값은 `data/raw_docs`입니다.

### 4. 평가 질문 CSV 작성

[golden_dataset_guide.md](golden_dataset_guide.md)를 보고 평가 질문 CSV를 작성합니다.
완성된 CSV는 Drive에 올리고, 다시 `sync_data.sh pull`로 VM에 반영합니다.

CSV의 정확한 컬럼명과 형식은 [docs/md/data/DATA_CONTRACT.md](../md/data/DATA_CONTRACT.md)를 참고하세요.

## 자주 하는 명령어

```bash
# 새 문서 받아오기 (Drive → VM)
bash scripts/sync_data.sh pull

# 실험 결과 백업 (VM → Drive)
bash scripts/sync_data.sh push

# 문서 몇 개인지 확인
find data/raw_docs -type f | wc -l

# 어떤 파일 형식이 있는지 확인
find data/raw_docs -type f | sed 's/.*\.//' | sort | uniq -c
```

## 주의사항

- 원본 문서는 절대 VM에서 직접 수정하지 않습니다. 수정본이 필요하면 별도 폴더에 복사
- Drive 용량 확인: PDF 100건이어도 500MB 이하
- 파일명에 한글/공백/특수문자 있어도 됨 (pipeline이 처리)
- 깨진 문서(읽기 실패)가 있다면 Issue로 기록하고 공유
