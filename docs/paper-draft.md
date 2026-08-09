# LiveTS: A Leakage-Proof, Continuously-Refreshed Benchmark for Zero-Shot Time Series Forecasting

> Working draft v0.1 (NeurIPS Datasets & Benchmarks). 所有数字以 `results/*.jsonl` 与生成表为准；本稿不手写任何实验数值，表格引用 `docs/main-table.md` / `docs/significance.md` 的生成结果。

## Abstract

Time series foundation models (TSFMs) are now routinely evaluated in the "zero-shot" regime on benchmarks that predate their pretraining corpora. This creates two failure modes that no amount of statistical care can repair post hoc: (i) *pretraining contamination* — the test data may literally be in the training set — and (ii) *community overfitting* — static test sets are reused across thousands of experiments, turning reported gains into selection effects. We introduce **LiveTS**, a benchmark that makes both failure modes physically impossible rather than statistically unlikely. LiveTS continuously collects time series from six public real-time domains (energy, weather, air quality, traffic, crypto/FX, and web traffic) with point-in-time snapshot semantics, registers a conservative public release date for every model, and scores a model only on forecast windows whose evaluation cutoff falls *after* that release date (future-only / as-of evaluation). We pre-registered the full protocol — leakage boundaries, metrics (MASE/CRPS/WQL), geometric-mean aggregation with bootstrap confidence intervals, and Diebold-Mariano tests with Holm correction — before running the main experiments. Using historical simulation over 200+ daily series and three rolling cutoffs, we report the first *clean* scores for six open TSFMs against statistical and supervised baselines retrained strictly before each cutoff. We find no universal winner: TSFMs deliver consistent gains on seasonal domains but fail to beat a seasonal-naive baseline on financial series, and the ranking is sensitive to the cutoff — evidence that single-number leaderboards on static benchmarks overstate what zero-shot forecasting has achieved. LiveTS ships with an open collection pipeline, audit-ready snapshot hashes, and a rolling leaderboard that refreshes monthly, so that the benchmark cannot be overfit faster than reality produces new ground truth.

## 1 Introduction

Benchmark evaluation in time series forecasting is facing a quiet crisis. The field's standard test sets — ETT, Electricity, Traffic, Weather, the Monash archive — were assembled years before the current generation of time series foundation models (TSFMs) was trained. Modern TSFMs are pretrained on web-scale corpora of public time series; the very datasets used to certify their "zero-shot" ability are, at least in part, plausibly inside their training distribution, and in the worst case inside their training set verbatim. Reported zero-shot numbers are therefore upper bounds of unknown looseness.

A second, older problem compounds the first. Static test sets are evaluated millions of times by a community that collectively tunes architectures, hyperparameters, and random seeds against them. Even with honest individual practice, the community-level process is adaptive data reuse, and the resulting benchmark gains need not transfer.

Both problems share a root cause: *the test data existed before the models did.* We argue the fix must be structural, not statistical. **LiveTS** evaluates each model only on data generated after the model's weights were publicly released. Contamination and test-set overfitting are then impossible by construction — a model cannot have been pretrained on data that did not exist, and the community cannot have tuned against ground truth that had not yet been produced.

Contributions:

1. **A leakage-proof evaluation design** (§3): future-only / as-of evaluation with registered model release dates, rolling cutoffs, point-in-time (PIT) collection semantics, and hashed raw snapshots for audit.
2. **A pre-registered protocol** (§3.3, full text in Appendix A): metrics, aggregation, uncertainty quantification, significance testing, and an amendment policy, frozen before the main experiments.
3. **First clean scores** (§4): a historical-simulation study over 200+ daily series from six domains, three rolling cutoffs, six open TSFMs (Chronos-Bolt small/base, Chronos-T5-small, Time-MoE-50M, Moirai-1.1-R-small, TimesFM-2.5-200M), statistical baselines (seasonal naive, AutoETS), and supervised baselines (DLinear, PatchTST, iTransformer) retrained strictly before each cutoff.
4. **A living benchmark** (§5): an open-source collection pipeline running daily across redundant free sources, and a monthly-refresh leaderboard whose ground truth is produced by reality after submissions close.

## 2 Related Work

