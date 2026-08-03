"""Forecast models for the pilot: seasonal naive + Chronos-Bolt wrapper."""

from __future__ import annotations

import numpy as np

QUANTILE_LEVELS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


def seasonal_naive(history: np.ndarray, horizon: int, season_length: int = 1) -> dict:
    """Point forecast = last season repeated; quantiles from in-sample seasonal residuals."""
    history = np.asarray(history, dtype=float)
    m = season_length
    last_season = history[-m:]
    point = np.tile(last_season, int(np.ceil(horizon / m)))[:horizon]
    residuals = history[m:] - history[:-m]
    quantiles = {}
    for q in QUANTILE_LEVELS:
        offset = np.quantile(residuals, q) if len(residuals) else 0.0
        quantiles[q] = point + offset
    return {"point": point, "quantiles": quantiles}


class ChronosBolt:
    """Wrapper around amazon/chronos-bolt-* (CPU-friendly)."""

    #: weights release date used for leakage-aware cutoffs (HF model card)
    RELEASE_DATE = "2024-11-26"

    def __init__(self, model_name: str = "amazon/chronos-bolt-small", device: str = "cpu"):
        from chronos import BaseChronosPipeline  # heavy import kept local

        self.pipeline = BaseChronosPipeline.from_pretrained(model_name, device_map=device)
        self.model_name = model_name

    def forecast(self, history: np.ndarray, horizon: int, season_length: int = 1) -> dict:
        import torch

        context = torch.tensor(np.asarray(history, dtype=np.float32))
        quantiles, mean = self.pipeline.predict_quantiles(
            inputs=context, prediction_length=horizon, quantile_levels=QUANTILE_LEVELS,
        )
        q = quantiles[0].numpy()  # (horizon, n_quantiles)
        return {
            "point": mean[0].numpy(),
            "quantiles": {lev: q[:, i] for i, lev in enumerate(QUANTILE_LEVELS)},
        }
