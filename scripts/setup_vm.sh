#!/bin/bash
# GCP VM 초기 셋업 스크립트
# 사용법: bash scripts/setup_vm.sh
# VM 생성 직후 한 번만 실행하면 모든 환경이 자동 구성됩니다.

set -e
echo "=== GCP VM 환경 셋업 시작 ==="
echo ""

# ===== 1. 시스템 패키지 =====
echo "[1/6] 시스템 패키지 설치..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3-pip python3-venv curl zstd

# ===== 2. Python 패키지 =====
echo "[2/6] Python 패키지 설치..."
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"
pip install -r requirements.txt --quiet

# ===== 3. Ollama 설치 =====
echo "[3/6] Ollama 설치..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "  이미 설치됨"
fi

# ===== 4. Ollama 서버 시작 + 모델 다운로드 =====
echo "[4/6] Ollama 서버 시작 및 모델 다운로드..."
if ! pgrep -x "ollama" > /dev/null; then
    ollama serve &
    sleep 5
fi

ollama pull gemma4:e2b

# ===== 5. rclone 설정 안내 =====
echo "[5/6] rclone 설정 안내"
if ! command -v rclone &> /dev/null; then
    sudo apt-get install -y -qq rclone
fi

echo ""
echo "  rclone 설정이 필요합니다. 아래 명령어를 실행하고 Google Drive 인증을 완료하세요:"
echo "    rclone config"
echo "    → n (new remote)"
echo "    → name: gdrive"
echo "    → storage: drive (Google Drive)"
echo "    → 이후 Enter로 기본값, 브라우저에서 인증"
echo ""

# ===== 6. 데이터 가져오기 =====
echo "[6/6] Drive에서 데이터 가져오기"
echo "  rclone 설정 완료 후 아래 명령어로 데이터를 가져오세요:"
echo "    bash scripts/sync_data.sh pull"
echo ""

echo "=== 셋업 완료 ==="
echo ""
echo "다음 단계:"
echo "  1. rclone config (Google Drive 연동)"
echo "  2. bash scripts/sync_data.sh pull (데이터 가져오기)"
echo "  3. python scripts/check_rag_pipeline.py --config configs/experiments/rag/rag_langchain.yaml --project-root . (동작 확인)"
echo "  4. 백업 자동화: crontab -e → 0 3 * * * bash $PROJECT_ROOT/scripts/sync_data.sh push"
