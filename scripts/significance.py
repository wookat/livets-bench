#!/usr/bin/env python3
"""Pairwise significance tests on the eval matrix (pre-registered protocol).

For each model pair, on the windows they share (series_id, cutoff, origin;
seeds averaged first): paired bootstrap test on mean MASE difference +
Diebold-Mariano with Harvey-Leybourne-Newbold small-sample correction,
Holm correction across all pairs. Outputs docs/significance.md.

Usage: python scripts/significance.py [--in results/matrix.jsonl] [--metric mase]
"""

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
B = 10000
SEED = 20260809


def dm_hln(d: np.ndarray, h: int = 14) -> float:
    """Two-sided DM test p-value with HLN correction (loss differential d per window)."""
    n = len(d)
    dbar = d.mean()
    # window-level losses are ~independent (distinct series/origins) -> lag-0 variance
    var = d.var(ddof=1) / n
    if var == 0:
        return 1.0
    dm = dbar / np.sqrt(var)
    k = np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    return float(2 * stats.t.sf(abs(dm * k), df=n - 1))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="inp", default=str(REPO / "results" / "matrix.jsonl"))
    parser.add_argument("--metric", default="mase")
    parser.add_argument("--out", default=str(REPO / "docs" / "significance.md"))
    args = parser.parse_args()

    df = pd.DataFrame([json.loads(l) for l in Path(args.inp).read_text().splitlines() if l.strip()])
    # average over seeds first
    df = df.groupby(["model", "series_id", "cutoff", "origin"], as_index=False)[args.metric].mean()
    piv = df.pivot_table(index=["series_id", "cutoff", "origin"], columns="model", values=args.metric)

    rng = np.random.default_rng(SEED)
    rows = []
    for m1, m2 in itertools.combinations(sorted(piv.columns), 2):
        sub = piv[[m1, m2]].dropna()
        d = (sub[m1] - sub[m2]).to_numpy()
        if len(d) < 10:
            continue
        boots = rng.choice(d, size=(B, len(d)), replace=True).mean(axis=1)
        p_boot = float(2 * min((boots > 0).mean(), (boots < 0).mean()))
        rows.append({"model_a": m1, "model_b": m2, "n_windows": len(d),
                     f"mean_{args.metric}_diff(a-b)": float(d.mean()),
                     "p_bootstrap": max(p_boot, 1 / B), "p_dm_hln": dm_hln(d)})

    res = pd.DataFrame(rows)
    for col in ("p_bootstrap", "p_dm_hln"):
        # Holm correction
        order = np.argsort(res[col].to_numpy())
        m = len(res)
        adj = np.empty(m)
        running = 0.0
        for rank, idx in enumerate(order):
            running = max(running, (m - rank) * res[col].iloc[idx])
            adj[idx] = min(1.0, running)
        res[col + "_holm"] = adj
    res["significant(α=0.05)"] = res["p_dm_hln_holm"] < 0.05

    lines = [f"# 模型两两显著性检验（{args.metric}，重叠窗口，Holm 校正）", "",
             f"配对 bootstrap B={B}（seed={SEED}）+ DM(HLN)；seeds 先平均。", "",
             res.to_markdown(index=False, floatfmt=".4f")]
    Path(args.out).write_text("\n".join(lines) + "\n")
    print(res.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
