# Data pipeline and backtest harness

The shared base for every model: clean, aligned data, a fair backtest, and the scores used to
choose models. This part makes no modelling choices. Section numbers (§) refer to
[`eda_findings.md`](eda_findings.md); the overall method is in [`methodology.md`](methodology.md).

| Part | Delivers | Code |
|---|---|---|
| Data pipeline | Clean monthly table, series catalog, flags, clean BOM (+ all BOM versions), RMU prices | `data.py`, `config.py` |
| Backtest harness | `run_backtest`, `score`, `compare`: the same leak-free test for every model since 2020, plus plots | `backtest.py`, `metrics.py`, `plots.py` |

Three rules: **nothing after 2026-09** · **clean, don't curate** (keep every loaded series, flag
issues) · **the backtest only uses data that was known at each forecast date** (strict run).

---

## Data pipeline

Job: make the given files clean and aligned. Nothing more.

### Use
```bash
uv run python -m schneider_forecast.data      # writes data/processed/ (gitignored)
```
```python
prices = pd.read_csv(PRICES_WIDE, parse_dates=["month"], index_col="month")
catalog = pd.read_csv(SERIES_CATALOG, index_col="series_id")  # paths in config.py
```

### Outputs
| File | Content |
|---|---|
| `prices_wide.csv` | One row per month (Jan 2008 → Sep 2026), one column per series |
| `series_catalog.csv` | Per series: source, material, region, unit, first / last month, n_obs, `gap_months`, `pub_lag`, `is_target`, `needs_nowcast` |
| `data_flags.csv` | Known data issues and their treatment |
| `bom_clean.csv` | The reference BOM (20 Nov v1): product × material, plant code and country, share, kg, price series |
| `bom_versions.csv` | All three BOM versions stacked (12 Nov CSV, 19 Nov xlsx, 20 Nov v1) with a `version` column, for sensitivity checks |
| `rmu_prices.csv` | Brand × year unit price, P10 / P50 / P90 |

### Cleaning per source
| Source | Columns | Cleaning |
|---|---|---|
| RM prices CSV | S01–S13, D01, D02 | Drop date helper columns and the empty licensed L01–L08 |
| MEPS sheet | **L01** (DE CR coil), **L03** (DE HDG coil), `MEPS_DE_{HR,EG}`, `MEPS_FR_{HR,CR,HDG,EG}` | Rebuild the 5-row header; skip the `▲` change sheets (0 for future months) |
| CRU Stainless sheet | **L02** (stainless 304 DE) | Price = base + alloy surcharge |
| Energy CSV | E01–E24, ED01–ED06 | None |
| Epoxy file | `EPX_BENZENE`, `EPX_ACETONE`, `EPX_ECH`, `EPX_OTHER`, `EPX_RESIN` | None |
| LME file | `LME_{CU,AL}_{CASH,3M}_{USD,EUR}`, `LME_{CU,AL}_{STOCKS,SPREAD}` | Completed months only (the month-to-date row is provisional) |

All series:
- **Dates set to the month** (stored as the 1st): sources stamp the same month on different days
  (MEPS the 1st, CRU the 15th, epoxy the 1st–5th). One label per month lets them line up.
- Numbers read strictly: a cell that cannot be read stops the build instead of becoming blank.
- One row per month; nothing after 2026-09; full history kept; no imputation, currency or
  inflation adjustment; no feature selection.

**Why L01–L03 are rebuilt:** the BOM names the licensed series L01 (carbon steel), L02 (stainless)
and L03 (galvanised steel) as the preferred prices for the two biggest-mass materials, but they are
empty in the data. The steel workbook has the real €/t prices for exactly those products, so they
fill the same IDs. The fallback indices (S09, S10) understate steel risk about 2.7× (§2).

**Facts modellers should know** (no series is removed for them): `EPX_OTHER` is resin minus its
inputs, so same-month use leaks `EPX_RESIN`; D01 / D02 use same-month FX; LME spreads can be
negative; L01–L03 reuse the licensed IDs; LME cash prices are close to S01 / S02 (IMF averages), and
cash vs 3-month is the choice of copper / aluminium reference for offers (Schneider left it open).