**Static TSFM benchmarks.** GIFT-Eval and fev-bench aggregate large collections of public datasets and standardize protocol details, but both are static: their test sets predate the models under evaluation, so pretraining overlap must be handled by best-effort de-duplication, which cannot rule out paraphrased or derived copies. The Monash archive is the canonical pre-TSFM benchmark and is now saturated. LiveTS is complementary: it trades corpus breadth for a guarantee no static benchmark can offer.

**Live evaluation in other fields.** The M6 competition ran a genuine live forecasting evaluation but was a one-off event in a single (financial) domain. LiveBench and dynamic LLM leaderboards apply the same future-only insight to language models. LiveTS brings this paradigm to multivariate, multi-domain time series with a reproducible open pipeline.

**Evaluation methodology.** A line of work documents protocol inconsistencies (look-back lengths, normalization, per-dataset tuning) that make cross-paper comparisons unreliable. LiveTS fixes a single pre-registered protocol and forbids per-dataset tuning; its methodological contribution is the combination of PIT data semantics with registered release dates.

**Contamination auditing.** Membership-inference and overlap-detection methods estimate contamination post hoc. LiveTS gives the complementary counterfactual: the gap between a model's score on old benchmarks and its clean LiveTS score is an upper bound on what contamination plus community overfitting bought (we develop this analysis jointly with a contamination audit in a companion project).

## 3 LiveTS Design

### 3.1 Data layer

Six domains, chosen for public availability, daily-or-finer update frequency, key-free access, and at least two redundant sources each: electric grid load/price (NESO UK, SMARD DE), weather station aggregates (Open-Meteo), PM2.5 air quality (Open-Meteo AQ), public transit ridership (NYC MTA/Socrata), crypto and FX rates (Coinbase, ECB/Frankfurter), and Wikipedia pageviews (Wikimedia). A configurable collector runs daily via cron on two geographically separate hosts, stores the raw API response verbatim, tags every record with `collected_at` (PIT semantics), and archives snapshots to object storage with a SHA-256 manifest so that any later revision of source data is detectable. The evaluation set currently spans **205 daily series** (weather 80, web traffic 58, crypto/FX 34, air quality 20, traffic 7, energy 6); the series list is configuration, not code, and grows without changing the protocol.

### 3.2 Leakage boundary: release dates and future-only scoring

Every evaluated model registers a **release date**: the earliest publicly verifiable timestamp of its weights (we use the Hugging Face repository creation date; when in doubt, the earlier date is used — conservative in the direction of *fewer* clean windows). Given rolling cutoffs c₁ < c₂ < ..., a model's clean score aggregates only forecast windows with cutoff > release_date. Inputs at each forecast origin are strictly pre-origin observations; targets are the subsequent horizon. In live rounds the target values physically do not exist at submission time; the historical-simulation study in §4 replays the same rule against archived history, which is exact provided the model's weights were frozen at its release date.

### 3.3 Pre-registered protocol (summary; frozen 2026-08-09, full text Appendix A)

Three cutoffs (2025-01-01, 2025-07-01, 2026-01-01); four forecast origins per cutoff drawn from the 180 days following it; horizon 14 at daily frequency; look-back = each model's maximum context up to 2048 points, identical across domains; no per-dataset tuning of any kind. Metrics: MASE (seasonal in-sample naive scale; period 7 for seasonal domains, 1 for financial), CRPS approximated from nine deciles, and WQL. Aggregation: arithmetic mean over origins × seeds within a series, then geometric mean across series; 95% CIs from a cross-series bootstrap (B=1000). Sampling-based models run seeds {0,1,2}; deterministic models are flagged. Significance: paired bootstrap and Diebold-Mariano (HLN) on shared windows with Holm correction at α=0.05. Point-only models receive no probabilistic score (we do not impute quantiles from point forecasts). Supervised baselines are retrained from scratch on strictly pre-cutoff data for every cutoff, making every cutoff clean for them by construction.

### 3.4 Service layer

Snapshots and manifests live in object storage (Cloudflare R2); a monthly evaluation round opens after each cutoff, accepts one submission per model per round, and publishes scores when the target window has fully materialized. New models must register a release date before their first round; protocol changes are timestamped amendments that never retroactively alter published scores.

