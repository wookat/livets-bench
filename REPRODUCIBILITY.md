# REPRODUCIBILITY

All numbers in the paper are generated from JSONL result files in `results/`; no number is hand-written.

## Environment

- Python 3.10+ (`python -m venv .venv && .venv/bin/pip install -r requirements-eval.txt`)
- Model-specific extras (kept in separate venvs to avoid dependency clashes):
  - TimesFM 2.5: `.venv-timesfm` (`timesfm` + pandas)
  - Moirai: `.venv-moirai` (`uni2ts`)
  - Time-MoE: `.venv-timemoe` (`transformers==4.40.1`)
- Behind restricted networks set `HF_ENDPOINT=https://hf-mirror.com`.
- GPU runs are scheduled via `sgpu` (launch scripts in `ops/sgpu/`); results are rsynced back and verified with `sha256sum`.

## Data

- Evaluation series are loaded/cached by `livets/eval/data_loaders.py` into `data/eval_cache/` (205 daily series, 6 domains). Loading is configuration-driven; single-series failures are isolated and logged.
- Live collection: `scripts/run_collect.py` (cron daily), raw snapshots + `collected_at` under `data/raw/`, SHA-256 manifest mirrored to Cloudflare R2 by `scripts/sync_r2.py`.

## Result files (provenance: every row carries git commit, environment, run timestamp)

| File | Contents |
|---|---|
| `results/matrix.jsonl` | 25-series pilot (8 models, 3,400 windows) — frozen, never rewritten |
| `results/matrix-expanded-all.jsonl` | merged + deduplicated expanded matrix (11 models, 205 series, 50,284 windows) |
| `results/matrix-expanded*.jsonl`, `results/gpu/*.jsonl`, `results/matrix-supervised.jsonl` | expanded-run shards (CPU, sgpu GPU jobs, supervised baselines) |

Dedup key: `(model, series_id, cutoff, origin, seed)`.

## One command per artifact

```bash
# zero-shot matrix (per model; GPU models via ops/sgpu/launch-*.sh through sgpu)
.venv/bin/python scripts/run_matrix.py --models <model> --out results/matrix-<name>.jsonl

# supervised baselines (strict pre-cutoff retraining, seeds 0/1/2)
.venv/bin/python scripts/run_supervised.py --models dlinear,patchtst,itransformer

# main table (markdown)          -> docs/main-table.md
.venv/bin/python scripts/make_table.py --in results/matrix-expanded-all.jsonl --out docs/main-table.md

# significance matrix            -> docs/significance.md
.venv/bin/python scripts/significance.py --in results/matrix-expanded-all.jsonl --out docs/significance.md

# LaTeX tables                   -> paper/tables/*.tex
.venv/bin/python scripts/make_latex_table.py

# figures                        -> docs/figures/*.{pdf,png}
.venv/bin/python scripts/make_figures.py

# freeze a live round snapshot   -> r2://livets-snapshots/rounds/<round>/
.venv/bin/python scripts/freeze_round.py --round 2026-09 --cutoff 2026-09-01

# paper
cd paper && pdflatex main && bibtex main && pdflatex main && pdflatex main
```

## Determinism

- Sampling models: seeds {0,1,2}; deterministic models seed 0.
- Bootstrap: B=1000, seed 12345 (tables/figures); pairwise significance B=10000, seed 20260809.
- Supervised training: `random_seed` passed to NeuralForecast models; training data strictly `< cutoff`.

## Known reproduction notes

- Pilot Moirai windows (900) were run directly on xu-4 RTX 3090 without the sgpu scheduler (one-time exception, recorded in JSONL env fields). All expanded-matrix GPU runs went through sgpu.
- iTransformer is wired univariately (`n_series=1`), a conservative configuration noted in the paper.
- Wikimedia API rate-limits (429): the loader retries with backoff; a few target articles 404 and are skipped (loader prints skips).

## Protocol

`docs/protocol-prereg.md` — v1.0 frozen 2026-08-09, amendment A1 (series expansion + supervised baselines) registered before the expanded runs. Release dates per model in `livets/eval/model_zoo.py`; clean-score rule: only cutoffs strictly after the model's release date count.
