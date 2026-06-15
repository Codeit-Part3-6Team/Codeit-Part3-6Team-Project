#!/bin/bash
# RAG 실험 결과 Google Drive 백업 스크립트
# 사용법: bash scripts/backup_experiments.sh
# 사전 준비: rclone 설정 (rclone config -> Google Drive -> 인증)

set -e

# ===== 설정 =====
# rclone remote 이름 (rclone config 에서 설정한 이름)
RCLONE_REMOTE="gdrive"

# Drive 내 백업 폴더 경로
DRIVE_BACKUP_DIR="codeit_rag_project"

# 로컬에서 백업할 폴더들
BACKUP_DIRS=("experiments" "reports")

# ===== 백업 실행 =====
echo "=== RAG 실험 결과 Google Drive 백업 ==="
echo "백업 일시: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

for dir in "${BACKUP_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        LOCAL_PATH="$PROJECT_ROOT/$dir"
        REMOTE_PATH="$RCLONE_REMOTE:/$DRIVE_BACKUP_DIR/$dir"
        echo "[백업] $LOCAL_PATH -> $REMOTE_PATH"
        rclone sync "$LOCAL_PATH" "$REMOTE_PATH" \
            --progress \
            --exclude "*.log" \
            --exclude "__pycache__/**" \
            --exclude ".gitkeep"
        echo "  완료: $dir ($(find "$LOCAL_PATH" -type f | wc -l)개 파일)"
    else
        echo "  건너뜀: $dir (폴더 없음)"
    fi
done

echo ""
echo "=== 백업 완료 ==="
echo "Drive 경로: MyDrive/$DRIVE_BACKUP_DIR/"
