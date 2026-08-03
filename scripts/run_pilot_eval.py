#!/usr/bin/env python3
"""Pilot historical-simulation eval: seasonal naive vs Chronos-Bolt.

Downloads a few daily series with long public history (weather / BTC / FX /
pageviews), splits at the Chronos-Bolt weights release date (2024-11-26), and
evaluates MASE / CRPS / WQL on post-release data only.

Usage:
    python scripts/run_pilot_eval.py [--horizon 14] [--n-origins 4] [--skip-chronos] [--out results/pilot.json]
"""

import argparse
import datetime as dt
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from livets.eval.backtest import EvalConfig, SeriesSpec, aggregate, evaluate_model  # noqa: E402
from livets.eval.models import ChronosBolt, seasonal_naive  # noqa: E402

UA = {"User-Agent": "livets-bench/0.1 (pilot eval)"}


def load_openmeteo_archive(lat: float, lon: float, name: str) -> SeriesSpec:
    end = dt.date.today() - dt.timedelta(days=3)
    start = end - dt.timedelta(days=1200)
    r = requests.get("https://archive-api.open-meteo.com/v1/archive", params={
        "latitude": lat, "longitude": lon, "start_date": str(start), "end_date": str(end),
        "daily": "temperature_2m_mean", "timezone": "UTC",
    }, headers=UA, timeout=120)
    r.raise_for_status()
    d = r.json()["daily"]
    s = pd.Series(d["temperature_2m_mean"], index=pd.to_datetime(d["time"]), dtype=float).dropna()
    return SeriesSpec(f"weather:{name}:t2m_mean", s, season_length=7, domain="weather")


def load_coinbase_btc() -> SeriesSpec:
    frames = []
    end = dt.datetime.now(dt.timezone.utc)
    for _ in range(5):  # 5 * 300 daily candles
        start = end - dt.timedelta(days=300)
        r = requests.get("https://api.exchange.coinbase.com/products/BTC-USD/candles", params={
            "granularity": 86400, "start": start.isoformat(), "end": end.isoformat(),
        }, headers=UA, timeout=120)
        r.raise_for_status()
        rows = r.json()
        if not rows:
            break
        df = pd.DataFrame(rows, columns=["ts", "low", "high", "open", "close", "volume"])
        frames.append(df)
        end = start
    df = pd.concat(frames)
    s = pd.Series(df["close"].values, index=pd.to_datetime(df["ts"], unit="s")).sort_index()
    s = s[~s.index.duplicated()].astype(float)
    return SeriesSpec("crypto:BTC-USD:close", s, season_length=1, domain="crypto_fx")


def load_frankfurter(pair: str = "USD") -> SeriesSpec:
    start = (dt.date.today() - dt.timedelta(days=1200)).isoformat()
    r = requests.get(f"https://api.frankfurter.dev/v1/{start}..", params={"symbols": pair}, headers=UA, timeout=120)
    r.raise_for_status()
    rates = r.json()["rates"]
    s = pd.Series({pd.Timestamp(d): v[pair] for d, v in rates.items()}).sort_index().astype(float)
    return SeriesSpec(f"fx:EUR{pair}", s, season_length=1, domain="crypto_fx")


def load_wikimedia(article: str) -> SeriesSpec:
    end = dt.date.today() - dt.timedelta(days=2)
    start = end - dt.timedelta(days=1200)
    url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/"
           f"all-access/user/{article}/daily/{start:%Y%m%d}/{end:%Y%m%d}")
    r = requests.get(url, headers=UA, timeout=120)
    r.raise_for_status()
    items = r.json()["items"]
    s = pd.Series({pd.Timestamp(i["timestamp"][:8]): float(i["views"]) for i in items}).sort_index()
    return SeriesSpec(f"web_traffic:{article}", s, season_length=7, domain="web_traffic")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon", type=int, default=14)
    parser.add_argument("--n-origins", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-chronos", action="store_true")
    parser.add_argument("--out", default="results/pilot.json")
    args = parser.parse_args()

    specs = [
        load_openmeteo_archive(52.52, 13.41, "berlin"),
        load_openmeteo_archive(40.71, -74.01, "nyc"),
        load_coinbase_btc(),
        load_frankfurter("USD"),
        load_wikimedia("Bitcoin"),
        load_wikimedia("Artificial_intelligence"),
    ]
    for s in specs:
        print(f"loaded {s.series_id}: {len(s.values)} points [{s.values.index[0].date()} .. {s.values.index[-1].date()}]")

    cfg = EvalConfig(horizon=args.horizon, n_origins=args.n_origins, seed=args.seed,
                     release_date=ChronosBolt.RELEASE_DATE)

    models = {"seasonal_naive": seasonal_naive}
    if not args.skip_chronos:
        chronos = ChronosBolt()
        models["chronos-bolt-small"] = chronos.forecast

    all_results, summary = {}, {}
    for name, fn in models.items():
        res = []
        for spec in specs:
            res.extend(evaluate_model(fn, spec, cfg))
        all_results[name] = res
        summary[name] = aggregate(res)
        print(name, json.dumps(summary[name], indent=2))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "config": vars(args),
        "release_date_cutoff": ChronosBolt.RELEASE_DATE,
        "run_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "env": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__},
        "summary": summary,
        "per_window": all_results,
    }
    with open(out, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"written {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
