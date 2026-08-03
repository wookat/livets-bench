"""Per-source fetch + parse functions.

Each parser takes the source config dict and returns (raw, records) where
- raw: the raw API response object(s) to be snapshotted verbatim (PIT semantics)
- records: list of tidy dicts: {series_id, timestamp, value, variable}
"""

from __future__ import annotations

import datetime as dt
import time
from typing import Any

import requests

USER_AGENT = "livets-bench/0.1 (time-series benchmark collector)"
TIMEOUT = 60


def _get(url: str, params: dict | None = None, retries: int = 3) -> Any:
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            last_exc = e
            time.sleep(2 ** attempt)
    raise last_exc


def open_meteo(source: dict) -> tuple[Any, list[dict]]:
    raw = _get(source["url"], source.get("params", {}))
    payloads = raw if isinstance(raw, list) else [raw]
    records = []
    for p in payloads:
        loc = f"{p['latitude']:.2f}_{p['longitude']:.2f}"
        hourly = p.get("hourly", {})
        times = hourly.get("time", [])
        for var, values in hourly.items():
            if var == "time":
                continue
            for t, v in zip(times, values):
                if v is None:
                    continue
                records.append({
                    "series_id": f"{source['id']}:{loc}:{var}",
                    "timestamp": t,
                    "value": float(v),
                    "variable": var,
                })
    return raw, records


def coinbase_candles(source: dict) -> tuple[Any, list[dict]]:
    raw = _get(source["url"], source.get("params", {}))
    records = []
    for ts, low, high, o, close, volume in raw:
        t = dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        records.append({"series_id": f"{source['id']}:close", "timestamp": t, "value": float(close), "variable": "close"})
        records.append({"series_id": f"{source['id']}:volume", "timestamp": t, "value": float(volume), "variable": "volume"})
    return raw, records


def frankfurter(source: dict) -> tuple[Any, list[dict]]:
    raw = _get(source["url"], source.get("params", {}))
    date = raw["date"]
    records = [
        {"series_id": f"{source['id']}:EUR{cur}", "timestamp": date, "value": float(rate), "variable": f"EUR{cur}"}
        for cur, rate in raw["rates"].items()
    ]
    return raw, records


def socrata(source: dict) -> tuple[Any, list[dict]]:
    raw = _get(source["url"], source.get("params", {}))
    records = []
    for row in raw:
        date = row.get("date")
        if not date:
            continue
        for col, val in row.items():
            if col == "date":
                continue
            try:
                v = float(val)
            except (TypeError, ValueError):
                continue
            records.append({"series_id": f"{source['id']}:{col}", "timestamp": date, "value": v, "variable": col})
    return raw, records


def neso_demand(source: dict) -> tuple[Any, list[dict]]:
    raw = _get(source["url"], source.get("params", {}))
    rows = raw["result"]["records"]
    records = []
    for row in rows:
        date = row.get("SETTLEMENT_DATE")
        period = row.get("SETTLEMENT_PERIOD")
        nd = row.get("ND")
        if date is None or period is None or nd is None:
            continue
        base = dt.datetime.fromisoformat(str(date)[:10])
        t = (base + dt.timedelta(minutes=30 * (int(period) - 1))).strftime("%Y-%m-%dT%H:%M:%S")
        records.append({"series_id": f"{source['id']}:ND", "timestamp": t, "value": float(nd), "variable": "ND"})
    return raw, records


def smard(source: dict) -> tuple[Any, list[dict]]:
    raw = _get(source["url"], source.get("params", {}))
    records = []
    for ts, v in zip(raw.get("timestamps", []), raw.get("series", []) or []):
        if v is None:
            continue
        t = dt.datetime.fromtimestamp(ts / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        records.append({"series_id": f"{source['id']}:value", "timestamp": t, "value": float(v), "variable": "value"})
    return raw, records


def wikimedia(source: dict) -> tuple[Any, list[dict]]:
    # pageviews lag 1-3 days (varies per article); walk the end date back on 404
    today = dt.datetime.now(dt.timezone.utc).date()
    raws, records = [], []
    for article in source["params"]["articles"]:
        raw = None
        for lag in range(1, 6):
            end_date = today - dt.timedelta(days=lag)
            start = (end_date - dt.timedelta(days=14)).strftime("%Y%m%d")
            url = source["url"].format(article=article, start_ymd=start, end_ymd=end_date.strftime("%Y%m%d"))
            try:
                raw = _get(url, retries=1)
                break
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 404:
                    continue
                raise
        if raw is None:
            raise RuntimeError(f"wikimedia pageviews unavailable for {article}")
        raws.append(raw)
        for item in raw.get("items", []):
            t = dt.datetime.strptime(item["timestamp"], "%Y%m%d%H").strftime("%Y-%m-%dT%H:%M:%S")
            records.append({
                "series_id": f"{source['id']}:{article}",
                "timestamp": t,
                "value": float(item["views"]),
                "variable": "views",
            })
    return raws, records


PARSERS = {
    "open_meteo": open_meteo,
    "coinbase_candles": coinbase_candles,
    "frankfurter": frankfurter,
    "socrata": socrata,
    "neso_demand": neso_demand,
    "smard": smard,
    "wikimedia": wikimedia,
}
