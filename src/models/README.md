# 모델 구현

이 폴더는 모델 코드와 registry를 관리합니다.

```text
src/models/
|-- registry.py      # config의 model.name을 실제 모델 객체로 연결
|-- centroid.py      # smoke test용 더미 모델
|-- text_keyword.py  # 텍스트 smoke test용 더미 모델
|-- huggingface_text.py # HuggingFace 텍스트 모델 adapter
`-- ...
```

새 모델을 추가할 때는 보통 아래 순서로 작업합니다.

1. `src/models/{model_name}.py`에 모델 구현을 추가한다.
2. `src/models/registry.py`의 `build_model()`에 등록한다.
3. config의 `model.name`으로 선택할 수 있게 한다.
4. train loop의 입력/출력 계약을 깨지 않는지 smoke test로 확인한다.

학습된 weight나 큰 모델 파일은 이 폴더에 넣지 않고 루트 `models/` 또는 `experiments/{exp_id}/` 아래에 저장합니다.

텍스트 프로젝트에서는 처음에 `keyword_text_classifier`로 파이프라인을 검증하고, 실제 학습 단계에서 `huggingface_sequence_classifier` 계열 adapter를 연결하는 식으로 확장합니다.
