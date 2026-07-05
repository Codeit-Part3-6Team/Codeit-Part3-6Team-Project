# Streamlit RAG 연결 구현 리뷰

대상 브랜치: `origin/jinwoo`  
비교 기준: `origin/feature/streamlit-contract-demo`  
작성 목적: Jinwoo님이 계약 기반으로 작성한 Streamlit 연결 구현을 서비스 구조 관점에서 검토하고, 내부 corpus 모드와 외부 업로드 모드를 어떻게 가져갈지 정리한다.

## 요약

Jinwoo님 구현은 기존 Streamlit UI를 크게 유지하면서 `app/services/frontend_adapter.py`를 통해 RAG 백엔드와 Mock 데이터를 같은 형태로 변환하는 방식이다.

방향 자체는 좋다. 기존 화면을 모두 갈아엎지 않고, 화면 코드와 RAG 계약층 사이에 번역 계층을 둔 점은 현실적인 선택이다.

다만 현재 구현은 주로 "외부 업로드 문서 1건을 분석하는 흐름"에 가깝다. 우리가 원래 의도했던 "이미 ingest된 내부 RFP 전체 문서를 대상으로 선택/비교/질문하는 흐름"과는 역할이 다르다.

따라서 둘 중 하나를 버리기보다 아래처럼 분리해서 가져가는 것이 좋다.

```text
내부 corpus 모드
→ /shared/data/raw_docs 전체를 한 번 ingest
→ 전체 내부 RFP 문서 목록에서 선택/비교/질문
→ 반복 ingest 없음

외부 업로드 모드
→ 사용자가 새 파일 업로드
→ 업로드 파일만 새 run으로 ingest
→ 해당 문서 요약/질문
→ 신규 문서 검토용
```

## 수정 체크리스트

| ID | 우선순위 | 범위 | 수정 항목 | 대상 파일 | 확인 방법 |
| --- | --- | --- | --- | --- | --- |
| F1 | 높음 | Jinwoo Streamlit 연결 | RAG import 실패를 broad `Exception`으로 Mock 처리하지 않도록 축소 | `app/services/frontend_adapter.py` | VM에서 RAG 내부 오류가 Mock으로 숨겨지지 않는지 확인 |
| F2 | 중간 | Jinwoo Streamlit UI | 파일명, 요약, 요구사항, 채팅 응답, citation tag에 HTML escape 적용 | `app/views/analyze.py`, `app/views/workspace.py` | `<b>test</b>` 같은 문자열이 태그가 아니라 문자로 보이는지 확인 |
| F3 | 높음 | 서비스 흐름 | 내부 corpus 모드와 외부 업로드 모드를 UI/흐름상 분리 | `app/views/*`, `app/services/frontend_adapter.py` 또는 별도 내부 문서 화면 | 내부 문서 화면은 98개 문서 목록, 업로드 화면은 업로드 문서 1건만 보이는지 확인 |
| F4 | 낮음 | 파일 구조 | `app/example`와 `app/examples` 중복 정리 | `app/example/*`, `app/examples/*` | `git ls-files app/example app/examples`로 단일 경로만 남았는지 확인 |
| F5 | 낮음~중간 | Streamlit 상태 관리 | 다른 문서 분석 시 `run_id`, `doc_bytes`, `pending_q`까지 초기화 | `app/views/workspace.py`, 필요 시 `app/views/analyze.py` | 문서 A 분석 후 문서 B 분석 시 이전 채팅/run 상태가 남지 않는지 확인 |
| R1 | 중간 | RAG 파이프라인 별도 이슈 | `preamble`을 `parsed_documents.csv` checkpoint에 보존 | `src/rag/pipeline.py` | chunks 재생성/resume 후에도 chunk text에 preamble이 유지되는지 확인 |

권장 처리 순서:

```text
1. F1 broad fallback 축소
2. F5 session 초기화
3. F4 example 경로 정리
4. F2 HTML escape
5. F3 내부 corpus / 외부 업로드 흐름 분리
6. R1 preamble checkpoint는 별도 RAG 파이프라인 이슈로 처리
```

## 현재 구현 구조

### 1. UI 진입점

`origin/jinwoo:app/app.py`

기존 페이지 구조는 유지하고, session state에 아래 값이 추가되었다.

```python
ss.setdefault("doc_bytes", None)
ss.setdefault("run_id", None)
```

이 값은 업로드 파일 내용을 rerun 이후에도 유지하고, RAG ingest 결과 run을 workspace에서 재사용하기 위한 값이다.

