# Google Drive 백업 설정

실험 결과와 리포트를 Google Drive에 자동 백업하는 방법입니다.

## 1회 설정 (VM에서 한 번만)

```bash
# rclone 설치
sudo apt install rclone

# Google Drive 연결 설정
rclone config
# → n (new remote)
# → name: gdrive
# → storage: drive (Google Drive 선택)
# → client_id: (Enter로 기본값)
# → client_secret: (Enter로 기본값)
# → scope: 1 (full access)
# → root_folder_id: (Enter)
# → service_account_file: (Enter)
# → auto config: y (브라우저에서 인증)
```

## 백업 실행

```bash
# 수동 백업
bash scripts/backup_experiments.sh

# 매일 자동 백업 (crontab)
# crontab -e 후 아래 줄 추가
0 3 * * * bash ~/project/scripts/backup_experiments.sh >> ~/backup.log 2>&1
```

## 복원

```bash
rclone copy "gdrive:/codeit_rag_project/experiments" ~/project/experiments
rclone copy "gdrive:/codeit_rag_project/reports" ~/project/reports
```

## 백업되는 것

| 폴더 | 내용 |
|---|---|
| `experiments/` | 모든 실험 산출물 (config, metrics, chunks, answers 등) |
| `reports/` | 비교 리포트, 실험 로그 |

## 백업되지 않는 것

- `*.log` 파일
- `__pycache__/`
- 원본 RFP 문서 (이미 Drive에 있음)
- Git 저장소 (GitHub에 있음)
