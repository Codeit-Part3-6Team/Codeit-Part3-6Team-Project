# Data Engineer — 데이터 관리 규칙

이 문서는 Data Engineer가 원본 RFP 문서를 확인·검증·정리하는 기준을 정리합니다.

## 데이터 보관 원칙

| 위치 | 용도 | 규칙 |
|---|---|---|
| **Codeit 제공 Drive** (`원본데이터/`) | **원본 정본**. 읽기 전용 | PDF/HWP/HWPX 100건 + data_list.csv |
| **GCP VM** (`/shared/data/raw_docs/`) | 실험용 사본. `sync_data.sh pull`로 가져옴 | VM 초기화되면 다시 pull |
| **우리 Drive** (PM 계정) | 실험 결과 백업 | `sync_data.sh push` (자동) |
| **GitHub** | 코드, Config, 문서만 | 원본 데이터 절대 금지 |

## Google Drive 폴더 구조

```
Codeit 제공 Drive                     우리 Drive (백업)
┌──────────────────┐           ┌────────────────────────┐
│ 원본데이터/      │           │ codeit_rag_project/    │
│   data_list.csv  │           │ ├── experiments/       │
│   *.pdf, *.hwp   │           │ └── reports/           │
└──────┬───────────┘           └────────────────────────┘
       │ rclone copy                  ▲
       ▼                              │ rclone sync (crontab)
┌──────────────────┐           ┌──────┴─────────────────┐
│ /shared/data/    │           │ ~/project/             │
│   raw_docs/      │           │   experiments/         │
│ (VM 공유 사본)    │           │   reports/             │
└──────────────────┘           └────────────────────────┘
```

## DE 첫 주 작업 흐름

### 1. 데이터 확인 (Codeit 제공 Drive)

코드잇에서 제공한 원본데이터 폴더를 확인합니다:
- 문서 총 개수, 포맷별 분포 (PDF/HWP/HWPX)
- `data_list.csv` 컬럼 확인 (발주기관, 사업명, 예산 등)

### 2. VM에 데이터 가져오기

```bash
# Codeit Drive → VM으로 복사 (rclone config 필요)
bash scripts/sync_data.sh pull
```

VM의 `/shared/data/raw_docs/`에 모든 문서가 복사됩니다.

### 3. 문서 로딩 확인

```bash
python scripts/check_rag_pipeline.py \
  --config configs/experiments/rag/rag_langchain.yaml \
  --project-root .
```

Config의 `paths.raw_docs_dir`가 `/shared/data/raw_docs`를 가리키는지 확인하세요.

### 4. 평가 질문 CSV 작성

[golden_dataset_guide.md](golden_dataset_guide.md)를 보고 평가 질문 CSV를 작성합니다.
완성된 CSV는 VM의 `/shared/data/eval_questions.csv`에 두고 Config에서 참조합니다.

CSV의 정확한 컬럼명과 형식은 [docs/md/data/DATA_CONTRACT.md](../md/data/DATA_CONTRACT.md)를 참고하세요.

## 자주 하는 명령어

```bash
# 새 문서 받아오기 (Drive → VM)
bash scripts/sync_data.sh pull

# 실험 결과 백업 (VM → Drive)
bash scripts/sync_data.sh push

# 문서 몇 개인지 확인
find /shared/data/raw_docs -type f | wc -l

# 어떤 파일 형식이 있는지 확인
find /shared/data/raw_docs -type f | sed 's/.*\.//' | sort | uniq -c
```

## 주의사항

- 원본 문서는 절대 VM에서 직접 수정하지 않습니다. 수정본이 필요하면 별도 폴더에 복사
- Drive 용량 확인: PDF 100건이어도 500MB 이하
- 파일명에 한글/공백/특수문자 있어도 됨 (pipeline이 처리)
- 깨진 문서(읽기 실패)가 있다면 Issue로 기록하고 공유
