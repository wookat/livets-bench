"""Model registry for the evaluation matrix.

Each entry: release_date (HF hub createdAt, conservative earliest-provable),
deterministic flag, and a factory returning
    forecast_fn(history, horizon, season_length, seed) -> {"point", "quantiles" | None}
Imports are lazy so each model family can live in its own venv if needed.
"""

from __future__ import annotations

import os

import numpy as np

from .models import QUANTILE_LEVELS, seasonal_naive

DEVICE = os.environ.get("LIVETS_DEVICE", "cpu")


def _seasonal_naive_factory():
    def fn(history, horizon, season_length, seed=0):
        return seasonal_naive(history, horizon, season_length)
    return fn


def _chronos_factory(model_name: str, sampling: bool):
    from chronos import BaseChronosPipeline
    import torch

    pipeline = BaseChronosPipeline.from_pretrained(model_name, device_map=DEVICE)

    def fn(history, horizon, season_length, seed=0):
        if sampling:
            torch.manual_seed(seed)
        context = torch.tensor(np.asarray(history, dtype=np.float32))
        quantiles, mean = pipeline.predict_quantiles(
            inputs=context, prediction_length=horizon, quantile_levels=QUANTILE_LEVELS)
        q = quantiles[0].cpu().numpy()
        return {"point": mean[0].cpu().numpy(),
                "quantiles": {lev: q[:, i] for i, lev in enumerate(QUANTILE_LEVELS)}}
    return fn


def _timemoe_factory(model_name: str = "Maple728/TimeMoE-50M"):
    import torch
    from transformers import AutoModelForCausalLM

    model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True,
                                                 torch_dtype=torch.float32).to(DEVICE)
    model.eval()

    def fn(history, horizon, season_length, seed=0):
        x = np.asarray(history, dtype=np.float32)[-2048:]
        mean, std = x.mean(), x.std() + 1e-8
        inp = torch.tensor((x - mean) / std).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            out = model.generate(inp, max_new_tokens=horizon)
        pred = out[0, -horizon:].cpu().numpy() * std + mean
        return {"point": pred, "quantiles": None}  # point-only model
    return fn


def _timesfm_factory(repo_id: str = "google/timesfm-2.5-200m-pytorch"):
    import timesfm

    tfm = timesfm.TimesFM_2p5_200M_torch.from_pretrained(repo_id)
    tfm.compile(timesfm.ForecastConfig(
        max_context=1024, max_horizon=64, normalize_inputs=True,
        use_continuous_quantile_head=True, fix_quantile_crossing=True))

    def fn(history, horizon, season_length, seed=0):
        x = np.asarray(history, dtype=np.float32)[-1024:]
        point, quantile_fc = tfm.forecast(horizon=horizon, inputs=[x])
        q = quantile_fc[0]  # (horizon, 1 + 9); cols 1..9 are deciles 0.1..0.9
        return {"point": point[0][:horizon],
                "quantiles": {lev: q[:horizon, i + 1] for i, lev in enumerate(QUANTILE_LEVELS)}}
    return fn


def _moirai_factory(model_name: str = "Salesforce/moirai-1.1-R-small", num_samples: int = 100):
    import torch
    from uni2ts.model.moirai import MoiraiForecast, MoiraiModule

    module = MoiraiModule.from_pretrained(model_name)

    from gluonts.dataset.common import ListDataset

    def fn(history, horizon, season_length, seed=0):
        torch.manual_seed(seed)
        x = np.asarray(history, dtype=np.float32)[-2048:]
        model = MoiraiForecast(module=module, prediction_length=horizon, context_length=len(x),
                               patch_size="auto", num_samples=num_samples,
                               target_dim=1, feat_dynamic_real_dim=0, past_feat_dynamic_real_dim=0)
        predictor = model.create_predictor(batch_size=1, device=DEVICE)
        ds = ListDataset([{"target": x, "start": "2000-01-01"}], freq="D")
        forecast = next(iter(predictor.predict(ds)))
        samples = forecast.samples[:, :, 0] if forecast.samples.ndim == 3 else forecast.samples
        return {"point": np.median(samples, axis=0),
                "quantiles": {lev: np.quantile(samples, lev, axis=0) for lev in QUANTILE_LEVELS}}
    return fn


MODEL_ZOO: dict[str, dict] = {
    "seasonal_naive": {"release_date": None, "deterministic": True,
                       "factory": _seasonal_naive_factory},
    "chronos-bolt-small": {"release_date": "2024-11-25", "deterministic": True,
                           "factory": lambda: _chronos_factory("amazon/chronos-bolt-small", sampling=False)},
    "chronos-bolt-base": {"release_date": "2024-11-25", "deterministic": True,
                          "factory": lambda: _chronos_factory("amazon/chronos-bolt-base", sampling=False)},
    "chronos-t5-small": {"release_date": "2024-02-21", "deterministic": False,
                         "factory": lambda: _chronos_factory("amazon/chronos-t5-small", sampling=True)},
    "time-moe-50m": {"release_date": "2024-09-21", "deterministic": True,
                     "factory": _timemoe_factory},
    "timesfm-2.5-200m": {"release_date": "2025-09-02", "deterministic": True,
                         "factory": _timesfm_factory},
    "moirai-1.1-r-small": {"release_date": "2024-06-14", "deterministic": False,
                           "factory": _moirai_factory},
}
