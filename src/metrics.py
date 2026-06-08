from __future__ import annotations


def accuracy(y_true: list[str], y_pred: list[str]) -> float:
    """같은 길이의 정답/예측 label 목록으로 단순 accuracy를 계산합니다."""
    if not y_true:
        return 0.0
    return sum(true == pred for true, pred in zip(y_true, y_pred)) / len(y_true)