### Targets (19)
**Rule:** every series ID listed in the BOM's `eu_series_ids` or `ww_series_ids` (fallbacks
included, not only the first choice) that has data, plus `config.EXTRA_TARGETS` (epoxy resin,
the insulation material; EUR/USD, methodology §3.1). The result must equal the fixed list `config.EXPECTED_TARGETS`
(19), or the build stops: to add a target, edit that list. `is_target` is a label: forecasters
decide what they model.

| Material | EU | World |
|---|---|---|
| Carbon steel | **L01**, S09 | S04, S12 |
| Stainless | **L02**, S09 | S03 |
| Galvanised steel | **L03**, S10 | S04, S05, S12 |
| Copper | D01, S07 | S01 |
| Aluminium | D02, S08 | S02 |
| Plastics | S11 | S13 |
| Epoxy · FX | `EPX_RESIN` · S06 | — |

### Two time gaps per series
| Column | Meaning | Source | Used for |
|---|---|---|---|
| `gap_months` | Months from the series' last value to 2026-09: L02 = 1; E20, E21, ED06 = 2; others 0 | Measured in our files | Main run (reference) |
| `pub_lag` | Months from a month's end to its publication: LME 0; MEPS, FX, power, epoxy 1; IMF, PPIs 2; CRU stainless 3; EU crude imports 4 | **Estimated** from the download date (~12 Nov) and provider notes (§4) | Strict run: **model selection** |

### Checks (the build stops if any fails)
- Months unique and sorted; nothing after 2026-09.
- Every series has a `pub_lag`.
- The 19 targets are all present, with no gaps inside their history and no values ≤ 0 (models
  work on logs).

### BOM and known issues
- **Plant country kept** (`plant_country`: AirSeT HU, RM6 FR): Schneider prices each steel part on
  its plant country's index (Hungary → Germany), per the steel workbook's index mapping. So
  AirSeT carbon steel → CR Germany (L01); RM6 carbon steel → CR France (`MEPS_FR_CR`); RM6
  galvanised steel is "HDG Germany" in the BOM (L03). Which series each line uses is decided in the pricing step.
- **Reference BOM = the 20 Nov v1** (`RM_Prices_XHEC_Challenge_v1.xlsx`), as Schneider asked
  (use the latest BOM version as the reference). Compared with earlier versions it
  labels RM6 carbon steel, adds AirSeT copper and epoxy, PE, PVC, PP,
  and RM6 epoxy, brass, PP and ETP; AirSeT totals 547 kg, RM6 310 kg.
- **Earlier versions** (12 Nov CSV, 19 Nov xlsx) disagree on every mass. They are kept in
  `bom_versions.csv` for the pricing sensitivity, not merged into the reference: several plastic rows
  share one price series, so rows cannot be matched one-to-one across versions.
- **BOM mapping kept as given:** brass has no price series; epoxy resin is mapped to the plastics
  index S11 although the epoxy file has a real resin price (`EPX_RESIN`). The pricing step picks
  the proxy; Schneider allows any public proxy if explained.
- **Not priceable:** AirSeT "Other" and RM6's unidentified remainder have no
  composition; Schneider asks for a sensitivity if they matter.
- **Flags:** epichlorohydrin, resin and `EPX_OTHER` May 2026 = error (kept, flagged) · WTI Apr 2020,
  Japan power Jan 2021, Russian crude imports Aug 2025 = real events (keep).

### Preprocessing assumptions
Each one is a choice the data does not settle on its own; it holds until Schneider says otherwise.

