# Source 디렉터리

`src/`는 파이프라인의 실제 구현 코드가 들어가는 곳입니다.

## 주요 모듈

- `config.py`: config 로딩과 JSON 저장
- `artifacts.py`: 실험 산출물 폴더, 상태 파일, 실패 로그, 백업
- `data.py`: 분류 모델용 데이터 로딩
- `train.py`: 학습 루프, checkpoint, scheduler, early stopping
- `predict.py`: 단건 예측
- `metrics.py`: metric 계산
- `experiments.py`: 실험 결과 요약
- `models/`: 분류 모델 구현체와 registry
- `rag/`: RAG 문서 처리, 검색, 답변, 평가
- `utils/`: path, seed, logging 같은 공통 유틸

## 원칙

- `scripts/`는 실행 진입점이고, `src/`는 재사용 가능한 구현체입니다.
- config로 바꿀 수 있는 값은 코드에 하드코딩하지 않습니다.
- public 함수와 클래스에는 한국어 docstring을 둡니다.
