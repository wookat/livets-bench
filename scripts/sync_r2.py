#!/usr/bin/env python3
"""Archive raw snapshots to Cloudflare R2 with sha256 manifest (audit trail).

Uploads every file under {data_root}/raw/ not yet in the manifest to
s3://{bucket}/raw/... and appends {key, sha256, size, uploaded_at} to
{data_root}/logs/r2_manifest.jsonl (also mirrored to R2).

Env: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET (default livets-snapshots)

Usage: python scripts/sync_r2.py [--data-root DIR]
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

import boto3

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from livets.collectors.runner import load_config, resolve_data_root  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(Path(__file__).resolve().parents[1] / "configs" / "sources.yaml"))
    parser.add_argument("--data-root", default=None)
    args = parser.parse_args()

    account = os.environ["R2_ACCOUNT_ID"]
    bucket = os.environ.get("R2_BUCKET", "livets-snapshots")
    s3 = boto3.client(
        "s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
    try:
        s3.head_bucket(Bucket=bucket)
    except Exception:
        s3.create_bucket(Bucket=bucket)

    data_root = resolve_data_root(load_config(args.config), args.data_root)
    manifest_path = data_root / "logs" / "r2_manifest.jsonl"
    done = set()
    if manifest_path.exists():
        done = {json.loads(l)["key"] for l in manifest_path.read_text().splitlines() if l.strip()}

    uploaded = 0
    with manifest_path.open("a") as mf:
        for path in sorted((data_root / "raw").rglob("*.json")):
            key = "raw/" + str(path.relative_to(data_root / "raw"))
            if key in done:
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            s3.upload_file(str(path), bucket, key)
            mf.write(json.dumps({"key": key, "sha256": digest, "size": path.stat().st_size,
                                 "uploaded_at": dt.datetime.now(dt.timezone.utc).isoformat()}) + "\n")
            uploaded += 1
    s3.upload_file(str(manifest_path), bucket, "manifest/r2_manifest.jsonl")
    print(f"uploaded {uploaded} snapshots to r2://{bucket} (manifest mirrored)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
