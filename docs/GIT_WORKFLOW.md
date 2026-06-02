# Git 운영 규칙

## 브랜치

```text
main: 제출 가능한 안정 버전
dev: 통합 작업 브랜치
feature/{issue-number}-{short-name}: 개인 작업 브랜치
```

기본 흐름:

```text
feature/* -> dev PR -> 제출/데모 전 main PR
```

## Merge 기준

- 관련 Issue가 연결되어 있다.
- 로컬 또는 Colab 실행 결과를 기록했다.
- Data Contract 영향 여부를 확인했다.
- 관련 산출물이나 문서 경로를 남겼다.
- 최소 1명 이상이 확인한 뒤 merge한다.
