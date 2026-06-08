# Git 운영 규칙

팀 프로젝트에서 충돌을 줄이고 작업 흐름을 보이게 만들기 위한 기본 규칙입니다.

## 브랜치

```text
main: 제출 가능한 안정 버전
dev: 팀 작업 통합 브랜치
feature/{issue-number}-{short-name}: 개인 기능 작업
fix/{issue-number}-{short-name}: 버그 수정
docs/{issue-number}-{short-name}: 문서 작업
experiment/{issue-number}-{short-name}: 실험 작업
```

기본 흐름:

```text
feature/* -> dev PR -> 발표/제출 전 main PR
```

## 커밋 메시지

커밋 메시지는 한국어로 작성합니다. 앞의 태그는 변경 성격을 빠르게 보기 위한 용도입니다.

```text
[feat] HuggingFace 텍스트 파인튜닝 파이프라인 추가
[fix] 데이터 검증 경로 처리 수정
[docs] Colab Drive 실험 가이드 추가
[test] HuggingFace 환경 smoke config 추가
[chore] 실험 요약 산출물 ignore 규칙 추가
```

## PR 기준

- 관련 Issue를 연결합니다.
- 변경 내용을 짧게 요약합니다.
- 실행한 명령과 결과를 남깁니다.
- 데이터 구조나 Data Contract에 영향이 있는지 확인합니다.
- 실험 결과가 있다면 `experiments/{experiment_name}` 또는 summary 경로를 남깁니다.
- 최소 1명 이상 확인 후 merge합니다.

## Merge 기준

- smoke test 또는 관련 테스트를 통과했습니다.
- 산출물이 필요한 작업이면 경로가 문서나 PR에 남아 있습니다.
- 충돌이 해결되어 있습니다.
- 발표/제출에 영향을 주는 변경은 PM이 최종 확인합니다.

## 금지/주의

- `data/raw` 원본 데이터를 직접 수정하지 않습니다.
- 대용량 weight, checkpoint, 실험 산출물을 Git에 올리지 않습니다.
- `main`에는 직접 push하지 않습니다.
- 실험 실패 기록을 지우지 않습니다. 실패도 다음 실험의 근거입니다.
