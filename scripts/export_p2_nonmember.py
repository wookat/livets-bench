#!/usr/bin/env python3
"""Export LiveTS series as post-cutoff non-member datasets for the P2
contamination audit (wookat/tsfm-contamination-audit).

Slices every series strictly to observations dated >= --start (default
2025-01-01, after all P2-audited models' release dates), groups them into
8 domain datasets, and writes NPZ files in P2's format (save_npz: one 1-D
float array per series, keys s0..sN) plus a provenance manifest with
SHA-256 hashes, series ids, date ranges, and the LiveTS git commit.

Usage: .venv/bin/python scripts/export_p2_nonmember.py --out /path/to/out
"""
import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from livets.eval.data_loaders import load_all  # noqa: E402

GROUPS = {
    "livets_energy_post2025": lambda s: s.domain == "energy",
    "livets_weather_temp_post2025": lambda s: s.domain == "weather" and s.series_id.endswith("t2m_mean"),
    "livets_weather_precip_post2025": lambda s: s.domain == "weather" and s.series_id.endswith("precip_sum"),
    "livets_airquality_post2025": lambda s: s.domain == "air_quality",
    "livets_crypto_post2025": lambda s: s.domain == "crypto_fx" and s.series_id.endswith(":close"),
    "livets_fx_post2025": lambda s: s.domain == "crypto_fx" and s.series_id.endswith(":rate"),
    "livets_traffic_post2025": lambda s: s.domain == "traffic",
    "livets_webtraffic_post2025": lambda s: s.domain == "web_traffic",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-01-01")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache-dir", default=str(REPO / "data" / "eval_cache"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    specs = load_all(args.cache_dir)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                            capture_output=True, text=True).stdout.strip()
    manifest = {
        "source": "wookat/livets-bench",
        "git_commit": commit,
        "exported_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "start": args.start,
        "semantics": ("Observations strictly dated >= start; all P2-audited "
                      "models were released before this date, so these are "
                      "guaranteed non-members. Raw snapshots with collected_at "
                      "and SHA-256 manifests archived on R2 (livets-snapshots)."),
        "datasets": {},
    }
    for name, pred in GROUPS.items():
        sel = [s for s in specs if pred(s)]
        arrays, ids, ranges = [], [], []
        for s in sel:
            v = s.values[s.values.index >= args.start].dropna()
            if len(v) < 300:
                continue
            arrays.append(v.to_numpy(dtype=np.float64))
            ids.append(s.series_id)
            ranges.append([str(v.index.min().date()), str(v.index.max().date())])
        path = out / f"{name}.npz"
        np.savez_compressed(path, **{f"s{i}": a for i, a in enumerate(arrays)})
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest["datasets"][name] = {
            "n_series": len(arrays),
            "lengths": [len(a) for a in arrays],
            "series_ids": ids,
            "date_ranges": ranges,
            "sha256": sha,
            "frequency": "daily",
        }
        print(f"[{name}] {len(arrays)} series, sha256={sha[:12]}")
    (out / "livets_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[done] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
