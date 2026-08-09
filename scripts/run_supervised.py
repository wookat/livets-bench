#!/usr/bin/env python3
"""Supervised baselines (DLinear / PatchTST / iTransformer) with leakage-safe retraining.

For each rolling cutoff, a global model is trained ONLY on observations strictly
before the cutoff (release_date := cutoff, so every cutoff is clean by
construction). Forecast windows are the same origins as scripts/run_matrix.py;
inputs at each origin are the pre-origin history (weights stay pre-cutoff).

Usage:
  .venv/bin/python scripts/run_supervised.py --models dlinear,patchtst,itransformer
"""

import argparse
import datetime as dt
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from livets.eval.backtest import origins_for_cutoff  # noqa: E402
from livets.eval.data_loaders import load_all  # noqa: E402
from livets.eval.metrics import crps_from_quantiles, mase, wql  # noqa: E402
from livets.eval.models import QUANTILE_LEVELS  # noqa: E402

DEFAULT_CUTOFFS = ["2025-01-01", "2025-07-01", "2026-01-01"]
INPUT_SIZE = 96
MAX_STEPS = 1000
LEVELS = sorted({round(abs(2 * q - 1) * 100) for q in QUANTILE_LEVELS if q != 0.5})


def build_model(name: str, horizon: int, seed: int):
    from neuralforecast.losses.pytorch import MQLoss
    loss = MQLoss(quantiles=QUANTILE_LEVELS)
    common = dict(h=horizon, input_size=INPUT_SIZE, loss=loss, max_steps=MAX_STEPS,
                  random_seed=seed, enable_progress_bar=False, logger=False)
    if name == "dlinear":
        from neuralforecast.models import DLinear
        return DLinear(**common)
    if name == "patchtst":
        from neuralforecast.models import PatchTST
        return PatchTST(**common)
    if name == "itransformer":
        from neuralforecast.models import iTransformer
        return iTransformer(n_series=1, **common)
    raise ValueError(name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default="dlinear,patchtst,itransformer")
    parser.add_argument("--cutoffs", default=",".join(DEFAULT_CUTOFFS))
    parser.add_argument("--seeds", default="0,1,2")
    parser.add_argument("--horizon", type=int, default=14)
    parser.add_argument("--cache", default=str(REPO / "data" / "eval_cache"))
    parser.add_argument("--out", default=str(REPO / "results" / "matrix-supervised.jsonl"))
    args = parser.parse_args()

    from neuralforecast import NeuralForecast

    specs = load_all(args.cache)
    print(f"loaded {len(specs)} series")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            r = json.loads(line)
            done.add((r["model"], r["series_id"], r["cutoff"], r["origin"], r["seed"]))

    git_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                                text=True).stdout.strip()
    env = {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__}

    with out_path.open("a") as f:
        for model_name in args.models.split(","):
            for cutoff in args.cutoffs.split(","):
                for seed in [int(s) for s in args.seeds.split(",")]:
                    # training set: strictly pre-cutoff observations, all series (global model)
                    train_frames = []
                    for spec in specs:
                        s = spec.values[spec.values.index < pd.Timestamp(cutoff)]
                        if len(s) < INPUT_SIZE + args.horizon + 28:
                            continue
                        train_frames.append(pd.DataFrame(
                            {"unique_id": spec.series_id, "ds": s.index, "y": s.values}))
                    train_df = pd.concat(train_frames)
                    print(f"== {model_name} cutoff={cutoff} seed={seed}: "
                          f"train {train_df.unique_id.nunique()} series, {len(train_df)} rows")
                    nf = NeuralForecast(models=[build_model(model_name, args.horizon, seed)], freq="D")
                    nf.fit(train_df)
                    col = nf.models[0].__class__.__name__

                    n_new = 0
                    for spec in specs:
                        for origin in origins_for_cutoff(spec.values, cutoff, args.horizon):
                            key = (model_name, spec.series_id, cutoff, int(origin), seed)
                            if key in done:
                                continue
                            hist = spec.values.iloc[:origin]
                            target = spec.values.iloc[origin:origin + args.horizon]
                            if len(target) < args.horizon or len(hist) < INPUT_SIZE:
                                continue
                            ctx = pd.DataFrame({"unique_id": spec.series_id,
                                                "ds": hist.index, "y": hist.values})
                            pred = nf.predict(df=ctx)
                            y_true = target.values
                            quantiles = {}
                            for q in QUANTILE_LEVELS:
                                if q == 0.5:
                                    qcol = f"{col}-median" if f"{col}-median" in pred else col
                                else:
                                    lv = round(abs(2 * q - 1) * 100)
                                    qcol = f"{col}-{'hi' if q > 0.5 else 'lo'}-{lv:.1f}"
                                quantiles[q] = pred[qcol].values[:args.horizon]
                            point = quantiles[0.5]
                            rec = {
                                "model": model_name, "release_date": cutoff, "domain": spec.domain,
                                "series_id": spec.series_id, "cutoff": cutoff, "origin": int(origin),
                                "seed": seed, "horizon": args.horizon,
                                "mase": float(mase(y_true, point, hist.values, spec.season_length)),
                                "crps": float(crps_from_quantiles(y_true, quantiles)),
                                "wql": float(wql(y_true, quantiles)),
                                "git_commit": git_commit, "env": env,
                                "run_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                                "trained_pre_cutoff": True,
                            }
                            f.write(json.dumps(rec) + "\n")
                            f.flush()
                            done.add(key)
                            n_new += 1
                    print(f"   wrote {n_new} new records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
