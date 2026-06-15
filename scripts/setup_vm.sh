#!/bin/bash
# GCP VM 초기 셋업 스크립트
# 사용법: bash scripts/setup_vm.sh
# VM 생성 직후 한 번만 실행하면 모든 환경이 자동 구성됩니다.

set -e
echo "=== GCP VM 환경 셋업 시작 ==="
echo ""

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONDA_ENV_NAME="codeit-ml-pipeline"

# ===== 1. 시스템 패키지 =====
echo "[1/8] 시스템 패키지 설치..."
sudo apt-get update -qq
sudo apt-get install -y -qq curl zstd python3-pip python3-venv nodejs npm

# ===== 2. Miniconda 설치 =====
echo "[2/8] Miniconda 설치..."
if ! command -v conda &> /dev/null; then
    MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    MINICONDA_SCRIPT="/tmp/miniconda_install.sh"
    curl -fsSL "$MINICONDA_URL" -o "$MINICONDA_SCRIPT"
    bash "$MINICONDA_SCRIPT" -b -p "$HOME/miniconda3"
    rm "$MINICONDA_SCRIPT"
    "$HOME/miniconda3/bin/conda" init bash
    source "$HOME/.bashrc"
else
    echo "  이미 설치됨"
fi

export PATH="$HOME/miniconda3/bin:$PATH"

# ===== 3. Conda 환경 생성 =====
echo "[3/8] Conda 환경 생성 ($CONDA_ENV_NAME)..."
cd "$PROJECT_ROOT"
if conda env list | grep -q "$CONDA_ENV_NAME"; then
    echo "  환경이 이미 존재합니다. 업데이트합니다..."
    conda env update -f environment.yml --prune
else
    conda env create -f environment.yml
fi

# ===== 4. Conda 환경을 Jupyter 커널로 등록 =====
echo "[4/8] Conda 환경을 Jupyter 커널로 등록..."
source "$HOME/miniconda3/bin/activate" "$CONDA_ENV_NAME"
python -m ipykernel install --user --name "$CONDA_ENV_NAME" --display-name "Python ($CONDA_ENV_NAME)"
pip install ipykernel jupyterlab-git --quiet

# ===== 5. Ollama 설치 =====
echo "[5/8] Ollama 설치..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "  이미 설치됨"
fi

# ===== 6. Ollama 서버 시작 + 모델 다운로드 =====
echo "[6/8] Ollama 서버 시작 및 모델 다운로드..."
if ! pgrep -x "ollama" > /dev/null; then
    ollama serve &
    sleep 5
fi
ollama pull gemma4:e2b

# ===== 7. rclone 설정 안내 =====
echo "[7/8] rclone 설정 안내"
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

# ===== 8. 데이터 가져오기 =====
echo "[8/8] Drive에서 데이터 가져오기"
echo "  rclone 설정 완료 후 아래 명령어로 데이터를 가져오세요:"
echo "    bash scripts/sync_data.sh pull"
echo ""

echo "=== 셋업 완료 ==="
echo ""
echo "Conda 환경: conda activate $CONDA_ENV_NAME"
echo "Jupyter 커널: Python ($CONDA_ENV_NAME)"
echo ""
echo "다음 단계:"
echo "  1. rclone config (Google Drive 연동)"
echo "  2. bash scripts/sync_data.sh pull (데이터 가져오기)"
echo "  3. python scripts/check_rag_pipeline.py --config configs/experiments/rag/rag_langchain.yaml --project-root ."
echo "  4. 백업 자동화: crontab -e → 0 3 * * * bash $PROJECT_ROOT/scripts/sync_data.sh push"
