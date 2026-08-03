"""Historical-simulation "live" evaluation skeleton.

Protocol: for a model with weights release date D, only forecast origins with
cutoff > D count as clean scores. Input = data strictly before the origin,
target = data after the origin (as-of semantics). Rolling origins, fixed seed.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .metrics import crps_from_quantiles, mase, wql


@dataclass
class SeriesSpec:
    series_id: str
    values: pd.Series  # DatetimeIndex -> float, regular frequency
    season_length: int = 1
    domain: str = ""


@dataclass
class EvalConfig:
    horizon: int = 14
    n_origins: int = 4
    min_context: int = 90
    seed: int = 42
    release_date: str | None = None  # model weights release date (clean-score cutoff)


def rolling_origins(values: pd.Series, cfg: EvalConfig) -> list[int]:
    """Indices of forecast origins: evenly spaced over the post-release span."""
    n = len(values)
    start = cfg.min_context
    if cfg.release_date is not None:
        release = pd.Timestamp(cfg.release_date)
        after = np.searchsorted(values.index, release, side="right")
        start = max(start, int(after))
    last = n - cfg.horizon
    if last <= start:
        return []
    return list(np.unique(np.linspace(start, last, cfg.n_origins, dtype=int)))


def evaluate_model(model_fn, spec: SeriesSpec, cfg: EvalConfig) -> list[dict]:
    """model_fn(history: np.ndarray, horizon: int, season_length: int) -> {point, quantiles}."""
    np.random.seed(cfg.seed)
    results = []
    for origin in rolling_origins(spec.values, cfg):
        history = spec.values.iloc[:origin].to_numpy(dtype=float)
        target = spec.values.iloc[origin:origin + cfg.horizon].to_numpy(dtype=float)
        fc = model_fn(history, cfg.horizon, spec.season_length)
        results.append({
            "series_id": spec.series_id,
            "domain": spec.domain,
            "origin": str(spec.values.index[origin]),
            "cutoff_after_release": (
                cfg.release_date is None
                or spec.values.index[origin] > pd.Timestamp(cfg.release_date)
            ),
            "mase": mase(target, fc["point"], history, spec.season_length),
            "crps": crps_from_quantiles(target, fc["quantiles"]),
            "wql": wql(target, fc["quantiles"]),
        })
    return results


def aggregate(results: list[dict]) -> dict:
    """Geometric mean across series/origins (protocol: geo-mean + bootstrap CI later)."""
    df = pd.DataFrame(results)
    out = {}
    for metric in ("mase", "crps", "wql"):
        vals = df[metric].dropna()
        vals = vals[vals > 0]
        out[f"geomean_{metric}"] = float(np.exp(np.mean(np.log(vals)))) if len(vals) else float("nan")
    out["n_evals"] = len(df)
    return out
