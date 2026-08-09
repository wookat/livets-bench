#!/usr/bin/env python3
"""Freeze a live evaluation round: publish an immutable input-data snapshot to R2.

At (or after) the round cutoff, this script:
  1. builds the evaluation series from the local cache with values strictly < cutoff;
  2. writes one CSV per series plus a round manifest (per-file sha256, series list,
     cutoff, protocol reference, git commit) under rounds/<round>/ locally;
  3. uploads everything to r2://{bucket}/rounds/<round>/ and refuses to overwrite
     an existing frozen round (immutability).

Participants forecast from exactly this snapshot; targets materialize afterwards.

Env: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET (default livets-snapshots)

Usage: python scripts/freeze_round.py --round 2026-09 --cutoff 2026-09-01 [--dry-run]
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from livets.eval.data_loaders import load_all  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", required=True, help="round id, e.g. 2026-09")
    parser.add_argument("--cutoff", required=True, help="ISO date; inputs strictly before this")
    parser.add_argument("--outdir", default=str(REPO / "data" / "rounds"))
    parser.add_argument("--cache-dir", default=str(REPO / "data" / "eval_cache"))
    parser.add_argument("--dry-run", action="store_true", help="build locally, skip R2 upload")
    args = parser.parse_args()

    cutoff = pd.Timestamp(args.cutoff)
    outdir = Path(args.outdir) / args.round
    outdir.mkdir(parents=True, exist_ok=True)

    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                            capture_output=True, text=True).stdout.strip()

    specs = load_all(args.cache_dir)
    files = []
    for spec in specs:
        s = spec.values[spec.values.index < cutoff]
        if len(s) < 100:
            print(f"skip {spec.series_id}: only {len(s)} pre-cutoff points")
            continue
        fname = spec.series_id.replace("/", "_").replace(":", "__") + ".csv"
        path = outdir / fname
        s.rename("value").rename_axis("date").to_csv(path)
        files.append({
            "series_id": spec.series_id, "file": fname, "domain": spec.domain,
            "season_length": spec.season_length, "n_points": len(s),
            "last_date": str(s.index[-1].date()),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })

    manifest = {
        "round": args.round, "cutoff": args.cutoff, "horizon": 14, "origins_per_cutoff": 4,
        "n_series": len(files), "protocol": "docs/protocol-prereg.md v1.0+A1",
        "git_commit": commit, "frozen_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "files": files,
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"round {args.round}: {len(files)} series frozen at {outdir}")

    if args.dry_run:
        print("dry-run: skipping R2 upload")
        return 0

    import boto3
    account = os.environ["R2_ACCOUNT_ID"]
    bucket = os.environ.get("R2_BUCKET", "livets-snapshots")
    s3 = boto3.client(
        "s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")

    prefix = f"rounds/{args.round}/"
    existing = s3.list_objects_v2(Bucket=bucket, Prefix=prefix + "manifest.json")
    if existing.get("KeyCount", 0) > 0:
        print(f"ERROR: round {args.round} already frozen on R2; rounds are immutable", file=sys.stderr)
        return 1

    for f in files:
        s3.upload_file(str(outdir / f["file"]), bucket, prefix + f["file"])
    s3.upload_file(str(outdir / "manifest.json"), bucket, prefix + "manifest.json")
    print(f"uploaded {len(files) + 1} objects to r2://{bucket}/{prefix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
