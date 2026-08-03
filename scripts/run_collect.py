#!/usr/bin/env python3
"""Daily collection entrypoint (cron-friendly).

Usage:
    python scripts/run_collect.py [--config configs/sources.yaml] [--data-root DIR] [--only id1,id2]

Cron example (daily at 02:15 UTC):
    15 2 * * * cd /opt/livets-bench && .venv/bin/python scripts/run_collect.py >> logs/cron.log 2>&1
"""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from livets.collectors.runner import run  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(Path(__file__).resolve().parents[1] / "configs" / "sources.yaml"))
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--only", default=None, help="comma-separated source ids")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    only = args.only.split(",") if args.only else None
    results = run(args.config, args.data_root, only)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 1 if any("error" in r for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
