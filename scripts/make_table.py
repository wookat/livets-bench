#!/usr/bin/env python3
"""Aggregate results/matrix.jsonl into the paper main table.

Aggregation (pre-registered): per (model, series) mean over origins/seeds,
then geometric mean across series; 95% CI via bootstrap over series (B=1000,
fixed seed). Also emits a per-domain geo-MASE breakdown.

Usage: python scripts/make_table.py [--in results/matrix.jsonl] [--out docs/main-table.md]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
B = 1000
BOOT_SEED = 12345


def geomean(x: np.ndarray) -> float:
    x = x[np.isfinite(x) & (x > 0)]
    return float(np.exp(np.mean(np.log(x)))) if len(x) else float("nan")


def boot_ci(series_means: np.ndarray, rng: np.random.Generator) -> tuple[float, float]:
    stats = [geomean(rng.choice(series_means, size=len(series_means), replace=True)) for _ in range(B)]
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="inp", default=str(REPO / "results" / "matrix.jsonl"))
    parser.add_argument("--out", default=str(REPO / "docs" / "main-table.md"))
    args = parser.parse_args()

    df = pd.DataFrame([json.loads(l) for l in Path(args.inp).read_text().splitlines() if l.strip()])
    print(f"{len(df)} window records, models: {sorted(df.model.unique())}", file=sys.stderr)

    rng = np.random.default_rng(BOOT_SEED)
    rows = []
    for model, g in df.groupby("model"):
        row = {"model": model, "n_windows": len(g),
               "n_series": g.series_id.nunique(), "release_date": g.release_date.iloc[0]}
        for metric in ("mase", "crps", "wql"):
            per_series = g.groupby("series_id")[metric].mean().to_numpy()
            gm = geomean(per_series)
            row[metric] = gm
            if np.isfinite(gm):
                lo, hi = boot_ci(per_series, rng)
                row[f"{metric}_ci"] = f"[{lo:.3f}, {hi:.3f}]"
            else:
                row[f"{metric}_ci"] = "—"
        rows.append(row)
    main_tbl = pd.DataFrame(rows).sort_values("mase")

    dom = df.groupby(["model", "domain"]).apply(
        lambda g: geomean(g.groupby("series_id")["mase"].mean().to_numpy()),
        include_groups=False).unstack()

    lines = ["# LiveTS 主表（历史模拟 live，future-only cutoffs）", "",
             f"来源：`{Path(args.inp).name}`（{len(df)} 窗口记录）。聚合：序列内均值 → 跨序列几何平均；bootstrap B={B} 95% CI。", "",
             "## 总表", "",
             "| 模型 | 发布日 | geo-MASE [95% CI] | geo-CRPS [95% CI] | geo-WQL [95% CI] | 序列 | 窗口 |",
             "|---|---|---|---|---|---|---|"]
    for _, r in main_tbl.iterrows():
        def fmt(m):
            return f"{r[m]:.3f} {r[f'{m}_ci']}" if np.isfinite(r[m]) else "—（point-only）"
        rel = r.release_date if isinstance(r.release_date, str) else "—"
        lines.append(f"| {r.model} | {rel} | {fmt('mase')} | {fmt('crps')} | {fmt('wql')} | {r.n_series} | {r.n_windows} |")

    lines += ["", "注：各模型仅统计其权重发布日之后的 cutoff（future-only），窗口数因此不同（如 TimesFM-2.5 仅 2026-01-01 一个洁净 cutoff），跨模型比较时以重叠 cutoff 子集为准。", ""]
    lines += ["", "## 分域 geo-MASE", "", "| 模型 | " + " | ".join(dom.columns) + " |",
              "|---|" + "---|" * len(dom.columns)]
    for model, r in dom.iterrows():
        lines.append(f"| {model} | " + " | ".join(f"{v:.3f}" if np.isfinite(v) else "—" for v in r) + " |")

    Path(args.out).write_text("\n".join(lines) + "\n")
    print(f"written {args.out}", file=sys.stderr)
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
