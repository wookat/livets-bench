#!/usr/bin/env python3
"""Generate LaTeX tables for the paper from results/matrix-expanded-all.jsonl."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
B = 1000
BOOT_SEED = 12345
RELEASE = {
    "chronos-bolt-small": "2024-11-25", "chronos-bolt-base": "2024-11-25",
    "chronos-t5-small": "2024-02-21", "time-moe-50m": "2024-09-21",
    "moirai-1.1-r-small": "2024-06-14", "timesfm-2.5-200m": "2025-09-02",
    "dlinear": "per-cutoff", "patchtst": "per-cutoff", "itransformer": "per-cutoff",
    "seasonal_naive": "---", "autoets": "---",
}


def geomean(x: np.ndarray) -> float:
    x = x[np.isfinite(x) & (x > 0)]
    return float(np.exp(np.mean(np.log(x)))) if len(x) else float("nan")


def ci(per_series: np.ndarray, rng) -> tuple[float, float]:
    boots = [geomean(rng.choice(per_series, size=len(per_series), replace=True)) for _ in range(B)]
    return float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="inp", default=str(REPO / "results" / "matrix-expanded-all.jsonl"))
    parser.add_argument("--outdir", default=str(REPO / "paper" / "tables"))
    args = parser.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([json.loads(l) for l in Path(args.inp).read_text().splitlines() if l.strip()])
    rng = np.random.default_rng(BOOT_SEED)

    rows = []
    for model, g in df.groupby("model"):
        ps_mase = g.groupby("series_id")["mase"].mean().to_numpy()
        gm = geomean(ps_mase)
        lo, hi = ci(ps_mase, rng)
        wql = g.dropna(subset=["wql"]) if "wql" in g else g
        gw = geomean(wql.groupby("series_id")["wql"].mean().to_numpy()) if len(wql) else float("nan")
        rows.append({"model": model, "gm": gm, "lo": lo, "hi": hi, "wql": gw,
                     "n_series": g.series_id.nunique(), "n_windows": len(g),
                     "n_cutoffs": g.cutoff.nunique()})
    t = pd.DataFrame(rows).sort_values("gm")

    def rank_marks(values):
        finite = [(i, v) for i, v in enumerate(values) if np.isfinite(v)]
        order = sorted(finite, key=lambda x: x[1])
        marks = {}
        if len(order) > 0:
            marks[order[0][0]] = "bold"
        if len(order) > 1:
            marks[order[1][0]] = "underline"
        return marks

    def fmt(v, mark, text):
        if mark == "bold":
            return rf"\textbf{{{text}}}"
        if mark == "underline":
            return rf"\underline{{{text}}}"
        return text

    gm_marks = rank_marks(t["gm"].to_numpy())
    wql_marks = rank_marks(t["wql"].to_numpy())

    lines = [
        r"\begin{tabular}{lccccc}",
        r"\toprule",
        r"Model & Release & geo-MASE [95\% CI] & geo-WQL & Series & Windows \\",
        r"\midrule",
    ]
    for i, (_, r) in enumerate(t.iterrows()):
        name = r.model.replace("_", r"\_")
        star = r"$^{\dagger}$" if r.n_cutoffs < 3 else ""
        gm_s = fmt(r.gm, gm_marks.get(i), f"{r.gm:.3f} [{r.lo:.3f}, {r.hi:.3f}]")
        wql_s = fmt(r.wql, wql_marks.get(i), f"{r.wql:.3f}") if np.isfinite(r.wql) else "---"
        lines.append(
            f"{name}{star} & {RELEASE.get(r.model, '?')} & "
            f"{gm_s} & {wql_s} & "
            f"{r.n_series} & {r.n_windows} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (outdir / "main_table.tex").write_text("\n".join(lines) + "\n")

    dom = df.groupby(["model", "domain"]).apply(
        lambda g: geomean(g.groupby("series_id")["mase"].mean().to_numpy()),
        include_groups=False).unstack()
    dom = dom.loc[t.model]
    cols = list(dom.columns)
    lines = [r"\begin{tabular}{l" + "c" * len(cols) + "}", r"\toprule",
             "Model & " + " & ".join(c.replace("_", r"\_") for c in cols) + r" \\", r"\midrule"]
    col_marks = {c: rank_marks(dom[c].to_numpy()) for c in cols}
    row_pos = {m: i for i, m in enumerate(dom.index)}
    for model, r in dom.iterrows():
        cells = " & ".join(
            fmt(r[c], col_marks[c].get(row_pos[model]), f"{r[c]:.2f}") for c in cols)
        lines.append(f"{model.replace('_', chr(92) + '_')} & {cells} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (outdir / "domain_table.tex").write_text("\n".join(lines) + "\n")
    print(f"tables written to {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
