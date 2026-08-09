#!/usr/bin/env python3
"""Collection pipeline health check.

Scans {data_root}/logs/collect_*.json for the most recent run and reports:
- whether a run happened within --max-age-hours
- per-source status of the latest run (errors, record counts)
Exit code 0 = healthy, 1 = stale or has failing sources.

Usage: python scripts/health_check.py [--data-root DIR] [--max-age-hours 30]
"""

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from livets.collectors.runner import load_config, resolve_data_root  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(Path(__file__).resolve().parents[1] / "configs" / "sources.yaml"))
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--max-age-hours", type=float, default=30)
    args = parser.parse_args()

    data_root = resolve_data_root(load_config(args.config), args.data_root)
    logs = sorted((data_root / "logs").glob("collect_*.json"))
    if not logs:
        print("UNHEALTHY: no collection runs found")
        return 1
    latest = logs[-1]
    ts = dt.datetime.strptime(latest.stem.split("_")[1], "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
    age_h = (dt.datetime.now(dt.timezone.utc) - ts).total_seconds() / 3600
    results = json.loads(latest.read_text())
    errors = [r for r in results if "error" in r]

    print(f"latest run: {ts.isoformat()} ({age_h:.1f}h ago), "
          f"{len(results) - len(errors)}/{len(results)} sources OK")
    for r in errors:
        print(f"  FAIL {r['source_id']}: {r['error']}")
    if age_h > args.max_age_hours:
        print(f"UNHEALTHY: last run older than {args.max_age_hours}h")
        return 1
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
