#!/bin/bash
# GCP VM ì´ˆê¸° ?‹ì—… ?¤í¬ë¦½íŠ¸
# ?¬ìš©ë²? bash scripts/setup_vm.sh
# VM ?ì„± ì§í›„ ??ë²ˆë§Œ ?¤í–‰?˜ë©´ ëª¨ë“  ?˜ê²½???ë™ êµ¬ì„±?©ë‹ˆ??

set -e
echo "=== GCP VM ?˜ê²½ ?‹ì—… ?œì‘ ==="
echo ""

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONDA_ENV_NAME="codeit-ml-pipeline"

# ===== 1. ?œìŠ¤???¨í‚¤ì§€ =====
echo "[1/9] ?œìŠ¤???¨í‚¤ì§€ ?¤ì¹˜..."
sudo apt-get update -qq
sudo apt-get install -y -qq curl zstd python3-pip python3-venv nodejs npm

# ===== 1.5. ê³µìœ  ?°ì´???”ë ‰?°ë¦¬ ?ì„± =====
echo "[1.5/9] ê³µìœ  ?°ì´???”ë ‰?°ë¦¬ ?ì„±..."
sudo mkdir -p /shared/data/raw_docs
sudo chmod -R 755 /shared
echo "  ê³µìœ  ?°ì´??ê²½ë¡œ: /shared/data/raw_docs"

# ===== 2. Miniconda ?¤ì¹˜ =====
echo "[2/8] Miniconda ?¤ì¹˜..."
if ! command -v conda &> /dev/null; then
    MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    MINICONDA_SCRIPT="/tmp/miniconda_install.sh"
    curl -fsSL "$MINICONDA_URL" -o "$MINICONDA_SCRIPT"
    bash "$MINICONDA_SCRIPT" -b -p "$HOME/miniconda3"
    rm "$MINICONDA_SCRIPT"
    "$HOME/miniconda3/bin/conda" init bash
    source "$HOME/.bashrc"
else
    echo "  ?´ë? ?¤ì¹˜??
fi

export PATH="$HOME/miniconda3/bin:$PATH"

# ===== 3. Conda ?˜ê²½ ?ì„± =====
echo "[3/8] Conda ?˜ê²½ ?ì„± ($CONDA_ENV_NAME)..."
cd "$PROJECT_ROOT"
if conda env list | grep -q "$CONDA_ENV_NAME"; then
    echo "  ?˜ê²½???´ë? ì¡´ì¬?©ë‹ˆ?? ?…ë°?´íŠ¸?©ë‹ˆ??.."
    conda env update -f environment.yml --prune
else
    conda env create -f environment.yml
fi

# ===== 4. Conda ?˜ê²½??Jupyter ì»¤ë„ë¡??±ë¡ =====
echo "[4/8] Conda ?˜ê²½??Jupyter ì»¤ë„ë¡??±ë¡..."
source "$HOME/miniconda3/bin/activate" "$CONDA_ENV_NAME"
python -m ipykernel install --user --name "$CONDA_ENV_NAME" --display-name "Python ($CONDA_ENV_NAME)"
pip install ipykernel jupyterlab-git --quiet

# ===== 5. Ollama ?¤ì¹˜ =====
echo "[5/8] Ollama ?¤ì¹˜..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "  ?´ë? ?¤ì¹˜??
fi

# ===== 6. Ollama ?œë²„ ?œì‘ + ëª¨ë¸ ?¤ìš´ë¡œë“œ =====
echo "[6/8] Ollama ?œë²„ ?œì‘ ë°?ëª¨ë¸ ?¤ìš´ë¡œë“œ..."
if ! pgrep -x "ollama" > /dev/null; then
    ollama serve &
    sleep 5
fi
ollama pull gemma4:e2b

# ===== 7. rclone ?¤ì • ?ˆë‚´ =====
echo "[7/8] rclone ?¤ì • ?ˆë‚´"
if ! command -v rclone &> /dev/null; then
    sudo apt-get install -y -qq rclone
fi
echo ""
echo "  rclone ?¤ì •???„ìš”?©ë‹ˆ?? ?„ë˜ ëª…ë ¹?´ë? ?¤í–‰?˜ê³  Google Drive ?¸ì¦???„ë£Œ?˜ì„¸??"
echo "    rclone config"
echo "    ??n (new remote)"
echo "    ??name: gdrive"
echo "    ??storage: drive (Google Drive)"
echo "    ???´í›„ Enterë¡?ê¸°ë³¸ê°? ë¸Œë¼?°ì??ì„œ ?¸ì¦"
echo ""

# ===== 8. ?°ì´??ê°€?¸ì˜¤ê¸?=====
echo "[8/8] Drive?ì„œ ?°ì´??ê°€?¸ì˜¤ê¸?
echo "  rclone ?¤ì • ?„ë£Œ ???„ë˜ ëª…ë ¹?´ë¡œ ?°ì´?°ë? ê°€?¸ì˜¤?¸ìš”:"
echo "    bash scripts/sync_data.sh pull"
echo ""

echo "=== ?‹ì—… ?„ë£Œ ==="
echo ""
echo "ê³µìœ  ?°ì´??ê²½ë¡œ: /shared/data/raw_docs"
echo "Conda ?˜ê²½: conda activate $CONDA_ENV_NAME"
echo "Jupyter ì»¤ë„: Python ($CONDA_ENV_NAME)"
echo ""
echo "?¤ìŒ ?¨ê³„:"
echo "  1. rclone config (Google Drive ?°ë™)"
echo "  2. bash scripts/sync_data.sh pull (?°ì´??ê°€?¸ì˜¤ê¸?"
echo "  3. python scripts/check_rag_pipeline.py --config configs/experiments/rag/rag_langchain.yaml --project-root ."
echo "  4. ë°±ì—… ?ë™?? crontab -e ??0 3 * * * bash $PROJECT_ROOT/scripts/sync_data.sh push"
echo ""
echo "=== ?€?ë³„ ?„ë¡œ?íŠ¸ ?´ë¡  ==="
echo "  ê°ì JupyterHub ?°ë??ì—???¤í–‰:"
echo "    git clone https://github.com/Codeit-Part3-6Team/Codeit-Part3-6Team-Project.git ~/project"
echo "    cd ~/project"
echo "    conda activate $CONDA_ENV_NAME"