### 2. 프론트 어댑터

`origin/jinwoo:app/services/frontend_adapter.py`

역할은 세 가지다.

```text
1. rag_service import 가능 여부 감지
2. RAG 응답을 기존 UI 데이터 형태로 변환
3. 실패 시 Mock 또는 UI 친화적 에러로 변환
```

이 구조 덕분에 `views/analyze.py`, `views/workspace.py`는 RAG 내부 구조를 거의 알지 않는다.

### 3. 분석 화면

`origin/jinwoo:app/views/analyze.py`

업로드 파일을 session state에 저장하고, 분석 버튼을 누르면:

```text
file_bytes
→ frontend_adapter.analyze_document()
→ rag_service.create_and_ingest()
→ summarize()
→ extract_requirements()
→ workspace 이동
```

이 흐름은 외부 업로드 문서 1건 분석에는 적합하다.

### 4. 워크스페이스

`origin/jinwoo:app/views/workspace.py`

왼쪽은 분석 결과 카드, 오른쪽은 채팅이다.

채팅은:

```python
chat_ask(question, ss.run_id)
```

를 호출하고, 내부적으로 `rag_service.ask_with_document_filter()`로 연결된다.

## 좋은 점

### 기존 UI와 충돌이 적다

기존 mock UI를 크게 유지하면서 연결부만 바꿨다. 이 방식은 프론트 구현자의 작업을 존중하면서 실제 RAG 연결을 붙이기에 좋다.

### RAG 계약층과 UI 계층을 분리했다

`rag_service.py`가 RAG 백엔드 계약이고, `frontend_adapter.py`는 기존 UI용 번역층이다.

이 분리는 유지할 가치가 있다.

```text
app/services/rag_service.py
→ RAG 백엔드 계약

app/services/frontend_adapter.py
→ Streamlit UI용 변환/폴백 계층
```

### 외부 업로드 문서 분석 흐름이 자연스럽다

사용자가 파일을 올리고 분석 버튼을 누르는 서비스 흐름에는 잘 맞는다.

```text
업로드 파일
→ 임시 디렉토리 저장
→ create_and_ingest()
→ 요약/요구사항 추출
→ 워크스페이스 표시
```

## 주요 이슈

### 1. RAG import 실패를 너무 넓게 Mock으로 숨긴다

위치: `origin/jinwoo:app/services/frontend_adapter.py:41-46`

우선순위: 높음  
수정 담당: Streamlit 연결 담당  
성격: 서비스 진단/운영 안정성

현재는 `Exception` 전체를 잡고 Mock으로 폴백한다.

```python
try:
    from services import rag_service
    _rag = rag_service
except Exception as exc:
    _rag = None
    _rag_error = str(exc)
```

문제는 VM 환경에서 RAG 코드 자체가 깨져도 Mock으로 조용히 넘어간다는 점이다.

예를 들어:

```text
config 오류
src 내부 import 오류
rag_service 내부 syntax/runtime 오류
dependency 버전 오류
```

이런 문제도 모두 "RAG 미연결 → Mock 모드"로 보일 수 있다.

권장 수정:

```python
def _load_rag():
    global _rag, _rag_checked, _rag_error
    if _rag_checked:
        return _rag
    _rag_checked = True
    try:
        from services import rag_service
        _rag = rag_service
    except ModuleNotFoundError as exc:
        # 로컬 프론트 개발처럼 RAG 백엔드 자체가 없는 경우만 Mock 허용
        _rag = None
        _rag_error = str(exc)
    except Exception:
        # VM/RAG 환경에서 실제 백엔드 오류가 난 경우는 숨기지 않음
        raise
    return _rag
```

확인 방법:

```text
1. 로컬에서 src 또는 services.rag_service import가 불가능한 상태
   → Mock 모드 표시

2. VM에서 rag_service 내부 오류를 임의로 발생
   → Mock으로 조용히 넘어가지 않고 에러가 보이는지 확인
```

### 2. HTML escape 없이 사용자/LLM/RAG 값을 렌더링한다

위치:

```text
origin/jinwoo:app/views/analyze.py:50-51
origin/jinwoo:app/views/workspace.py:57-78
origin/jinwoo:app/views/workspace.py:100-127
```

우선순위: 중간  
수정 담당: Streamlit UI 담당  
성격: 화면 안정성/표시 안전성

현재 `unsafe_allow_html=True` 안에 아래 값들이 그대로 들어간다.

```text
파일명
요약 답변
요구사항
사업 개요 meta
채팅 답변
citation tag
```

