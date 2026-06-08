from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.train import run_training


def main() -> None:
    """Train one experiment from a config file and print final metrics."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    metrics = run_training(args.config, args.project_root)
    print(metrics)


if __name__ == "__main__":
    main()
