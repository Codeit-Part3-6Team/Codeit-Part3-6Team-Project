#!/bin/bash
# JupyterHub 사용자별 초기 셋업 스크립트
# 사용법: bash setup_user.sh
# 주피터허브 터미널에서 최초 1회 실행하면 모든 환경이 자동 구성됩니다.

set -e
echo "=== 사용자 환경 셋업 시작 ==="
echo ""

GIT_REPO="https://github.com/Codeit-Part3-6Team/Codeit-Part3-6Team-Project.git"
CONDA_ENV_NAME="codeit-ml-pipeline"
MINICONDA_DIR="$HOME/miniconda3"
PROJECT_DIR="$HOME/project"

# ===== 1. 프로젝트 클론 =====
echo "[1/5] 프로젝트 클론..."
if [ -d "$PROJECT_DIR" ]; then
    echo "  이미 클론되어 있습니다. 최신 상태로 업데이트합니다..."
    cd "$PROJECT_DIR"
    git pull
else
    git clone "$GIT_REPO" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# ===== 2. Miniconda 설치 (없는 경우) =====
echo "[2/5] Miniconda 설치 확인..."
if ! command -v conda &> /dev/null; then
    echo "  Miniconda 설치 중..."
    MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    curl -fsSL "$MINICONDA_URL" -o /tmp/miniconda_install.sh
    bash /tmp/miniconda_install.sh -b -p "$MINICONDA_DIR"
    rm /tmp/miniconda_install.sh
    "$MINICONDA_DIR/bin/conda" init bash
    export PATH="$MINICONDA_DIR/bin:$PATH"
else
    echo "  이미 설치됨"
fi

export PATH="$MINICONDA_DIR/bin:$PATH"

# ===== 3. Conda 환경 생성 =====
echo "[3/5] Conda 환경 생성 ($CONDA_ENV_NAME)..."
cd "$PROJECT_DIR"
if conda env list | grep -q "$CONDA_ENV_NAME"; then
    echo "  환경이 이미 존재합니다. 업데이트합니다..."
    conda env update -f environment.yml --prune
else
    conda env create -f environment.yml
fi

# ===== 4. Jupyter 커널 등록 =====
echo "[4/5] Jupyter 커널 등록..."
source "$MINICONDA_DIR/bin/activate" "$CONDA_ENV_NAME"
python -m ipykernel install --user --name "$CONDA_ENV_NAME" --display-name "Python ($CONDA_ENV_NAME)"
pip install ipykernel jupyterlab-git --quiet

# ===== 5. 데이터 경로 확인 =====
echo "[5/5] 데이터 경로 확인..."
if [ -d "/shared/data/raw_docs" ]; then
    echo "  공유 데이터 경로: /shared/data/raw_docs (준비됨)"
else
    echo "  /shared/data/raw_docs 경로가 없습니다. 관리자에게 문의하세요."
fi

echo ""
echo "=== 셋업 완료 ==="
echo ""
echo "Conda 환경: conda activate $CONDA_ENV_NAME"
echo "Jupyter 커널: Python ($CONDA_ENV_NAME)"
echo "프로젝트 경로: $PROJECT_DIR"
echo ""
echo "개인 노트북에서 커널을 'Python ($CONDA_ENV_NAME)'로 선택 후 사용하세요."
