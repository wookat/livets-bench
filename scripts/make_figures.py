#!/usr/bin/env python3
"""Generate paper figures from results/matrix-expanded-all.jsonl.

Figures (PDF + PNG under docs/figures/):
  fig1_main_geomase   — geo-MASE per model with bootstrap 95% CI (clean windows only)
  fig2_domain_heatmap — per-domain geo-MASE heatmap (relative to seasonal naive)
  fig3_cutoff_shift   — per-cutoff geo-MASE ranking shift (cutoff sensitivity)
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
B = 1000
BOOT_SEED = 12345


def geomean(x: np.ndarray) -> float:
    x = x[np.isfinite(x) & (x > 0)]
    return float(np.exp(np.mean(np.log(x)))) if len(x) else float("nan")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="inp", default=str(REPO / "results" / "matrix-expanded-all.jsonl"))
    parser.add_argument("--outdir", default=str(REPO / "docs" / "figures"))
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([json.loads(l) for l in Path(args.inp).read_text().splitlines() if l.strip()])
    rng = np.random.default_rng(BOOT_SEED)

    # ---- fig 1: main geo-MASE with CI ----
    rows = []
    for model, g in df.groupby("model"):
        per_series = g.groupby("series_id")["mase"].mean().to_numpy()
        gm = geomean(per_series)
        boots = [geomean(rng.choice(per_series, size=len(per_series), replace=True)) for _ in range(B)]
        rows.append({"model": model, "gm": gm,
                     "lo": np.percentile(boots, 2.5), "hi": np.percentile(boots, 97.5),
                     "n_cutoffs": g.cutoff.nunique()})
    t = pd.DataFrame(rows).sort_values("gm", ascending=False)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    y = np.arange(len(t))
    colors = ["#888888" if n < 3 else "#3b6fb6" for n in t.n_cutoffs]
    ax.barh(y, t.gm, xerr=[t.gm - t.lo, t.hi - t.gm], color=colors, height=0.62,
            error_kw={"elinewidth": 1, "capsize": 2.5})
    ax.axvline(1.0, color="#c33", lw=1, ls="--")
    labels = [f"{m}*" if n < 3 else m for m, n in zip(t.model, t.n_cutoffs)]
    ax.set_yticks(y, labels)
    ax.set_xlabel("geo-MASE (clean windows, 95% bootstrap CI); * = fewer clean cutoffs")
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(outdir / f"fig1_main_geomase.{ext}", dpi=200)
    plt.close(fig)

    # ---- fig 2: per-domain heatmap relative to seasonal naive ----
    dom = df.groupby(["model", "domain"]).apply(
        lambda g: geomean(g.groupby("series_id")["mase"].mean().to_numpy()),
        include_groups=False).unstack()
    rel = np.log2(dom / dom.loc["seasonal_naive"])
    rel = rel.drop(index="seasonal_naive").sort_values(rel.columns.tolist()[0])
    order = rel.mean(axis=1).sort_values().index
    rel = rel.loc[order]
    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    im = ax.imshow(rel.to_numpy(), cmap="RdBu_r", vmin=-1.2, vmax=1.2, aspect="auto")
    ax.set_xticks(range(len(rel.columns)), rel.columns, rotation=30, ha="right")
    ax.set_yticks(range(len(rel.index)), rel.index)
    for i in range(rel.shape[0]):
        for j in range(rel.shape[1]):
            ax.text(j, i, f"{rel.iloc[i, j]:+.2f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, label="log2(geo-MASE / seasonal naive)")
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(outdir / f"fig2_domain_heatmap.{ext}", dpi=200)
    plt.close(fig)

    # ---- fig 3: per-cutoff geo-MASE (cutoff sensitivity) ----
    cut = df.groupby(["model", "cutoff"]).apply(
        lambda g: geomean(g.groupby("series_id")["mase"].mean().to_numpy()),
        include_groups=False).unstack()
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for model, row in cut.iterrows():
        vals = row.dropna()
        style = "--o" if len(vals) < 3 else "-o"
        ax.plot(vals.index, vals.to_numpy(), style, label=model, ms=4, lw=1.2)
    ax.set_ylabel("geo-MASE per cutoff")
    ax.set_xlabel("rolling cutoff")
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(outdir / f"fig3_cutoff_shift.{ext}", dpi=200)
    plt.close(fig)

    print(f"figures written to {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
