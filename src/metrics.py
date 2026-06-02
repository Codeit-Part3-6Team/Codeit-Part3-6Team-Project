from __future__ import annotations


def accuracy(y_true: list[str], y_pred: list[str]) -> float:
    if not y_true:
        return 0.0
    return sum(true == pred for true, pred in zip(y_true, y_pred)) / len(y_true)

