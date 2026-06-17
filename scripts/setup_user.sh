#!/bin/bash
# 팀원별 개인 환경 셋업 스크립트
# 사용법: bash setup_user.sh
# SSH 접속 후 최초 1회 실행하면 모든 환경이 자동 구성됩니다.
# 공용 conda(/opt/conda)를 사용하므로 conda 설치는 생략합니다.

set -e
echo "=== 사용자 환경 셋업 시작 ==="
echo ""

GIT_REPO="https://github.com/Codeit-Part3-6Team/Codeit-Part3-6Team-Project.git"
CONDA_DIR="/opt/conda"
CONDA_ENV_NAME="codeit-ml-pipeline"
PROJECT_DIR="$HOME/project"

# ===== 1. 공용 conda PATH 등록 =====
echo "[1/4] 공용 conda 설정..."
if [ ! -d "$CONDA_DIR" ]; then
    echo "  오류: $CONDA_DIR 가 없습니다. 관리자에게 문의하세요."
    exit 1
fi

if ! grep -q "$CONDA_DIR/bin" "$HOME/.bashrc" 2>/dev/null; then
    echo "export PATH=\"$CONDA_DIR/bin:\$PATH\"" >> "$HOME/.bashrc"
fi
"$CONDA_DIR/bin/conda" init bash --no-user
export PATH="$CONDA_DIR/bin:$PATH"
echo "  conda 경로: $CONDA_DIR"

# ===== 2. 프로젝트 클론 =====
echo "[2/4] 프로젝트 클론..."
if [ -d "$PROJECT_DIR" ]; then
    echo "  이미 클론되어 있습니다. 최신 상태로 업데이트합니다..."
    cd "$PROJECT_DIR"
    git pull
else
    git clone "$GIT_REPO" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# ===== 3. Jupyter 커널 등록 =====
echo "[3/4] Jupyter 커널 등록..."
source "$CONDA_DIR/bin/activate" "$CONDA_ENV_NAME"
python -m ipykernel install --user --name "$CONDA_ENV_NAME" --display-name "Python ($CONDA_ENV_NAME)"

# ===== 4. 데이터 경로 확인 =====
echo "[4/4] 데이터 경로 확인..."
if [ -d "/shared/data/raw_docs" ]; then
    echo "  공유 데이터 경로: /shared/data/raw_docs (준비됨)"
    echo "  문서 수: $(find /shared/data/raw_docs -type f | wc -l)개"
else
    echo "  /shared/data/raw_docs 경로가 없습니다. 관리자에게 문의하세요."
fi

echo ""
echo "=== 셋업 완료 ==="
echo ""
echo "공용 conda: $CONDA_DIR"
echo "Conda 환경: conda activate $CONDA_ENV_NAME"
echo "Jupyter 커널: Python ($CONDA_ENV_NAME)"
echo "프로젝트 경로: $PROJECT_DIR"
echo ""
echo "VS Code 사용자는 Python 인터프리터로 '$CONDA_DIR/envs/$CONDA_ENV_NAME/bin/python'을 선택하세요."
