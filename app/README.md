# It's mine - RFP 입찰 분석 서비스

RFP/입찰 공고 문서를 내부 corpus로 미리 인덱싱해두고, 사용자가 문서를 검색/선택한 뒤 요약, 요구사항 추출, 비교, 채팅 질의를 수행하는 Streamlit 앱입니다.

현재 앱은 파일 업로드 화면이 아니라 **내부 RFP 문서 목록 기반 분석 흐름**을 기본으로 사용합니다.

## 폴더 구조

```text
app/
|-- app.py                    # Streamlit 실행 파일, 공통 session_state 초기화
|-- README.md                 # 앱 설명 파일
|-- views/
|   |-- home.py               # 홈
|   |-- documents.py          # 내부 문서 검색/선택/분석 시작
|   |-- workspace.py          # 분석 결과 + 선택 문서 RAG 채팅
|   |-- pricing.py            # 요금제
|-- services/
|   |-- frontend_adapter.py   # 화면 코드와 RAG 서비스 사이 변환 계층
|   |-- rag_service.py        # Streamlit UI용 RAG 서비스 함수
|   |-- sqlite_store.py       # run/document/chat_history 저장소
|-- examples/
|   |-- build_internal_corpus.py # 내부 문서 전체 ingest 예시
|   |-- list_corpus_runs.py      # 생성된 corpus run 확인
|-- utils/
|   |-- styles.py             # 전역 CSS
|   |-- components.py         # 상단 네비게이션/공통 컴포넌트
|   |-- mock_data.py          # RAG 미연결 로컬 미리보기 데이터
|-- .streamlit/
|   |-- config.toml           # Streamlit 테마 설정
```

## 실행 방법

```bash
pip install -r requirements.txt
python -m streamlit run app/app.py
```

기본 화면은 앱 내부 네비게이션을 통해 `documents.py`로 이동해 문서를 선택하고, 분석 완료 후 `workspace.py`에서 결과와 채팅을 확인하는 흐름입니다.

## RAG 연결 흐름

화면 코드는 `src.rag`를 직접 import하지 않고 `app/services/frontend_adapter.py`를 통해 호출합니다.

주요 흐름은 다음과 같습니다.

1. VM에서 내부 원문 폴더를 한 번 ingest해 corpus run 생성
2. `documents.py`가 `internal_corpus()`로 가장 적합한 corpus run과 문서 목록 조회
3. 사용자가 문서 1건 또는 여러 건 선택
4. `analyze_selection()`이 `summarize()`와 `extract_requirements()` 실행
5. `workspace.py`가 `chat_ask()`로 선택 문서 범위 RAG 질의 수행
6. UI는 `reply`, `structured_output`, `citations`를 분리해 표시

## 내부 corpus 준비

VM에서 내부 문서를 먼저 인덱싱합니다.

```bash
python app/examples/build_internal_corpus.py --raw-docs-dir /shared/data/raw_docs
python app/examples/list_corpus_runs.py
```

특정 run을 앱에서 고정해서 쓰고 싶으면 환경변수로 지정합니다.

```bash
set RAG_CORPUS_RUN_ID=<run_id>
```

Linux/VM shell에서는 다음처럼 지정합니다.

```bash
export RAG_CORPUS_RUN_ID=<run_id>
```

## 실행 모드

`RAG_MODE`로 앱 모드를 명시할 수 있습니다.

```bash
set RAG_MODE=rag
set RAG_MODE=mock
```

- `RAG_MODE=mock`: RAG 연결 없이 mock 데이터로 화면 미리보기
- `RAG_MODE=rag`: RAG 연결 실패 시 상단 배너에 실패 상태 표시
- 미설정: RAG import 가능하면 실제 RAG, 아니면 mock fallback

## 현재 점검 메모

- Streamlit config는 `configs/experiments/rag/streamlit.yaml`을 사용하며, `agent/agent_lplus.yaml`과 `config_final.yaml`을 `base_config`로 상속합니다.
- 앱 경로에서는 `streamlit.yaml`이 `vector_store.type: chroma`를 override하므로 Chroma 기반 검색을 사용합니다.
- 선택 문서 채팅은 `ask_with_document_filter(run_id, question, selected_doc_ids)`를 통해 문서 범위를 전달합니다.
- 내일 VM 실테스트에서는 내부 corpus ingest, 문서 목록 선택, 단일 문서 요약, 다중 문서 비교, 선택 문서 채팅, citation 범위를 우선 확인합니다.
