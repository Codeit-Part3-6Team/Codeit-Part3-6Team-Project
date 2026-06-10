# Outputs 디렉터리

`outputs/`는 임시 출력물이나 데모용 산출물을 둘 수 있는 공간입니다.

## Outputs 마인드맵

```mermaid
mindmap
  root((outputs))
    임시 결과
      확인용 파일
      export 파일
      데모 캡처
    구분
      experiments는 실험 결과
      reports는 공유 요약
      outputs는 임시 출력
    정리 기준
      재생성 가능
      커밋 필요성 확인
      대용량 제외
```

## 텍스트 구조

```text
outputs/
|-- .gitkeep    # 빈 디렉터리 유지
`-- README.md   # 임시 출력물 사용 기준
```

반복 실험 결과는 `experiments/`를 사용하고, 팀 공유용 요약은 `reports/`를 사용합니다.
이 폴더는 주로 임시 파일, export 파일, 확인용 결과물을 둘 때 사용합니다.