내부 데모 서비스라 보안 위험도는 높지 않다. 다만 RFP 원문, 파일명, LLM 응답은 외부 입력이므로 HTML 특수문자가 섞이면 화면이 깨질 수 있다. 특히 citation tag, 파일명, 채팅 응답은 escape 처리하는 편이 안전하다.

권장 수정:

```python
from html import escape

safe_summary = escape(data["summary"])
```

예시:

```python
safe_doc_name = escape(str(ss.doc_name))
safe_summary = escape(str(data.get("summary", "")))

st.markdown(
    f'<div class="panel-title">🗂️ {safe_doc_name}</div>',
    unsafe_allow_html=True,
)
```

가능한 곳은 `unsafe_allow_html=True`를 쓰지 않고 `st.write`, `st.markdown` 기본 렌더링을 사용한다.

확인 방법:

```text
파일명 또는 mock 응답에 <b>test</b>, <script>alert(1)</script> 같은 문자열을 넣었을 때
태그로 렌더링되지 않고 문자 그대로 보이는지 확인
```

### 3. 내부 corpus 모드와 외부 업로드 모드가 섞여 있다

현재 Jinwoo님 구현은 외부 업로드 문서 분석에 가깝다.

우선순위: 높음  
수정 담당: 서비스/UI 설계 담당  
성격: 제품 흐름 정리

```text
업로드 파일 1개
→ create_and_ingest(temp_dir)
→ 문서 1개짜리 run 생성
```

반면 우리가 원하는 내부 문서 탐색은:

```text
/shared/data/raw_docs 전체
→ 한 번 ingest
→ 98개 문서 전체 인덱스 재사용
```

이다.

따라서 UI에서는 두 모드를 명확히 나누는 편이 좋다.

```text
탭 1. 내부 문서 탐색 또는 사내 문서 분석
  - 전체 RFP 문서 목록
  - 문서 선택
  - 요약 / 비교 / 질문

탭 2. 새 문서 업로드 또는 신규 RFP 분석
  - 파일 업로드
  - 해당 문서만 분석
  - 요약 / 질문
```

구현 방향:

```text
내부 문서 탐색
→ list_runs()
→ 문서가 있는 최신 내부 corpus run 자동 선택
→ get_documents(run_id)
→ selected_doc_ids 기반 summarize / compare / ask

새 문서 업로드
→ file_uploader
→ create_and_ingest(temp_dir)
→ summarize / extract_requirements / ask
```

확인 방법:

```text
1. /shared/data/raw_docs 전체를 build_internal_corpus.py로 ingest
2. 내부 문서 탐색 화면에서 문서가 1개가 아니라 전체 문서 수로 보이는지 확인
3. 새 문서 업로드 화면에서 업로드 문서만 분석되는지 확인
```

### 4. 예시 경로가 중복된다

Jinwoo님 브랜치:

```text
app/example/
```

기존 계약 브랜치:

```text
app/examples/
```

우선순위: 낮음  
수정 담당: 작업 브랜치 정리 담당  
성격: 경로 정리/팀 혼선 방지

둘 다 있으면 팀원이 헷갈린다.

권장:

```text
app/examples/ 로 통일
app/example/ 제거 또는 이동
```

수정 예시:

```bash
mkdir -p app/examples
git mv app/example/*.py app/examples/
git rm -r app/example
```

확인 방법:

```bash
git ls-files app/example app/examples
```

`app/example` 아래 파일이 남지 않으면 된다.

### 5. 세션 초기화가 일부 부족하다

위치: `origin/jinwoo:app/views/workspace.py:40-45`

우선순위: 낮음~중간  
수정 담당: Streamlit UI 담당  
성격: 상태 꼬임 방지

다른 문서 분석으로 돌아갈 때 아래 값들도 함께 초기화하는 편이 안전하다.

```python
ss.run_id = None
ss.doc_bytes = None
ss.pending_q = None
```

현재는 일부 이전 상태가 남을 수 있다.

수정 예시:

```python
if st.button("다른 문서 분석", type="secondary", use_container_width=True, key="ws_change"):
    ss.doc_name = None
    ss.doc_bytes = None
    ss.analyzed = False
    ss.analysis = None
    ss.run_id = None
    ss.pending_q = None
    ss.messages = []
    st.switch_page(P_ANALYZE)
```

확인 방법:

```text
1. 문서 A 분석
2. 채팅 질문 입력
3. 다른 문서 분석 버튼 클릭
4. 문서 B 분석
5. 이전 run_id, 채팅 기록, pending 질문이 남지 않는지 확인
```

