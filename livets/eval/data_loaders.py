"""Long-history daily series loaders for the historical-simulation eval matrix.

All loaders return SeriesSpec lists with >=~1100 daily points and cache to
{cache_dir}/{series_id}.csv so repeated runs don't hammer the APIs.
"""

from __future__ import annotations

import datetime as dt
import time
from pathlib import Path

import pandas as pd
import requests

from .backtest import SeriesSpec

UA = {"User-Agent": "livets-bench/0.2 (eval matrix)"}
HISTORY_DAYS = 1200


def _safe_append(specs: list, cache: Path, sid: str, loader, season_length: int, domain: str,
                 min_points: int = 800, trim: int | None = None) -> None:
    try:
        s = _cached(cache, sid, loader)
    except Exception as e:  # noqa: BLE001 - skip unavailable series, keep the rest
        print(f"  skip {sid}: {e}")
        return
    if trim:
        s = s.iloc[-trim:]
    if len(s) < min_points:
        print(f"  skip {sid}: only {len(s)} points")
        return
    specs.append(SeriesSpec(sid, s, season_length=season_length, domain=domain))


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
    "london": (51.51, -0.13), "paris": (48.85, 2.35), "madrid": (40.42, -3.70),
    "rome": (41.90, 12.50), "moscow": (55.76, 37.62), "istanbul": (41.01, 28.98),
    "cairo": (30.04, 31.24), "lagos": (6.52, 3.38), "nairobi": (-1.29, 36.82),
    "johannesburg": (-26.20, 28.05), "mumbai": (19.08, 72.88), "delhi": (28.61, 77.21),
    "bangkok": (13.76, 100.50), "jakarta": (-6.21, 106.85), "singapore": (1.35, 103.82),
    "seoul": (37.57, 126.98), "shanghai": (31.23, 121.47), "hongkong": (22.32, 114.17),
    "la": (34.05, -118.24), "chicago": (41.88, -87.63), "houston": (29.76, -95.37),
    "toronto": (43.65, -79.38), "mexicocity": (19.43, -99.13), "bogota": (4.71, -74.07),
    "lima": (-12.05, -77.04), "santiago": (-33.45, -70.67), "buenosaires": (-34.60, -58.38),
    "auckland": (-36.85, 174.76), "perth": (-31.95, 115.86), "anchorage": (61.22, -149.90),
    "reykjavik": (64.15, -21.94), "oslo": (59.91, 10.75), "helsinki": (60.17, 24.94),
    "athens": (37.98, 23.73),
}
WEATHER_VARS = ["temperature_2m_mean", "precipitation_sum"]
AQ_CITIES = {
    "beijing": (39.90, 116.40), "delhi": (28.61, 77.21), "london": (51.51, -0.13),
    "la": (34.05, -118.24), "mexicocity": (19.43, -99.13), "jakarta": (-6.21, 106.85),
    "lahore": (31.55, 74.34), "dhaka": (23.81, 90.41), "cairo": (30.04, 31.24),
    "santiago": (-33.45, -70.67), "milan": (45.46, 9.19), "warsaw": (52.23, 21.01),
    "seoul": (37.57, 126.98), "bangkok": (13.76, 100.50), "saopaulo": (-23.55, -46.63),
    "johannesburg": (-26.20, 28.05), "istanbul": (41.01, 28.98), "tehran": (35.69, 51.39),
    "hanoi": (21.03, 105.85), "kathmandu": (27.72, 85.32),
}


def load_weather(cache: Path) -> list[SeriesSpec]:
    specs = []
    for name, (lat, lon) in CITIES.items():
        for var in WEATHER_VARS:
            short = "t2m_mean" if var == "temperature_2m_mean" else "precip_sum"
            sid = f"weather:{name}:{short}"
            _safe_append(specs, cache, sid, lambda lat=lat, lon=lon, v=var: _openmeteo_daily(
                "https://archive-api.open-meteo.com/v1/archive", lat, lon, daily_var=v), 7, "weather")
    return specs


