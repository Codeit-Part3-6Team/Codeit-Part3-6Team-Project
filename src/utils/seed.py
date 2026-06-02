from __future__ import annotations

import random


def set_seed(seed: int | None) -> None:
    if seed is None:
        return
    random.seed(seed)

