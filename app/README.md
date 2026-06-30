# It's mine - RFP 입찰 분석 서비스

RAG 기반의 모델을 활용하여 RFP(정부제안서) 입찰 문서를 분석하는 웹 서비스의 프론트엔드 및 백엔드 파일입니다.
RFP 문서를 업로드 하면 요약을 해주고 챗봇의 형태로 사용자가 질문도 할 수 있습니다.

## 폴더 구조

```
app/
|-- app.py     # 실행 파일, 공통 설정 
|-- README.md   # 앱 설명 파일
|-- views/
|   |-- home.py         # 홈 (랜딩페이지)
|   |-- analyze.py      # 분석하기 
|   |-- workspace.py    # 요약 + 채팅
|   |-- pricing.py      # 요금제
|
|-- utils/
|   |-- styles.py       # 전역 CSS (디자인, 색상)
|   |-- components.py   # 상단 네비바 및 아이콘
|   |-- mock_data.py    #  Mock 데이터 (RAG 연결 파일)
|
|-- .streamlit/
    |-- config.toml     # 다크 테마 설정
```

## 실행 방법

```bash
pip install streamlit
```
> requirements.txt에 포함되어 있기 때문에 pip install -r requirements.txt로 설치해도 됩니다.

```bash
python -m streamlit run app/app.py
```

실행하면 브라우저에서 자동 실행됩니다.
(기본 주소: http://localhost:8501/workspace)

## RAG 연결 계약

실제 RAG 연결은 화면 코드에서 `src.rag`를 직접 import하지 않고 `app/services/rag_service.py`를 통해 호출합니다.

주요 흐름은 다음과 같습니다.

1. 업로드 파일을 임시 디렉토리에 저장
2. `create_and_ingest(temp_dir)` 호출
3. 반환된 `run_id`를 세션에 저장
4. `summarize`, `extract_requirements`, `ask_with_document_filter` 호출
5. `reply`, `structured_output`, `citations`를 UI에 표시

참고 화면은 `app/views/rag_contract_demo.py`입니다. 최종 UI는 이 화면을 그대로 쓰기보다 `app/services/rag_service.py`의 함수 계약만 유지해서 다시 구성하면 됩니다.

팀 공유용 설명은 `docs/team/rag_frontend_contract.md`를 확인하세요.


