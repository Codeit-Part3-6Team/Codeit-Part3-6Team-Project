# Data Engineer — 데이터 작업 가이드

DE는 VM에 있는 실제 RFP 문서를 확인하고, 평가용 질문셋을 만드는 역할입니다.

## 준비물 확인

- [ ] VM에 VS Code SSH로 접속할 수 있나요?
- [ ] `/shared/data/raw_docs/` 에 파일이 들어있나요?
- [ ] `conda activate codeit-ml-pipeline` 이 되나요?

하나라도 안 되면 PM에게 문의하세요.

## 데이터가 어디에 있는가

```
내 Google Drive                 VM (모든 팀원 공유)
┌────────────────────┐          ┌─────────────────────────────┐
│ codeit-project2/   │  rclone  │ /shared/data/raw_docs/      │
│ └── data/          │ ──pull──→│ ├── files/                   │
│     ├── files/     │          │ │   ├── 한영대학_xxx.hwp    │
│     │   ├── *.hwp  │          │ │   └── ... (46개 HWP)      │
│     │   └── *.pdf  │          │ ├── data_list.csv            │
│     └── data_list.  │          │ └── ... (4개 PDF)           │
│         csv         │          └─────────────────────────────┘
└────────────────────┘

~/project/                        ← 개인 git repo (코드)
└── notebooks/rag/                ← EDA/분석 노트북 여기에 만듦
```

**핵심:**
- `/shared/data/raw_docs/` 는 읽기 전용. 원본 절대 수정 금지
- `data_list.csv` 에 문서별 메타데이터(발주기관, 예산, 사업명 등)가 들어있음
- VS Code에서 `File > Add Folder to Workspace` → `/shared/data/raw_docs` 추가하면 사이드바에서 바로 탐색 가능

## DE가 해야 할 일

```
1. 데이터 현황 파악 (10분)
   ↓
2. data_list.csv 메타데이터 검증 (20분)
   ↓
3. 문서 본문 품질 확인 (20분)
   ↓
4. 평가 질문 CSV 작성 (집중 작업)
```

### 1. 데이터 현황 파악

VM 터미널에서 기본 통계 확인:

```bash
cd ~/project
conda activate codeit-ml-pipeline

# 전체 파일 개수
find /shared/data/raw_docs -type f | wc -l

# 포맷별 분포
find /shared/data/raw_docs -type f | sed 's/.*\.//' | sort | uniq -c | sort -rn

# 예상 출력:
#   46 hwp
#    4 pdf
#    1 csv
```

### 2. data_list.csv 검증

VS Code에서 새 노트북(`~/project/notebooks/rag/de_eda.ipynb`)을 만들어 확인:

```python
import pandas as pd

# CSV 읽기 (메타데이터)
df = pd.read_csv("/shared/data/raw_docs/data_list.csv", encoding="utf-8-sig")

# 기본 정보
df.info()
df.head()

# 컬럼 목록
print(df.columns.tolist())
# ['공고 번호', '공고 차수', '사업명', '사업 금액', '발주 기관', ...]

# 체크할 것들
df["발주 기관"].value_counts()       # 어떤 기관이 많은가
df["사업 금액"].describe()           # 예산 분포
df["텍스트"].str.len().describe()    # 본문 길이 분포 (너무 짧으면 깨진 문서)
df[df["텍스트"].str.len() < 100]     # 본문이 거의 없는 문서 (깨졌을 가능성)
```

### 3. 문서 품질 확인

```python
# 깨진 문서 의심 기준
short_docs = df[df["텍스트"].str.len() < 100]
print(f"본문 100자 미만: {len(short_docs)}건")
if len(short_docs) > 0:
    print(short_docs[["공고 번호", "사업명", "파일명"]])

# 빈 텍스트
empty_docs = df[df["텍스트"].isna() | (df["텍스트"].str.strip() == "")]
print(f"빈 문서: {len(empty_docs)}건")

# 중복 확인
dupes = df[df["공고 번호"].duplicated(keep=False)]
print(f"중복 공고번호: {len(dupes)}건")
```

발견한 이슈는 GitHub Issue에 기록:
```markdown
제목: [데이터] 본문 누락 문서 3건 발견
내용:
- 2024xxxx: 텍스트 컬럼 0자 (파일 깨짐 의심)
- 2024yyyy: 특수문자만 있음
```

### 4. 평가 질문 CSV 작성

**위치:** `/shared/data/eval_questions.csv`

**양식:**
```csv
question,expected_answer,expected_chunk_ids
"이 사업의 예산은 얼마인가?","130,000,000원",
"발주 기관은 어디인가?","한영대학",
"사업 기간은 어떻게 되는가?","계약일로부터 3개월",
```

**작성 방법:**
1. `data_list.csv`의 `사업 요약` 컬럼을 읽습니다
2. 각 RFP에서 뽑을 수 있는 질문을 생각합니다:
   - 예산은 얼마인가?
   - 발주 기관은?
   - 사업 기간은?
   - 주요 사업 내용은?
   - 입찰 방식은?
3. `사업 요약` 텍스트에서 정답을 찾아 `expected_answer`에 넣습니다
4. `expected_chunk_ids`는 **비워둡니다** (config 확정 전에는 정확한 chunk ID를 알 수 없음)

**목표: 50~100개 질문**

**팁:**
- 다양한 발주기관에서 골고루 질문을 만드세요
- 정답이 명확한 질문이 좋습니다 (예/아니오보다 구체적인 정보)
- 질문은 RFP 본문에서 찾을 수 있는 것만 만드세요 (외부 지식 X)
- VS Code에서 CSV 파일을 직접 열어서 편집할 수 있습니다 (`File > Open File`)

## CSV 저장 및 공유

```bash
# 작성이 끝나면 모든 팀원이 읽을 수 있게 권한 설정
chmod 644 /shared/data/eval_questions.csv

# EL이 실험할 때 이 파일을 config에서 가리킴:
# evaluation:
#   questions_path: /shared/data/eval_questions.csv
```

## 자주 하는 명령어

```bash
# 최신 데이터 가져오기 (PM이 Drive에 새로 올렸을 때)
bash ~/project/scripts/sync_data.sh pull

# 문서 개수 확인
find /shared/data/raw_docs -type f | wc -l

# 한글 깨짐 없이 CSV 미리보기
head -3 /shared/data/eval_questions.csv
```

## 문제가 생겼을 때

| 증상 | 확인/조치 |
|---|---|
| `/shared/data/raw_docs/` 비어있음 | PM에게 데이터 pull 요청 |
| CSV 읽기 실패 (Permission denied) | `chmod 644 /shared/data/eval_questions.csv` |
| 한글 깨짐 | VS Code에서 `Reopen with Encoding > UTF-8` |
| 문서 일부만 보임 | HWP 파싱 한계. 깨진 파일은 Issue에 기록만 하고 넘어감 |
