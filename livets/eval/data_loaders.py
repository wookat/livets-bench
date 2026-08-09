"""Long-history daily series loaders for the historical-simulation eval matrix.

All loaders return SeriesSpec lists with >=~1100 daily points and cache to
{cache_dir}/{series_id}.csv so repeated runs don't hammer the APIs.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import requests

from .backtest import SeriesSpec

UA = {"User-Agent": "livets-bench/0.2 (eval matrix)"}
HISTORY_DAYS = 1200


def _cached(cache_dir: Path, series_id: str, loader) -> pd.Series:
    path = cache_dir / (series_id.replace(":", "__").replace("/", "_") + ".csv")
    if path.exists():
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        return df["value"].astype(float)
    s = loader()
    path.parent.mkdir(parents=True, exist_ok=True)
    s.rename("value").to_frame().to_csv(path)
    return s


def _openmeteo_daily(host: str, lat: float, lon: float, daily_var: str | None = None,
                     hourly_var: str | None = None) -> pd.Series:
    end = dt.date.today() - dt.timedelta(days=3)
    start = end - dt.timedelta(days=HISTORY_DAYS)
    params = {"latitude": lat, "longitude": lon, "start_date": str(start), "end_date": str(end), "timezone": "UTC"}
    if daily_var:
        params["daily"] = daily_var
    else:
        params["hourly"] = hourly_var
    r = requests.get(host, params=params, headers=UA, timeout=180)
    r.raise_for_status()
    j = r.json()
    if daily_var:
        d = j["daily"]
        return pd.Series(d[daily_var], index=pd.to_datetime(d["time"]), dtype=float).dropna()
    h = j["hourly"]
    s = pd.Series(h[hourly_var], index=pd.to_datetime(h["time"]), dtype=float)
    return s.resample("1D").mean().dropna()


CITIES = {
    "berlin": (52.52, 13.41), "nyc": (40.71, -74.01), "beijing": (39.90, 116.40),
    "tokyo": (35.68, 139.69), "sydney": (-33.87, 151.21), "saopaulo": (-23.55, -46.63),
}
AQ_CITIES = {"beijing": (39.90, 116.40), "delhi": (28.61, 77.21), "london": (51.51, -0.13), "la": (34.05, -118.24)}


def load_weather(cache: Path) -> list[SeriesSpec]:
    specs = []
    for name, (lat, lon) in CITIES.items():
        sid = f"weather:{name}:t2m_mean"
        s = _cached(cache, sid, lambda lat=lat, lon=lon: _openmeteo_daily(
            "https://archive-api.open-meteo.com/v1/archive", lat, lon, daily_var="temperature_2m_mean"))
        specs.append(SeriesSpec(sid, s, season_length=7, domain="weather"))
    return specs


def load_air_quality(cache: Path) -> list[SeriesSpec]:
    specs = []
    for name, (lat, lon) in AQ_CITIES.items():
        sid = f"air_quality:{name}:pm2_5_daily_mean"
        s = _cached(cache, sid, lambda lat=lat, lon=lon: _openmeteo_daily(
            "https://air-quality-api.open-meteo.com/v1/air-quality", lat, lon, hourly_var="pm2_5"))
        specs.append(SeriesSpec(sid, s, season_length=7, domain="air_quality"))
    return specs


def _coinbase(product: str) -> pd.Series:
    frames = []
    end = dt.datetime.now(dt.timezone.utc)
    for _ in range(5):
        start = end - dt.timedelta(days=300)
        r = requests.get(f"https://api.exchange.coinbase.com/products/{product}/candles", params={
            "granularity": 86400, "start": start.isoformat(), "end": end.isoformat()}, headers=UA, timeout=120)
        r.raise_for_status()
        rows = r.json()
        if not rows:
            break
        frames.append(pd.DataFrame(rows, columns=["ts", "low", "high", "open", "close", "volume"]))
        end = start
    df = pd.concat(frames)
    s = pd.Series(df["close"].values, index=pd.to_datetime(df["ts"], unit="s")).sort_index()
    return s[~s.index.duplicated()].astype(float)


def _frankfurter(symbol: str) -> pd.Series:
    start = (dt.date.today() - dt.timedelta(days=HISTORY_DAYS)).isoformat()
    r = requests.get(f"https://api.frankfurter.dev/v1/{start}..", params={"symbols": symbol}, headers=UA, timeout=120)
    r.raise_for_status()
    rates = r.json()["rates"]
    return pd.Series({pd.Timestamp(d): v[symbol] for d, v in rates.items()}).sort_index().astype(float)


def load_crypto_fx(cache: Path) -> list[SeriesSpec]:
    specs = []
    for product in ("BTC-USD", "ETH-USD"):
        sid = f"crypto_fx:{product}:close"
        s = _cached(cache, sid, lambda p=product: _coinbase(p))
        specs.append(SeriesSpec(sid, s, season_length=1, domain="crypto_fx"))
    for sym in ("USD", "GBP", "JPY"):
        sid = f"crypto_fx:EUR{sym}:rate"
        s = _cached(cache, sid, lambda x=sym: _frankfurter(x))
        specs.append(SeriesSpec(sid, s, season_length=1, domain="crypto_fx"))
    return specs


def _mta(mode: str) -> pd.Series:
    # "MTA Daily Ridership and Traffic: Beginning 2020" (successor of vxuj-8kew, still updated)
    r = requests.get("https://data.ny.gov/resource/sayj-mze2.json", params={
        "$order": "date", "$limit": 50000, "$where": f"mode='{mode}'",
        "$select": "date,count"}, headers=UA, timeout=180)
    r.raise_for_status()
    rows = r.json()
    s = pd.Series({pd.Timestamp(row["date"][:10]): float(row["count"]) for row in rows if row.get("count")})
    return s.sort_index()


MTA_MODES = ["Subway", "Bus", "LIRR", "MNR"]


def load_traffic(cache: Path) -> list[SeriesSpec]:
    specs = []
    for mode in MTA_MODES:
        sid = f"traffic:mta_{mode.lower()}:daily_ridership"
        s = _cached(cache, sid, lambda m=mode: _mta(m))
        specs.append(SeriesSpec(sid, s.iloc[-HISTORY_DAYS:], season_length=7, domain="traffic"))
    return specs


def _smard_daily(filter_id: int) -> pd.Series:
    idx = requests.get(f"https://www.smard.de/app/chart_data/{filter_id}/DE/index_day.json",
                       headers=UA, timeout=120).json()["timestamps"]
    cutoff_ms = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=HISTORY_DAYS + 400)).timestamp() * 1000
    frames = {}
    for ts in [t for t in idx if t >= cutoff_ms]:
        j = requests.get(f"https://www.smard.de/app/chart_data/{filter_id}/DE/{filter_id}_DE_day_{ts}.json",
                         headers=UA, timeout=120).json()
        for t, v in j.get("series", []):
            if v is not None:
                frames[pd.Timestamp(t, unit="ms")] = float(v)
    return pd.Series(frames).sort_index()


SMARD_FILTERS = {"total_load": 410, "day_ahead_price": 4169}


def load_energy(cache: Path) -> list[SeriesSpec]:
    specs = []
    for name, fid in SMARD_FILTERS.items():
        sid = f"energy:smard_de_{name}:daily"
        try:
            s = _cached(cache, sid, lambda f=fid: _smard_daily(f))
        except Exception:  # noqa: BLE001 - optional secondary series
            continue
        specs.append(SeriesSpec(sid, s.iloc[-HISTORY_DAYS:], season_length=7, domain="energy"))
    return specs


WIKI_ARTICLES = ["Bitcoin", "Artificial_intelligence", "Electric_vehicle", "Inflation"]


def _wikimedia(article: str) -> pd.Series:
    end = dt.date.today() - dt.timedelta(days=3)
    start = end - dt.timedelta(days=HISTORY_DAYS)
    url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/"
           f"all-access/user/{article}/daily/{start:%Y%m%d}/{end:%Y%m%d}")
    r = requests.get(url, headers=UA, timeout=120)
    r.raise_for_status()
    items = r.json()["items"]
    return pd.Series({pd.Timestamp(i["timestamp"][:8]): float(i["views"]) for i in items}).sort_index()


def load_web_traffic(cache: Path) -> list[SeriesSpec]:
    specs = []
    for article in WIKI_ARTICLES:
        sid = f"web_traffic:{article}:pageviews"
        s = _cached(cache, sid, lambda a=article: _wikimedia(a))
        specs.append(SeriesSpec(sid, s, season_length=7, domain="web_traffic"))
    return specs


def load_all(cache_dir: str | Path) -> list[SeriesSpec]:
    cache = Path(cache_dir)
    specs = []
    for loader in (load_weather, load_air_quality, load_crypto_fx, load_traffic, load_energy, load_web_traffic):
        specs.extend(loader(cache))
    return specs
