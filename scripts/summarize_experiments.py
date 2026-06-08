from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    # scripts/를 어디서 실행하든 src 패키지를 import할 수 있게 project root를 경로에 추가합니다.
    sys.path.insert(0, str(PROJECT_ROOT))

from src.experiments import SUMMARY_COLUMNS, write_experiment_summary


def main() -> None:
    """여러 실험 폴더를 비교하는 CSV/JSON 리포트를 생성합니다."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--experiments-dir", default="experiments")
    parser.add_argument("--output", default="reports/experiment_summary.csv")
    args = parser.parse_args()

    rows = write_experiment_summary(
        project_root=args.project_root,
        output_path=args.output,
        experiments_dir=args.experiments_dir,
    )
    print(f"wrote {args.output} ({len(rows)} experiments)")
    if rows:
        print(",".join(SUMMARY_COLUMNS))
        for row in rows:
            print(",".join(str(row.get(column, "")) for column in SUMMARY_COLUMNS))


if __name__ == "__main__":
    main()