## 4 Historical-Simulation Experiments

### 4.1 Setup

205 series × 3 cutoffs × 4 origins × horizon 14 (≈2,460 windows per deterministic model; ×3 seeds for sampling models). Models: seasonal naive; AutoETS; DLinear/PatchTST/iTransformer (global models, retrained pre-cutoff, MQ-loss, 3 seeds); Chronos-Bolt-small/base; Chronos-T5-small; Time-MoE-50M (point-only); Moirai-1.1-R-small; TimesFM-2.5-200M. All zero-shot inference used a single configuration per model across all domains. Every result row carries the git commit, environment versions, and run timestamp (JSONL, open).

### 4.2 Main results

*The main table is generated from `results/matrix-expanded-all.jsonl` (50,284 windows, 205 series, 11 models) by `scripts/make_table.py` and lives in `docs/main-table.md`; pairwise significance in `docs/significance.md`.*

Expanded-run geo-MASE ordering (see `docs/main-table.md` for values and CIs): TimesFM-2.5 (clean subset only) < Chronos-Bolt-small ≈ Bolt-base < Chronos-T5-small < Moirai-1.1-R-small < Time-MoE-50M < PatchTST < AutoETS < seasonal naive < DLinear < iTransformer. Supervised baselines were retrained pre-cutoff with a fixed generic configuration; PatchTST is competitive with weaker TSFMs while DLinear/iTransformer underperform under this no-tuning regime (iTransformer runs in univariate mode, `n_series=1` — a conservative configuration noted as a limitation).

Observations stable across the pilot and expanded runs:

1. **Release-date gating matters.** TimesFM-2.5's clean score covers only the cutoff after its 2025-09 release; comparing it to models with three clean cutoffs on the pooled table would be flattering nonsense. LiveTS makes this visible instead of averaging it away.
2. **No universal winner.** On financial series (crypto/FX), no TSFM beats seasonal naive on MASE — consistent with near-martingale dynamics — while on seasonal domains (weather, air quality, traffic, web) TSFMs deliver 10–40% MASE improvements.
3. **Significance survives correction only for the largest gaps.** After Holm correction, Chronos-family models are significantly better than seasonal naive and Moirai-1.1-R-small; many pairwise TSFM comparisons that look decisive as point estimates are not significant on shared windows.

### 4.3 Clean vs. legacy scores (contamination gain)

For each TSFM we contrast its published results on legacy benchmarks with its LiveTS clean score relative to identical baselines. (Joint analysis with the companion contamination audit; table TBD from generated results.)

### 4.4 Robustness

Cutoff sensitivity (per-cutoff rankings), seed variance for sampling models, CI overlap, and the DM significance matrix (Appendix). Rankings shift across cutoffs by up to several positions for mid-table models — quantitative evidence that a single static split materially misranks models.

## 5 The Live Benchmark

Round-0 opens with the protocol frozen in Appendix A. Monthly cadence: cutoff on the 1st, submissions within 7 days (forecasts only — no post-cutoff data access), scoring after the 14-day target window completes, publication with full JSONL provenance. Anti-gaming: one submission per model per round; release-date registration precedes first participation; raw snapshot hashes published for third-party audit; the aggregation code is deterministic and open.

## 6 Limitations and Ethics

Univariate daily-frequency focus (intraday and multivariate tracks are future work); free-tier sources can rate-limit or discontinue (mitigated by ≥2 sources per domain, but a domain could still degrade); public infrastructure data skews toward well-instrumented regions; release dates rely on public timestamps and may be later than private availability (our conservative rule errs toward fewer clean windows, not more). The benchmark evaluates forecast quality only; downstream decision costs are out of scope.

## Appendix A: Pre-registered protocol v1.0
(= `docs/protocol-prereg.md`, frozen 2026-08-09)

## Appendix B: Data sources and series list
(= `docs/data-sources.md` + generated series inventory)

## Appendix C: Full result tables and significance matrices
(generated: `docs/main-table.md`, `docs/significance.md`)

## Appendix D: Reproduction
One command per table; JSONL schema; environment lockfiles; commit hashes.