| # | Assumption | Why | If wrong |
|---|---|---|---|
| 1 | Forecast origin is 2026-09: nothing after it is used | Slides p17 ("last data used") | Re-run with another `ORIGIN` |
| 2 | Each value belongs to its calendar month (stored as the 1st), whatever day the source stamps | All sources are monthly; dates must line up | Epoxy may be a point reading, not a monthly average (§1) |
| 3 | L01 / L03 = MEPS Germany CR / HDG coil, L02 = CRU stainless 304 Germany, under the licensed IDs | The BOM points to L01–L03; the workbook has those products' real €/t prices | Schneider's licensed series may differ; switch IDs in the submission builder |
| 4 | MEPS stands in for CRU flat steel | CRU sits ≈ 2 % above MEPS and tracks it (§1); Schneider indexes on CRU | Small level gap; moves agree |
| 5 | Stainless price = base + alloy surcharge | European stainless is quoted that way; base alone can be negative (§1) | Not confirmed by Schneider |
| 6 | Unpriced BOM lines ("Other", unidentified remainder, brass) are left without a price series | No composition or series given | The pricing step runs a sensitivity |
| 7 | The 20 Nov v1 BOM is the reference; earlier versions are kept for sensitivity only | Schneider: use the latest version | Another revision replaces `config.BOM` |
| 8 | Steel index follows plant country (HU → Germany, FR → France) | Schneider's own part-to-index mapping | The pricing step uses the plant column to switch |
| 9 | Publication lags (`pub_lag`) | Estimated from the download date and provider notes, not release calendars (§4) | The strict run, used for model selection, changes |
| 10 | Prices are nominal, in their native currency | Schneider: nominal is fine; conversion happens in the cost bridge | — |
| 11 | Known errors are kept and flagged, not fixed (epoxy May 2026) | Cleaning does not change data; modellers decide | Every model skips flagged months |
| 12 | `EPX_OTHER` is kept although it is resin minus inputs | Clean, don't curate; same-month use leaks the resin price | Forecasters must not use it for same-month resin |

---

## Backtest harness

**What it answers:** "Had we used this model since 2020, how good would its P10 / P50 / P90 have
been?" Forecasters write only the model function; the harness runs it, scores it and compares it
with other models. **Choosing a model stays with the forecasters**: the harness only gives them the
evidence.

### How it works in three steps
```python
results = run_backtest(model, name="ets_v1")  # 1. replay the past: one row per forecast
scores = score(results)  # 2. turn the rows into metrics
compare(score(rw_results), scores)  # 3. put models side by side
```

| Step | You give | You get |
|---|---|---|
| 1. `run_backtest` | the model function, a name; optional: `targets` (all 19), `horizons` (3, 6, 9), `start` (2020-01), `strict` (off), `refit_every` (1) | One row per forecast: model, target, origin, horizon, target month, P10 / P50 / P90, actual, last value, flagged. Saved to `outputs/backtest/<name>.csv` (gitignored), with runtime and CO₂ |
| 2. `score` | the rows from step 1; optional: `drop_flagged` (off) | One row per target × horizon with every metric below, overall and for 2020–22 vs 2023–26 |
| 3. `compare` | several `score` tables, the first one is the baseline | One table: each model's metrics plus its skill vs the baseline |

Step 1 is the slow one and runs once per model; steps 2 and 3 are instant and can be redone in
different ways. Data (prices and catalog) comes from the pipeline outputs.

### The model function
```python
def my_model(history, target, horizon, origin):  # history = only what was known at origin
    ...  # forecast month = origin + horizon, always
    return p10, p50, p90  # price levels, target's unit
```
- `origin` is passed explicitly: for L02 the last value is one month before the origin, but the
  forecast month is still origin + h.
- Slow models can instead be an object with `fit(history, target, horizon, origin)` and
  `predict(history, target, horizon, origin)`; `refit_every=k` then calls `fit` every *k* origins
  and `predict` at every origin.
- The run stops on model errors or invalid outputs (non-finite, ≤ 0, crossing quantiles).

### How the past is replayed
- **One forecast origin per month**, from 2020-01 to 2026-09 − h, at horizons 3 / 6 / 9.
- **Expanding window:** each origin uses all history before it, as a real forecaster would.
- **Not k-fold cross-validation:** random folds train on the future and leak neighbouring months.

