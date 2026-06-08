from __future__ import annotations

import random


def set_seed(seed: int | None) -> None:
    """Set the scaffold-level random seed when provided.

    This currently covers Python's standard `random` module. Torch/CUDA
    deterministic settings can be added here when training reproducibility
    becomes a project requirement.
    """
    if seed is None:
        return
    random.seed(seed)