def load_air_quality(cache: Path) -> list[SeriesSpec]:
    specs = []
    for name, (lat, lon) in AQ_CITIES.items():
        sid = f"air_quality:{name}:pm2_5_daily_mean"
        _safe_append(specs, cache, sid, lambda lat=lat, lon=lon: _openmeteo_daily(
            "https://air-quality-api.open-meteo.com/v1/air-quality", lat, lon, hourly_var="pm2_5"), 7, "air_quality")
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
    for product in ("BTC-USD", "ETH-USD", "SOL-USD", "LTC-USD", "DOGE-USD", "ADA-USD", "XRP-USD", "AVAX-USD"):
        sid = f"crypto_fx:{product}:close"
        _safe_append(specs, cache, sid, lambda p=product: _coinbase(p), 1, "crypto_fx")
    for sym in ("USD", "GBP", "JPY", "CHF", "CNY", "AUD", "CAD", "SEK", "NOK", "PLN",
                "MXN", "BRL", "INR", "KRW", "ZAR", "TRY", "SGD", "NZD", "CZK", "HUF",
                "DKK", "HKD", "ILS", "PHP", "THB", "IDR"):
        sid = f"crypto_fx:EUR{sym}:rate"
        _safe_append(specs, cache, sid, lambda x=sym: _frankfurter(x), 1, "crypto_fx", min_points=700)
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


MTA_MODES = ["Subway", "Bus", "LIRR", "MNR", "SIR", "BT", "AAR"]


def load_traffic(cache: Path) -> list[SeriesSpec]:
    specs = []
    for mode in MTA_MODES:
        sid = f"traffic:mta_{mode.lower()}:daily_ridership"
        _safe_append(specs, cache, sid, lambda m=mode: _mta(m), 7, "traffic", trim=HISTORY_DAYS)
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


SMARD_FILTERS = {"total_load": 410, "day_ahead_price": 4169, "residual_load": 4359,
                 "wind_onshore": 4067, "wind_offshore": 1225, "photovoltaic": 4068}


def load_energy(cache: Path) -> list[SeriesSpec]:
    specs = []
    for name, fid in SMARD_FILTERS.items():
        sid = f"energy:smard_de_{name}:daily"
        _safe_append(specs, cache, sid, lambda f=fid: _smard_daily(f), 7, "energy", trim=HISTORY_DAYS)
    return specs


WIKI_ARTICLES = [
    "Bitcoin", "Artificial_intelligence", "Electric_vehicle", "Inflation",
    "Climate_change", "Ethereum", "Machine_learning", "ChatGPT", "Python_(programming_language)",
    "Quantum_computing", "Solar_power", "Wind_power", "Nuclear_power", "Federal_Reserve",
    "Recession", "Stock_market", "Gold", "Crude_oil", "Interest_rate", "Unemployment",
    "Influenza", "COVID-19", "Vaccine", "Diabetes", "Hypertension",
    "World_Cup", "Olympic_Games", "Super_Bowl", "NBA", "Premier_League",
    "Taylor_Swift", "Elon_Musk", "OpenAI", "Nvidia", "Tesla,_Inc.",
    "Amazon_(company)", "Google", "Apple_Inc.", "Microsoft", "Meta_Platforms",
    "United_States", "China", "India", "Russia", "European_Union",
    "New_York_City", "London", "Tokyo", "Paris", "Dubai",
    "Cristiano_Ronaldo", "Lionel_Messi", "LeBron_James", "Formula_One", "UEFA_Champions_League",
    "Netflix", "YouTube", "TikTok", "Instagram", "Reddit",
]


def _wikimedia(article: str) -> pd.Series:
    end = dt.date.today() - dt.timedelta(days=3)
    start = end - dt.timedelta(days=HISTORY_DAYS)
    url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/"
           f"all-access/user/{article}/daily/{start:%Y%m%d}/{end:%Y%m%d}")
    for attempt in range(6):
        r = requests.get(url, headers=UA, timeout=120)
        if r.status_code != 429:
            break
        time.sleep(5 * (attempt + 1))
    r.raise_for_status()
    time.sleep(1)  # stay under the pageviews API rate limit
    items = r.json()["items"]
    return pd.Series({pd.Timestamp(i["timestamp"][:8]): float(i["views"]) for i in items}).sort_index()


def load_web_traffic(cache: Path) -> list[SeriesSpec]:
    specs = []
    for article in WIKI_ARTICLES:
        sid = f"web_traffic:{article}:pageviews"
        _safe_append(specs, cache, sid, lambda a=article: _wikimedia(a), 7, "web_traffic")
    return specs


def load_all(cache_dir: str | Path) -> list[SeriesSpec]:
    cache = Path(cache_dir)
    specs = []
    for loader in (load_weather, load_air_quality, load_crypto_fx, load_traffic, load_energy, load_web_traffic):
        specs.extend(loader(cache))
    return specs