## 별도 RAG 파이프라인 이슈

아래 항목은 Jinwoo님 Streamlit 연결 구현 자체의 문제라기보다, 현재 RAG 파이프라인의 checkpoint 재현성 이슈다. 별도 이슈로 관리하는 것이 적절하다.

### preamble checkpoint 보존

현재 main 기준 구조:

```text
document_loader.py
→ document row에 preamble 생성

chunker.py / engines/langchain.py
→ document["preamble"]을 읽어 chunk text 앞에 삽입

pipeline.py
→ DOCUMENT_COLUMNS에는 preamble 없음
```

즉 첫 ingest에서 documents를 메모리로 바로 chunking하면 정상이다. 하지만 `parsed_documents.csv`를 checkpoint로 다시 읽어 chunk를 재생성하면 preamble이 유실될 수 있다.

진우님 신규 업로드 단발 분석 경로에서는 즉시 문제 가능성이 낮다. 다만 내부 corpus 재사용, resume, chunks 재생성, 실험 반복에서는 검색 품질이 조용히 달라질 수 있다.

권장 수정:

```python
DOCUMENT_COLUMNS = [
    "document_id",
    "title",
    "source_path",
    "page",
    "section",
    "preamble",
    "text",
]
```

확인 방법:

```text
1. CSV 기반 ingest 실행
2. parsed_documents.csv에 preamble 컬럼이 저장되는지 확인
3. chunks.csv 삭제 후 resume 실행
4. 새 chunks.csv text 앞에 사업명/발주기관/금액 preamble이 유지되는지 확인
```

## 내부 corpus 모드와 외부 업로드 모드 권장 설계

### 내부 corpus 모드

목적:

```text
사내에 이미 쌓아둔 RFP 전체를 대상으로 검색/비교/질문
```

초기 준비:

```bash
python app/examples/build_internal_corpus.py --raw-docs-dir /shared/data/raw_docs
```

서비스 동작:

```text
1. 최신 내부 corpus run을 찾는다
2. get_documents(run_id)로 전체 문서 목록을 보여준다
3. 사용자가 문서 0개, 1개, 여러 개를 선택한다
4. 선택 문서 기준으로 summarize / compare / ask 실행
```

특징:

```text
반복 ingest 없음
문서 목록 기반 UI
비교/추천/조건 검색에 적합
```

### 외부 업로드 모드

목적:

```text
새로 받은 RFP 1건을 빠르게 분석
```

서비스 동작:

```text
1. 사용자가 파일 업로드
2. 임시 디렉토리에 저장
3. create_and_ingest(temp_dir)
4. 새 run 생성
5. 해당 문서 요약/요구사항/질문
```

특징:

```text
업로드마다 새 run 생성
신규 문서 검토에 적합
내부 corpus와 독립적으로 관리 가능
```

## 머지 전 최소 체크리스트

1. `frontend_adapter.py`의 broad exception Mock fallback 축소
2. `workspace.py`, `analyze.py`의 HTML escape 처리
3. `app/example` vs `app/examples` 경로 통일
4. 다른 문서 분석 시 `run_id`, `doc_bytes`, `pending_q` 초기화
5. 내부 corpus 모드와 외부 업로드 모드를 UI에서 분리할지 결정

별도 RAG 파이프라인 이슈:

```text
preamble이 parsed_documents.csv checkpoint에 보존되는지 확인
```

## 결론

기존 UI에 실제 RAG를 붙이는 adapter 방식은 꽤 좋은 방향이다.

다만 현재 상태로는 외부 업로드 문서 분석에 초점이 맞춰져 있고, 내부 전체 RFP corpus 탐색 흐름은 별도로 유지해야 한다.

따라서 추천 방향은 다음과 같다.

```text
rag_service.py
→ 유지. RAG 백엔드 계약층

frontend_adapter.py
→ 유지. 기존 UI용 변환 계층

내부 corpus UI
→ 별도 탭/페이지로 유지

외부 업로드 UI
→ Jinwoo님 analyze/workspace 흐름 활용

app/example
→ app/examples로 통합

preamble checkpoint
→ Jinwoo님 UI 구현 리뷰에서는 제외하고 RAG 파이프라인 이슈로 별도 처리
```

한 줄로 정리하면:

```text
외부 업로드 분석은 Jinwoo님 흐름을 살리고,
내부 RFP 전체 탐색은 corpus 재사용 모드로 분리해서 가져가는 것이 가장 덜 꼬인다.
```
