"""Evaluation metrics: MASE, quantile loss / WQL, CRPS (quantile approximation)."""

from __future__ import annotations

import numpy as np


def mase(y_true: np.ndarray, y_pred: np.ndarray, y_train: np.ndarray, season_length: int = 1) -> float:
    """Mean Absolute Scaled Error, scaled by in-sample seasonal naive MAE."""
    y_true, y_pred, y_train = map(np.asarray, (y_true, y_pred, y_train))
    scale = np.mean(np.abs(y_train[season_length:] - y_train[:-season_length]))
    if scale == 0 or np.isnan(scale):
        return float("nan")
    return float(np.mean(np.abs(y_true - y_pred)) / scale)


def quantile_loss(y_true: np.ndarray, q_pred: np.ndarray, q: float) -> np.ndarray:
    """Pinball loss for quantile level q. q_pred shape == y_true shape."""
    diff = y_true - q_pred
    return np.maximum(q * diff, (q - 1) * diff)


def wql(y_true: np.ndarray, quantile_preds: dict[float, np.ndarray]) -> float:
    """Weighted Quantile Loss: 2 * sum_q pinball / sum |y|."""
    y_true = np.asarray(y_true)
    denom = np.sum(np.abs(y_true))
    if denom == 0:
        return float("nan")
    per_q = [np.sum(quantile_loss(y_true, np.asarray(p), q)) for q, p in quantile_preds.items()]
    return float(2 * np.mean(per_q) / denom)


def crps_from_quantiles(y_true: np.ndarray, quantile_preds: dict[float, np.ndarray]) -> float:
    """CRPS approximated by averaging pinball loss over quantile levels (x2).

    With a dense quantile grid this converges to the true CRPS.
    """
    y_true = np.asarray(y_true)
    levels = sorted(quantile_preds)
    losses = [np.mean(quantile_loss(y_true, np.asarray(quantile_preds[q]), q)) for q in levels]
    return float(2 * np.mean(losses))
