from __future__ import annotations

import random


def set_seed(seed: int | None) -> None:
    """seed가 주어졌을 때 스캐폴드 수준의 random seed를 설정합니다.

    현재는 Python 표준 `random`만 다룹니다. 학습 재현성이 더 중요해지면
    torch/cuda deterministic 설정을 이 함수에 추가하면 됩니다.
    """
    if seed is None:
        return
    random.seed(seed)
