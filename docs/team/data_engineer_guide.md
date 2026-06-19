# Data Engineer — 데이터 작업 가이드

DE는 RFP 문서의 메타데이터를 검증하고, 평가용 질문셋을 만드는 역할입니다.
모든 작업은 **로컬 PC에서** 진행하며, 최종 결과물만 Drive로 공유합니다.

## 준비물

- [ ] PM에게 공유받은 Google Drive 폴더에 접근할 수 있나요?
- [ ] `data_list.csv` 를 로컬에 다운로드했나요?

## 데이터가 어디에 있는가

```
내 Google Drive (PM 계정)
└── codeit-project2/
    └── data/
        ├── files/              ← RFP 원본 문서 (HWP/PDF)
        └── data_list.csv       ← 메타데이터 (DE가 볼 메인 파일)
```

**핵심:**
- `data_list.csv` 를 로컬에 다운로드해서 작업합니다
- 작업이 끝나면 최종 CSV만 Drive에 다시 업로드
- VM에서 `sync_data.sh pull` 로 가져가서 실험에 사용

## DE가 해야 할 일

```
1. data_list.csv 다운로드 + 메타데이터 검증
   ↓
2. 문서 본문 품질 확인
   ↓
3. 평가 질문 CSV 작성 (집중 작업)
   ↓
4. 완성된 CSV를 Drive에 업로드
```

### 1. data_list.csv 검증

로컬에서 Python이나 Excel로 `data_list.csv`를 열어 확인:

```python
import pandas as pd

df = pd.read_csv("data_list.csv", encoding="utf-8-sig")

# 기본 정보
df.info()
print(df.columns.tolist())
# ['공고 번호', '공고 차수', '사업명', '사업 금액', '발주 기관', ...]

# 체크할 것들
df["발주 기관"].value_counts()       # 어떤 기관이 많은가
df["사업 금액"].describe()           # 예산 분포
df["텍스트"].str.len().describe()    # 본문 길이 분포 (너무 짧으면 깨진 문서)
df[df["텍스트"].str.len() < 100]     # 본문이 거의 없는 문서 (깨졌을 가능성)
```

### 2. 문서 품질 확인

```python
# 깨진 문서 의심 기준
short_docs = df[df["텍스트"].str.len() < 100]
print(f"본문 100자 미만: {len(short_docs)}건")

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

### 3. 평가 질문 CSV 작성

**최종 파일명:** `eval_questions.csv`

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
- Excel이나 VS Code에서 직접 CSV를 편집할 수 있습니다

### 4. 완성된 CSV 공유

완성된 `eval_questions.csv`를 PM의 Google Drive에 업로드:
- 경로: `codeit-project2/data/`
- PM이 VM에서 `bash scripts/sync_data.sh pull` 로 가져갑니다

EL이 실험할 때 config에서 이 경로를 사용합니다:
```yaml
evaluation:
  questions_path: /shared/data/eval_questions.csv
```

## 문제가 생겼을 때

| 증상 | 확인/조치 |
|---|---|
| Google Drive 접근 불가 | PM에게 공유 권한 요청 |
| CSV 인코딩 깨짐 | UTF-8(BOM)으로 저장 (`utf-8-sig`) |
| 한글 깨짐 | VS Code에서 `Reopen with Encoding > UTF-8` |
| 문서 일부만 보임 | HWP 파싱 한계. 깨진 파일은 Issue에 기록만 하고 넘어감 |