### What the model is allowed to see at origin *o* (no leakage)
1. **No rows after *o*.**
2. **Each series cut by what was missing at *o*:**
   - **strict run** (`strict=True`, **used for model selection**): cut at
     *o* − max(`pub_lag`, `gap_months`), i.e. only data already **published** at *o*, as on the
     quote date. Scores are lower and more honest.
   - **main run** (default, reported for reference): cut at *o* − `gap_months`, the same data
     situation as our 2026-09 snapshot (L02 one month short, EU crude imports two).

   Targets and inputs follow the same rule in both runs.
3. **A copy of `history`, nothing else:** everything the model learns (fit, bands, calibration)
   uses only values known at *o*.

### Two options of `run_backtest`
| Option | What it does | Why |
|---|---|---|
| `strict=True` | Cuts each series at *o* − max(`pub_lag`, `gap_months`): only data already **published** at *o* | The run models are selected on: a forecast made on the quote date, when the latest months are not out yet. The main run is reported next to it |
| `refit_every=k` | Fits the model once every *k* origins and reuses that fit, applied to the newest history, in between | Keeps slow models (pretrained, large LightGBM) fast: about 4,400 model calls per full run |

### Metrics (`score`)
| Metric | Question it answers |
|---|---|
| MAE of log error (P50) | How far is the P50 from the actual? (scale-free) |
| MAPE (P50) | Same, in %, for the slides |
| Pinball loss (log scale) | How good are P10, P50 and P90 together? |
| Interval score (80 %) | Are the bands narrow **and** do they hold? (width + 10 × misses) |
| Coverage | How often is the actual inside P10–P90? (target ≈ 0.80) |
| Below-P10, above-P90 rates | Do the misses happen on the downside or the upside? |
| Width (P90 − P10) / P50 | How wide are the bands? |
| n, effective n (n / h) | How many forecasts, and how many really independent ones? |

- Every metric is split into **2020–22 (shock) and 2023–26 (calm)** by target month.
- `drop_flagged=True` re-scores without known data errors (epoxy May 2026).
- `compare` adds **skill = 1 − model error / baseline error** (> 0 beats the baseline) for log
  error, pinball loss and interval score. The random walk's P50 error comes from `last value`, so
  it needs no model.

### Plots
- **Rolling 12-month coverage** per target: shows when the bands stop holding (e.g. 2021–22).
- **Fan chart** per target: actual price against P10 / P50 / P90 at each origin, for the slides.

### Tests (synthetic data, in CI)
- History never has a value past each series' cutoff, in the main and the strict run.
- An L02-like series ending at *o* − 1 still gets target month *o* + h.
- A random walk on a known series gives known errors and skill 0 against itself.
- Pinball loss, interval score and coverage on hand-checked numbers.
- `refit_every` gives the same forecasts as refitting every time for a model with no fit.
- Invalid outputs are rejected.

**Limits** (stated in the README): one data vintage, so revised PPIs flatter results; publication
lags estimated (they drive the strict run, used for selection); overlapping windows leave ≈ 26 / 12 / 8 independent errors at +3 /
+6 / +9.

---

## Proof: README, CI, licence and CO₂ table
- **CI** (GitHub Actions): ruff and the tests on synthetic data on every push and pull request.
  It has no confidential data, so the forecast CSV is built locally.
- **README:** approach, the commands to rebuild the data and the CSV, data limits, AI-tool
  disclosure.
- **Licence and CO₂ table** in [`models_and_licenses.md`](models_and_licenses.md): every model and
  library with its licence, plus runtime and CO₂ from the backtest runs (`outputs/backtest/*_run.json`).
- **Submission CSV:** built by `schneider_forecast.submit` from the material forecasts and the six
  cost-index rows. Non-EUR/t series are submitted as `index (origin=100)`, so no USD band is
  converted with a forecast exchange rate; regions are `EU` or `WW`.
