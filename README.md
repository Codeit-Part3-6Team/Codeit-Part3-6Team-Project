# 📄 입찰메이트 — RAG 기반 RFP 입찰 분석 서비스

공공입찰 제안요청서(RFP)에서 **핵심 정보를 요약하고, 질문에 대한 답변과 출처를 함께 제공하는** 문서 분석 서비스입니다.

긴 입찰 문서를 일일이 읽어야 하는 담당자를 위해, 내부 문서 검색부터 요구사항 확인, 근거 기반 질의응답까지 하나의 Streamlit 앱으로 연결했습니다. 검색·답변 품질은 config 기반 RAG 실험 파이프라인에서 비교하고 검증합니다.

> **기간**: 2026-06-17 ~ 2026-07-08<br>
> **주제**: B2G 입찰지원 컨설팅을 위한 RFP 문서 분석 및 질의응답

---

## 팀 구성

| 이름 | 역할 | 담당 |
| --- | --- | --- |
| 윤승준 | PM (Project Manager) | 서비스 기획, 프로젝트 방향 설정, 팀 협업 관리 |
| 정승호 | DE (Data Engineer) | 원본 문서·메타데이터 검증, 텍스트 복원, 평가 질문셋 제작 |
| 유수빈 | EL (Experiment Lead) | RAG 실험 설계·실행, 검색·답변 품질 개선, 성능 지표 비교 |
| 정진우 | PL (Presentation Lead) | Streamlit 프론트엔드 구현, 데모 구성, 최종 발표·보고서 |

---

## 팀 보고서 📊

[종합보고서 PDF](reports/6팀_중급프로젝트_종합보고서.pdf) · [종합보고서 Markdown](reports/final_report.md)

데이터 정제, 청킹 개선, 평가셋 구축, RAG 튜닝, 서비스 구현 과정과 한계를 정리했습니다.

---

## 협업일지 및 팀 일간 보고서 📄

