"""Collection runner with PIT (point-in-time) semantics.

For each enabled source:
1. fetch raw API response and snapshot it verbatim under
   {data_root}/raw/{domain}/{source_id}/{collected_date}/{collected_ts}.json
2. append tidy records (with collected_at) to
   {data_root}/tidy/{domain}/{source_id}.csv  (append-only, dedup on load)

data_root resolution: CLI --data-root > $LIVETS_DATA_ROOT > config data_root.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import logging
import os
from pathlib import Path

import yaml

from .fetchers import PARSERS

log = logging.getLogger("livets.collect")

TIDY_COLUMNS = ["series_id", "timestamp", "value", "variable", "collected_at"]


def load_config(config_path: str | Path) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def resolve_data_root(config: dict, override: str | None = None) -> Path:
    root = override or os.environ.get("LIVETS_DATA_ROOT") or config.get("data_root", "./data")
    return Path(root).expanduser().resolve()


def collect_source(source: dict, data_root: Path) -> dict:
    collected_at = dt.datetime.now(dt.timezone.utc)
    ts_str = collected_at.strftime("%Y%m%dT%H%M%SZ")
    parser = PARSERS[source["parser"]]
    raw, records = parser(source)

    raw_dir = data_root / "raw" / source["domain"] / source["id"] / collected_at.strftime("%Y-%m-%d")
    raw_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = raw_dir / f"{ts_str}.json"
    with open(snapshot_path, "w") as f:
        json.dump({"collected_at": collected_at.isoformat(), "source": source, "raw": raw}, f)

    tidy_dir = data_root / "tidy" / source["domain"]
    tidy_dir.mkdir(parents=True, exist_ok=True)
    tidy_path = tidy_dir / f"{source['id']}.csv"
    new_file = not tidy_path.exists()
    with open(tidy_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TIDY_COLUMNS)
        if new_file:
            writer.writeheader()
        for r in records:
            r["collected_at"] = collected_at.isoformat()
            writer.writerow(r)

    n_series = len({r["series_id"] for r in records})
    return {
        "source_id": source["id"],
        "domain": source["domain"],
        "collected_at": collected_at.isoformat(),
        "n_records": len(records),
        "n_series": n_series,
        "snapshot": str(snapshot_path.relative_to(data_root)),
    }


def run(config_path: str | Path, data_root_override: str | None = None,
        only: list[str] | None = None) -> list[dict]:
    config = load_config(config_path)
    data_root = resolve_data_root(config, data_root_override)
    results = []
    for source in config["sources"]:
        if not source.get("enabled", True):
            continue
        if only and source["id"] not in only:
            continue
        try:
            summary = collect_source(source, data_root)
            log.info("OK %s: %d records, %d series", source["id"], summary["n_records"], summary["n_series"])
        except Exception as e:  # noqa: BLE001 - one bad source must not kill the run
            summary = {"source_id": source["id"], "domain": source["domain"], "error": str(e)}
            log.error("FAIL %s: %s", source["id"], e)
        results.append(summary)

    log_dir = data_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    run_ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with open(log_dir / f"collect_{run_ts}.json", "w") as f:
        json.dump(results, f, indent=2)
    return results
