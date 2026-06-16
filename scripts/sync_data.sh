#!/bin/bash
# Google Drive <-> VM 데이터 동기화 스크립트
# 사용법:
#   bash scripts/sync_data.sh pull    # Drive -> VM (데이터 가져오기)
#   bash scripts/sync_data.sh push    # VM -> Drive (실험 결과 백업)

set -e

RCLONE_REMOTE="gdrive"
DRIVE_DIR="codeit_rag_project"

# VM에 데이터를 둘 경로 (모든 계정 공유)
VM_DATA_DIR="/shared/data/raw_docs"
VM_EVAL_DIR="/shared/data"

# Drive 경로 (Codeit 제공 공유 폴더)
DRIVE_DATA="AI 10기/프로젝트/중급 프로젝트/원본 데이터"
DRIVE_EVAL="AI 10기/프로젝트/중급 프로젝트/원본 데이터"

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

pull_data() {
    echo "=== Drive -> VM 데이터 가져오기 ==="
    echo ""

    # 1) 원본 RFP 문서
    echo "[Pull] 원본 RFP 문서"
    mkdir -p "$VM_DATA_DIR"
    rclone sync "$RCLONE_REMOTE:/$DRIVE_DATA" "$VM_DATA_DIR" --progress
    echo "  문서 수: $(find "$VM_DATA_DIR" -type f | wc -l)개"

    # 2) 평가 질문 CSV
    echo ""
    echo "[Pull] 평가 질문 CSV"
    rclone copy "$RCLONE_REMOTE:/$DRIVE_EVAL/eval_questions.csv" "$VM_EVAL_DIR/" --ignore-existing 2>/dev/null || echo "  (eval_questions.csv 없음, 건너뜀)"

    echo ""
    echo "=== 데이터 동기화 완료 ==="
}

push_results() {
    echo "=== VM -> Drive 실험 결과 백업 ==="
    echo ""

    for dir in "experiments" "reports"; do
        if [ -d "$dir" ]; then
            echo "[Push] $dir/"
            rclone sync "$dir" "$RCLONE_REMOTE:/$DRIVE_DIR/$dir" \
                --progress \
                --exclude "*.log" \
                --exclude "__pycache__/**"
        else
            echo "[Push] $dir/ (건너뜀 - 폴더 없음)"
        fi
    done

    echo ""
    echo "=== 백업 완료 ==="
}

case "${1:-}" in
    pull) pull_data ;;
    push) push_results ;;
    *)
        echo "사용법: bash scripts/sync_data.sh [pull|push]"
        echo "  pull  - Drive에서 VM으로 데이터 가져오기"
        echo "  push  - VM에서 Drive로 실험 결과 백업"
        exit 1
        ;;
esac
