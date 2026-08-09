#!/usr/bin/env python3
"""Full evaluation matrix: models x domains x rolling cutoffs x seeds -> JSONL.

Every JSONL record is self-describing (model, release_date, cutoff, origin,
seed, metrics, env, git commit, run timestamp) for full provenance.

Usage:
    python scripts/run_matrix.py --models seasonal_naive,chronos-bolt-small \
        [--cutoffs 2025-01-01,2025-07-01,2026-01-01] [--seeds 0,1,2] \
        [--horizon 14] [--out results/matrix.jsonl]

Sampling-based models run all seeds; deterministic models run seed 0 only.
Existing (model, series_id, cutoff, origin, seed) records are skipped, so the
matrix can be filled incrementally (also from per-family venvs).
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

from livets.eval.backtest import evaluate_window, origins_for_cutoff  # noqa: E402
from livets.eval.data_loaders import load_all  # noqa: E402
from livets.eval.model_zoo import MODEL_ZOO  # noqa: E402


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def existing_keys(out: Path) -> set:
    keys = set()
    if out.exists():
        for line in out.read_text().splitlines():
            try:
                r = json.loads(line)
                keys.add((r["model"], r["series_id"], r["cutoff"], r["origin"], r["seed"]))
            except json.JSONDecodeError:
                continue
    return keys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", required=True, help="comma-separated model names from MODEL_ZOO")
    parser.add_argument("--cutoffs", default="2025-01-01,2025-07-01,2026-01-01")
    parser.add_argument("--seeds", default="0,1,2", help="used only for non-deterministic models")
    parser.add_argument("--horizon", type=int, default=14)
    parser.add_argument("--n-origins", type=int, default=4)
    parser.add_argument("--window-days", type=int, default=180)
    parser.add_argument("--cache-dir", default=str(REPO / "data" / "eval_cache"))
    parser.add_argument("--out", default=str(REPO / "results" / "matrix.jsonl"))
    args = parser.parse_args()

    cutoffs = args.cutoffs.split(",")
    seeds = [int(s) for s in args.seeds.split(",")]
    specs = load_all(args.cache_dir)
    print(f"loaded {len(specs)} series across {len({s.domain for s in specs})} domains")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = existing_keys(out)
    commit = git_commit()
    env = {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__}

    for model_name in args.models.split(","):
        zoo = MODEL_ZOO[model_name]
        model_seeds = seeds if not zoo["deterministic"] else [0]
        print(f"== {model_name} (release={zoo['release_date']}, seeds={model_seeds})")
        fn = zoo["factory"]()
        n_new = 0
        with open(out, "a") as f:
            for spec in specs:
                for cutoff in cutoffs:
                    # future-only: cutoff must postdate the model's weight release
                    if zoo["release_date"] and cutoff <= zoo["release_date"]:
                        continue
                    for origin in origins_for_cutoff(spec.values, cutoff, args.horizon,
                                                     args.n_origins, args.window_days):
                        for seed in model_seeds:
                            origin_date = str(spec.values.index[origin].date())
                            key = (model_name, spec.series_id, cutoff, origin_date, seed)
                            if key in done:
                                continue
                            rec = evaluate_window(fn, spec, origin, args.horizon, seed)
                            rec.update({
                                "model": model_name,
                                "release_date": zoo["release_date"],
                                "cutoff": cutoff,
                                "horizon": args.horizon,
                                "git_commit": commit,
                                "env": env,
                                "run_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                            })
                            f.write(json.dumps(rec) + "\n")
                            f.flush()
                            done.add(key)
                            n_new += 1
        print(f"   wrote {n_new} new records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
