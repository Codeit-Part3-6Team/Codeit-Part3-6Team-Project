#!/bin/bash
# GCP VM 초기 셋업 스크립트
# 사용법: sudo bash scripts/setup_vm.sh
# VM 생성 직후 한 번만 실행하면 모든 환경이 자동 구성됩니다.

set -e
echo "=== GCP VM 환경 셋업 시작 ==="
echo ""

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONDA_ENV_NAME="codeit-ml-pipeline"
CONDA_DIR="/opt/conda"

# ===== 1. 시스템 패키지 =====
echo "[1/9] 시스템 패키지 설치..."
sudo apt-get update -qq
sudo apt-get install -y -qq curl zstd python3-pip python3-venv nodejs npm git

# ===== 1.5. 공유 디렉터리 생성 =====
echo "[1.5/9] 공유 디렉터리 생성..."
sudo groupadd -f shared
sudo usermod -aG shared "$USER"
sudo mkdir -p /shared/data/raw_docs
sudo mkdir -p /shared/cache/huggingface
sudo mkdir -p /shared/cache/sentence-transformers
sudo chgrp -R shared /shared
sudo chmod -R 775 /shared
echo "  공유 데이터 경로: /shared/data/raw_docs"
echo "  공유 캐시 경로: /shared/cache/"
echo "  팀원 추가 시: sudo usermod -aG shared 계정명"

# ===== 2. Miniconda 설치 (공용 /opt/conda) =====
echo "[2/9] Miniconda 설치 ($CONDA_DIR)..."
if [ ! -d "$CONDA_DIR" ]; then
    MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    MINICONDA_SCRIPT="/tmp/miniconda_install.sh"
    curl -fsSL "$MINICONDA_URL" -o "$MINICONDA_SCRIPT"
    sudo bash "$MINICONDA_SCRIPT" -b -p "$CONDA_DIR"
    rm "$MINICONDA_SCRIPT"
    sudo chmod -R 775 "$CONDA_DIR"
else
    echo "  이미 설치됨"
fi

export PATH="$CONDA_DIR/bin:$PATH"

# ===== 3. Conda 환경 생성 =====
echo "[3/9] Conda 환경 생성 ($CONDA_ENV_NAME)..."
ENV_DIR="$CONDA_DIR/envs/$CONDA_ENV_NAME"
cd "$PROJECT_ROOT"
if [ -d "$ENV_DIR" ]; then
    echo "  환경이 이미 존재합니다. 업데이트합니다..."
    conda env update -f environment.yml -p "$ENV_DIR" --prune
else
    sudo "$CONDA_DIR/bin/conda" env create -f environment.yml -p "$ENV_DIR"
fi
sudo chmod -R 775 "$ENV_DIR"
sudo chgrp -R shared "$ENV_DIR"

# ===== 3.5. HF 캐시 환경변수 설정 =====
echo "[3.5/9] HuggingFace 캐시 공유 세팅..."
ACTIVATE_D="$CONDA_DIR/envs/$CONDA_ENV_NAME/etc/conda/activate.d"
sudo mkdir -p "$ACTIVATE_D"
sudo tee "$ACTIVATE_D/env_vars.sh" > /dev/null << 'EOF'
export HF_HOME=/shared/cache/huggingface
export SENTENCE_TRANSFORMERS_HOME=/shared/cache/sentence-transformers
export TORCH_HOME=/shared/cache/torch
EOF
sudo chmod 775 "$ACTIVATE_D/env_vars.sh"
echo "  HF 캐시: /shared/cache/huggingface"

# ===== 4. Conda 환경을 Jupyter 커널로 등록 =====
echo "[4/9] Conda 환경을 Jupyter 커널로 등록..."
source "$CONDA_DIR/bin/activate" "$CONDA_ENV_NAME"
pip install ipykernel jupyterlab-git --quiet
python -m ipykernel install --user --name "$CONDA_ENV_NAME" --display-name "Python ($CONDA_ENV_NAME)"

# ===== 5. Ollama 설치 =====
echo "[5/9] Ollama 설치..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "  이미 설치됨"
fi

# ===== 6. Ollama 서버 시작 + 모델 다운로드 =====
echo "[6/9] Ollama 서버 시작 및 모델 다운로드..."
if ! pgrep -x "ollama" > /dev/null; then
    ollama serve &
    sleep 5
fi
ollama pull gemma4:e2b

# ===== 7. rclone 설정 안내 =====
echo "[7/9] rclone 설정 안내"
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
echo "[8/9] Drive에서 데이터 가져오기"
echo "  rclone 설정 완료 후 아래 명령어로 데이터를 가져오세요:"
echo "    bash scripts/sync_data.sh pull"
echo ""

echo "=== 셋업 완료 ==="
echo ""
echo "공유 데이터 경로: /shared/data/raw_docs"
echo "공유 캐시 경로: /shared/cache/"
echo "Conda 환경 (공용): $CONDA_DIR/envs/$CONDA_ENV_NAME"
echo "Jupyter 커널: Python ($CONDA_ENV_NAME)"
echo ""
echo "다음 단계:"
echo "  1. bash scripts/add_user.sh <계정명> <ssh-pubkey> (팀원 추가)"
echo "  2. rclone config (Google Drive 연동)"
echo "  3. bash scripts/sync_data.sh pull (데이터 가져오기)"
echo "  4. python scripts/check_rag_pipeline.py --config configs/experiments/rag/rag_langchain.yaml --project-root ."
echo ""
echo "=== 팀원별 초기 셋업 ==="
echo "  각자 SSH 접속 후 한 번만 실행:"
echo "    wget https://raw.githubusercontent.com/Codeit-Part3-6Team/Codeit-Part3-6Team-Project/main/scripts/setup_user.sh"
echo "    bash setup_user.sh"
