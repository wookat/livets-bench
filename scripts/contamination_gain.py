#!/usr/bin/env python3
"""Contamination-gain scaffold: LiveTS clean skill vs. legacy-benchmark skill.

For each TSFM, computes the LiveTS clean skill ratio
    skill_live = geo-MASE(model) / geo-MASE(seasonal_naive)   (shared clean windows)
and tabulates it against the model's published legacy-benchmark skill ratio
(same statistic on GIFT-Eval-style static benchmarks), to be filled from the
companion contamination-audit project (P2). The gap
    gain = skill_legacy - skill_live
upper-bounds what contamination plus community overfitting bought on legacy sets.

LiveTS-side numbers are computed here from results; legacy-side numbers must be
sourced (with citation) by P2 — they are marked TBD and never invented.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
TSFMS = ["chronos-bolt-small", "chronos-bolt-base", "chronos-t5-small",
         "time-moe-50m", "moirai-1.1-r-small", "timesfm-2.5-200m"]


def geomean(x: np.ndarray) -> float:
    x = x[np.isfinite(x) & (x > 0)]
    return float(np.exp(np.mean(np.log(x)))) if len(x) else float("nan")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="inp", default=str(REPO / "results" / "matrix-expanded-all.jsonl"))
    parser.add_argument("--out", default=str(REPO / "docs" / "contamination-gain.md"))
    args = parser.parse_args()

    df = pd.DataFrame([json.loads(l) for l in Path(args.inp).read_text().splitlines() if l.strip()])
    df = df.groupby(["model", "series_id", "cutoff", "origin"], as_index=False)["mase"].mean()
    piv = df.pivot_table(index=["series_id", "cutoff", "origin"], columns="model", values="mase")

    rows = []
    for m in TSFMS:
        sub = piv[[m, "seasonal_naive"]].dropna()
        skill = (geomean(sub.groupby(level="series_id")[m].mean().to_numpy())
                 / geomean(sub.groupby(level="series_id")["seasonal_naive"].mean().to_numpy()))
        rows.append({"model": m, "n_windows": len(sub), "skill_live": round(skill, 3)})
    t = pd.DataFrame(rows)

    lines = [
        "# 污染增益分析（LiveTS × P2 对接表）",
        "",
        "skill = geo-MASE(model)/geo-MASE(seasonal naive)，共享洁净窗口；<1 越小越好。",
        "legacy 列由 P2 污染审计项目按发表数字/官方榜单填入（必须带引用），本脚本不虚构。",
        "gain = skill_legacy − skill_live：负值表示 legacy 上的相对优势大于 LiveTS 洁净窗口上的优势，",
        "其量级是「污染 + 社区过拟合」收益的上界估计。",
        "",
        "| 模型 | 洁净共享窗口 | skill_live (LiveTS) | skill_legacy (P2 填入) | gain |",
        "|---|---|---|---|---|",
    ]
    for _, r in t.iterrows():
        lines.append(f"| {r.model} | {r.n_windows} | {r.skill_live} | TBD (P2) | TBD |")
    lines += ["", f"生成：`scripts/contamination_gain.py`，输入 `{Path(args.inp).name}`。"]
    Path(args.out).write_text("\n".join(lines) + "\n")
    print(t.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