[GitHub Discussions 바로 가기](https://github.com/Codeit-Part3-6Team/Codeit-Part3-6Team-Project/discussions)

---

## 주요 기능

| 기능 | 내용 |
| --- | --- |
| 내부 RFP 문서 검색 | 미리 인덱싱한 문서 목록에서 분석할 공고 검색·선택 |
| 단일 공고 분석 | 핵심 요약, 참가 자격·제출 서류 등 요구사항, 확인된 사업 정보 표시 |
| 문서 기반 채팅 | 선택한 문서 범위에서 후속 질문 처리, 답변과 근거 출처(citation) 제공 |
| 실험·평가 | config별 검색 결과, 답변, 출처, 성능 지표와 실패 사례 저장 |

현재 시연 앱은 **내부 문서 목록에서 한 건을 선택해 분석하는 흐름**을 제공합니다. 여러 공고 비교·추천과 참여 리스크 판단의 화면 연결, 평가표·배점표 포맷팅, 사업기간·제출마감 추출 정밀화는 후속 개선 과제입니다.

---

## 프로젝트 파이프라인

```text
1. 문서 준비 및 인덱싱
   입력: 공공조달 RFP 원문(HWP·PDF)과 메타데이터
   처리: 텍스트 추출·복원 → 중복·결측 정리 → 청킹 → 임베딩·인덱스 생성
   출력: 검색 가능한 문서 조각(chunk)과 문서 메타데이터

        ↓ 내부 문서 검색·선택

2. 검색 및 답변 생성
   입력: 선택한 문서와 사용자 질문
   검색: 의미 검색 + BM25 → RRF 순위 결합 → Cross-Encoder 재정렬
   출력: 핵심 요약·요구사항 또는 질문에 대한 답변 + 근거 출처

        ↓ 품질 확인

3. 평가 및 실험 기록
   평가: 정답 근거 검색 여부, 출처 정확도, 답변 정확도
   기록: 실행 config, 검색 결과, 답변, 지표, 실패 사례
```

실험 조건은 YAML config로 관리하며, 실행 결과는 `experiments/` 아래에 남깁니다. 상세 구조는 [RAG 파이프라인 명세](docs/md/rag/RAG_PIPELINE_SPEC.md)에서 확인할 수 있습니다.

---

## 기술 스택

| 구분 | 사용 기술 |
| --- | --- |
| 언어·환경 | Python 3.11, conda, GCP VM |
| RAG 프레임워크 | LangChain, 프로젝트 자체 실험·평가 파이프라인 |
| 임베딩 | OpenAI `text-embedding-3-small` |
| 검색·재정렬 | BM25 + 의미 검색, RRF, `BAAI/bge-reranker-v2-m3` |
| 답변 생성 | 실험: OpenAI `gpt-5-mini` / Streamlit 서비스 설정: Ollama `exaone3.5:7.8b` |
| 저장소 | ChromaDB(서비스 문서 검색), SQLite(실행 정보·문서 목록·대화 기록) |
| 웹 UI | Streamlit |

최종 RAG 실험 설정은 [`config_final.yaml`](configs/experiments/rag/config_final.yaml), 앱 실행 설정은 [`streamlit.yaml`](configs/experiments/rag/streamlit.yaml)에서 관리합니다.

---

## 데이터 및 실험 결과

- **원본 문서**: 공공조달 RFP 100건(HWP 96건, PDF 4건)에서 중복을 제거해 98건으로 정리
- **검색 데이터**: 텍스트 복원, 목차 노이즈 제거, 메타데이터 보강 후 14,717개 청크 구성
- **평가셋**: 발주기관·예산·일정·자격·제출서류 질문을 검수해 최종 370문항 구축

아래는 **v12mini 50문항, `top_k=15`, reranker 활성화, `gpt-5-mini` 답변 생성** 조건의 보고서 기록입니다.

| 지표 | 결과 |
| --- | --- |
| 정답 근거 검색률 (`retrieval_hit`) | 96% |
| 첫 번째 검색 결과 정답률 (`hit@1`) | 80% |
| 출처 정확도 (`citation`) | 92% |
| LLM 평가 기반 답변 정확도 (`judge_correct`) | 80% |

전체 370문항이나 Ollama 기반 앱의 성능을 뜻하지 않습니다. 평가셋 버전별 비교와 채택·기각한 실험은 [종합보고서의 RAG 실험 결과](reports/final_report.md#6-rag-실험-및-하이퍼파라미터-튜닝)를 참고하세요.

---

## 프로젝트 구조

```text
Codeit-Part3-6Team-Project/
├── app/                    # Streamlit 서비스
│   ├── views/              # 문서 검색·분석·채팅 화면
│   ├── services/           # UI와 RAG 연결, 실행·대화 기록 관리
│   └── examples/           # 내부 문서 인덱싱·연동 예제
├── configs/                # YAML 기반 실험·서비스 설정
│   └── experiments/rag/    # RAG·Agent·Streamlit config
├── data/                   # 작은 샘플 문서·평가 질문
├── docs/                   # 팀 운영·설계·구현 문서
│   ├── team/               # 킥오프, 역할, 일정, 협업 가이드
│   ├── md/                 # RAG·데이터·실험 상세 명세
│   └── llm/                # 코딩 에이전트용 프로젝트 맥락
├── notebooks/              # RAG 실행·결과 비교 노트북
├── src/rag/                # 문서 로딩, 검색, 답변, Agent, 평가 구현
├── scripts/                # RAG 실행·점검·비교 명령
├── experiments/            # 실험별 config·검색 결과·답변·지표
├── reports/                # 종합보고서·실험 요약·공유 자료
└── tests/                  # 단위·통합 테스트
```

원본 RFP 데이터와 대용량 모델·인덱스·임시 산출물은 Git에 포함하지 않습니다.

---

## 환경 설정

### 사전 요구사항

- Python 3.11, conda 권장
- 실제 서비스 연결 시 OpenAI API 키와 Ollama 서버 필요
- reranker·로컬 LLM을 사용하는 서비스 환경은 GPU 사용 권장

### 설치

```bash
git clone https://github.com/Codeit-Part3-6Team/Codeit-Part3-6Team-Project.git
cd Codeit-Part3-6Team-Project

conda env create -f environment.yml
conda activate codeit-ml-pipeline
```

`environment.yml`은 Python 환경 생성과 `requirements.txt` 설치를 함께 수행합니다. 이미 Python 3.11 환경이 있다면 `pip install -r requirements.txt`로 의존성을 설치합니다.

---

## 재현 방법

### 1. 로컬 샘플로 RAG 흐름 확인

저장소에 포함된 TXT 문서와 평가 질문을 사용합니다. `rag_keyword.yaml`은 외부 API·모델 서버 없이 실행하는 로컬 키워드 검색 예제입니다.

```bash
# 설정·입력 경로 점검
python scripts/check_rag_pipeline.py --config configs/experiments/rag/rag_keyword.yaml --project-root .

# 문서 로딩·청킹·인덱싱
python scripts/run_rag_ingest.py --config configs/experiments/rag/rag_keyword.yaml --project-root .

# 질문에 대한 답변과 출처 확인
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_keyword.yaml --project-root . --question "예산이 얼마야?"

# 샘플 평가 질문 실행
python scripts/run_rag_chat.py --config configs/experiments/rag/rag_keyword.yaml --project-root . --evaluate
```

결과는 `experiments/rag_keyword/`에 저장됩니다. `answers.jsonl`에서 답변·출처를, `metrics.json`과 실패 분석 CSV에서 품질을 확인합니다.

LangChain 기본 예제는 `configs/experiments/rag/rag_langchain.yaml`을 사용합니다. 이 파일의 `paths.raw_docs_dir`은 VM 경로(`/shared/data/raw_docs`)이므로, 로컬 샘플로 실행하려면 `data/rag_sample`로 변경합니다.

### 2. 실제 내부 문서로 Streamlit 서비스 실행

팀의 원본 데이터는 별도로 준비해야 합니다. 현재 서비스 config는 `data_list_v5.csv`를 입력으로 사용하며, OpenAI 임베딩·Ollama 답변 생성·HuggingFace reranker를 사용합니다.

아래 명령은 **Linux/GCP VM의 Bash 기준**입니다. Ollama 서버를 실행한 상태에서 진행합니다.

```bash
export OPENAI_API_KEY="<OpenAI API 키>"
export RAG_STREAMLIT_EXPERIMENTS="./experiments/streamlit"

ollama pull exaone3.5:7.8b

# data_list_v5.csv가 있는 팀 데이터 디렉터리 인덱싱
python app/examples/build_internal_corpus.py --raw-docs-dir /shared/data/raw_docs
python app/examples/list_corpus_runs.py

# 위 명령에서 확인한 준비 완료 run_id 지정
export RAG_CORPUS_RUN_ID="<run_id>"
export RAG_MODE=rag
python -m streamlit run app/app.py
```

앱에서 **문서 검색·선택 → 분석 결과 확인 → 선택 문서에 질문** 순서로 이용합니다. 원본 데이터 없이 화면만 미리 보려면 `RAG_MODE=mock`으로 실행합니다.

실행 모드·저장 경로·Windows 환경변수 설정은 [앱 실행 가이드](app/README.md)를 참고하세요.

### 3. 테스트

```bash
python -m pytest
```

테스트 범위와 개별 실행 방법은 [테스트 가이드](tests/README.md)에서 확인할 수 있습니다.

---

## 주요 문서

| 문서 | 내용 |
| --- | --- |
| [팀 문서 시작점](docs/team/README.md) | 목표, 일정, 역할, 첫 작업 안내 |
| [RAG 파이프라인 명세](docs/md/rag/RAG_PIPELINE_SPEC.md) | 문서 입력부터 검색·답변·평가까지의 계약 |
| [데이터 계약](docs/md/data/DATA_CONTRACT.md) | 원본 문서, 청크 메타데이터, 평가 질문 형식 |
| [실험 실행 가이드](docs/md/experiments/EXPERIMENT_GUIDE.md) | config 기반 실행과 결과 확인 |
| [Config 가이드](configs/README.md) | 실험 조건과 provider 설정 |
| [실행 스크립트 가이드](scripts/README.md) | 개별 RAG 명령과 산출물 |
| [앱 실행 가이드](app/README.md) | 내부 문서 준비, 실행 모드, 서비스 연결 |
| [프론트엔드 연결 계약](docs/team/rag_frontend_contract.md) | UI에서 사용하는 함수와 응답 형식 |

---

## 협업 원칙

- `main`은 공유 가능한 기준선으로 유지하고, 작업 브랜치와 PR로 변경을 관리합니다.
- RAG 실험 조건은 `configs/experiments/rag/`, 실행 산출물은 `experiments/`, 공유용 요약은 `reports/`에 둡니다.
- PR에는 변경 이유, 확인 방법, 관련 산출물 경로를 남깁니다.
- 답변뿐 아니라 검색된 근거·출처·실패 사례도 함께 검토합니다.

보드·Issue·PR·Daily Report 운영 방법은 [팀 운영 가이드](docs/team/operations.md)를 따릅니다.
