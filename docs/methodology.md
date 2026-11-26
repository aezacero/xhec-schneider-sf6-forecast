# Methodology

How each part of the solution is built. Section numbers (§) refer to
[`eda_findings.md`](eda_findings.md). Details per part:
[`data_pipeline.md`](data_pipeline.md) (data and backtest),
[`forecasting_steel.md`](forecasting_steel.md) (steel and stainless),
[`forecasting_other.md`](forecasting_other.md) (other materials and the shared bands),
[`pricing.md`](pricing.md) (cost index and quote rules).

## 1. What is delivered

| Deliverable | Content |
|---|---|
| Forecast CSV | 19 raw-material series × {3, 6, 9} months and a cost index for RM6 and RM AirSeT × {3, 6, 9}, each with P10 / P50 / P90: `outputs/forecasts/team_05_forecast_202609.csv` |
| Repo | README (approach, data limits, AI disclosure), pinned dependencies (`uv.lock`), the commands that rebuild the CSV, a backtest of every model against the random walk at all three horizons, CI |
| Decision tool | A Streamlit app that prices a quote from the forecasts (`app/`) |
| Strategy | Goal B: a voluntary switch from SM6 to SM AirSeT in markets with no SF6 rule (section 5) |

The backtest and its validation matter more than raw accuracy: the forecasts are judged on a
strict replay against a naive baseline, and on how well P10–P90 covers the outcomes.

## 2. End-to-end pipeline

```
 data/raw ──► [data pipeline] ──► monthly table cut at 2026-09, publication lags, error flags
                                │
                                ▼
                 [forecasting ladder: steel / other materials]
                 direct h = 3 / 6 / 9, P10 / P50 / P90, strict backtest vs the random walk
                                │
              ┌─────────────────┴──────────────────┐
              ▼                                    ▼
   [pricing, Goal A]                     [strategy, Goal B]
   cost index (joint simulation)         RM6 vs AirSeT cost gap and quote validity,
   → margin at risk → quote rules        TCO, SF6 risk, competitors, markets
              │                                    │
              └──────────► forecast CSV + decision tool + slides
```

Every model has the same interface:
`model(history, target, horizon, origin) -> (p10, p50, p90)`; the forecast month is always
`origin + horizon`.

## 3. Forecasts

### 3.1 Targets
Origin **2026-09** for every target; target months 2026-12, 2027-03, 2027-06. Stainless 304 ends
2026-08, so it is forecast 4 / 7 / 10 months out from its last value.

| Material | target_id | Series | Unit |
|---|---|---|---|
| Carbon steel | L01 | MEPS cold-rolled coil, Germany | EUR/t |
| Stainless steel | L02 | CRU 304 cold-rolled, base + alloy | EUR/t |
| Galvanised steel | L03 | MEPS HDG coil, Germany | EUR/t |
| Steel indices, iron ore, zinc, nickel | S09, S10, S12, S04, S05, S03 | as in the dataset | index / USD/t |
| Copper | D01, S01, S07 | LME copper in EUR and USD; EU copper index | EUR/t, USD/t, index |
| Aluminium | D02, S02, S08 | LME aluminium in EUR and USD; EU aluminium index | EUR/t, USD/t, index |
| Plastics | S11, S13 | EU and US plastics indices | index |
| Epoxy | EPX_RESIN | Epoxy resin price | EUR/t |
| FX | S06 | EUR/USD | USD per EUR |

Electronics have no price data and a small cost impact: left out and stated as a limit. Prices
are nominal, which is what a buyer pays.

### 3.2 Model ladder
Each rung is kept only if it beats the rung below in the strict backtest.

| Rung | Model | Kept for |
|---|---|---|
| 0 | Random walk with volatility-scaled bands | Baseline everywhere; final choice for copper, aluminium, nickel, iron ore, EUR/USD, US indices and most +9 cells |
| 1 | Damped-trend exponential smoothing | Inside the blend only |
| 2 | Pooled driver models: MEPS coils (`meps_pooled`), steel indices led by MEPS (`steel_ppi_lead`) | L01, L03, S09, S10 |
| 3 | One pooled quantile model for all materials | Dropped |
| 4 | Chronos-2, zero-shot, local CPU | Stainless (L02), zinc at +6 / +9 |
| 4b | Blend: geometric mean of damped trend and Chronos-2 with drivers | Epoxy, EU aluminium and plastics indices at +3 / +6; EU copper index at +3 |

Principles:
- **Predict the h-month log change** `log(y[t+h] / y[t])` directly for each horizon, then convert
  back to €/t or index. It is scale-free, so it can be pooled across series.
- About 120 monthly points per series: few features, strong regularisation, no deep training.
- Copper and aluminium behave like random walks (§5–§7), so the work there is on the bands, not
  the P50. Price indices, steel and epoxy have momentum: that is where models win.
- Pretrained models run locally; no data is sent to a third-party service.

### 3.3 Features (all known at the forecast date)
- Own past changes over 1, 3 and 6 months; EWMA volatility.
- Drivers only if their effect keeps the same sign before 2020 and over the full sample (§6):
  MEPS coil for the steel indices; Brent, TTF gas and an energy index for plastics and epoxy;
  EUR/USD for aluminium and the copper index.
- Month terms for MEPS steel only (March up, June–July down, §5).
- Publication lags (§4): IMF prices and price indices M − 2, MEPS / CRU / FX / power / epoxy M − 1,
  CRU stainless M − 3. Target-month FX is never used.

### 3.4 Backtest and selection
- **Walk-forward, expanding window:** one origin per month from 2020-01, horizons 3 / 6 / 9,
  refitted at each origin. Not k-fold cross-validation, which would train on the future.
- **Strict run:** each series is cut at what had been published on the quote date. Model choice
  uses this run only.
- **Metrics:** MAPE of the P50; skill vs the random walk (1 − model error ÷ random-walk error);
  pinball loss; interval score; P10–P90 coverage (target 0.80). Each is split into 2020–22
  (shock) and 2023–26 (calm).
- **Selection rule:** a model replaces the random walk for a target × horizon only if its P50
  error is no worse in 2020–22 **and** in 2023–26. The simpler model wins a tie. Coverage is
  reported, not used to select.
- **Bands:** one shared method for every model: past h-month changes divided by the EWMA
  volatility at their start (half-life 3 months), multiplied by today's volatility, capped at 2×
  its median. The 2021–22 surge keeps equal weight.
- **Small sample:** overlapping windows leave about 26 / 12 / 8 independent errors at +3 / +6 / +9.
- Compute and CO₂ are tracked with `codecarbon` for every run.

## 4. Business link (Goal A)

### 4.1 Cost index
- Material cost per unit = Σ mass (kg) × price (€/kg) over the priced v1 BOM lines; weights are
  cost shares at 2026-09.
- Reported as an **index (origin = 100)** for the CSV and in € per unit for the explanation.
- **The quantile of a sum is not the sum of quantiles.** A joint simulation draws 10,000 past dates
  and reads every material's rank of change on that date, so materials move together as they did
  (§6: copper–aluminium 0.67, carbon steel–stainless 0.60), with the size of each move taken from
  its forecast.

### 4.2 From cost to margin at risk
- Priced raw material is **7.3 % (RM6) and 8.0 % (AirSeT)** of the €12,233 benchmark price. The
  true exposed share α is unknown, so results are also shown for α of 10, 17 and 25 %.
- Margin at risk at horizon h = α × (cost index P90 − 100) % of the price, shown for an assumed
  20 % margin (10 % and 30 % in the sensitivity).

### 4.3 Quote rules

| Lever | Rule |
|---|---|
| Price adjustment | quote = list price × (1 + α × (P50 index − 100) %) |
| Risk buffer | + α × (P90 − P50) %, so the cost beats it only 1 time in 10 |
| Quotation validity | the longest horizon where the buffer stays under 10 % of the margin (2 % of price) |
| Indexation trigger | when one index moves more than X = tolerance ÷ (α × its weight), the price is revised by α × the change |
| Scenarios | downside / baseline / upside = P10 / P50 / P90 |

Price did not follow cost in 2021 (RM6 cost +58 %, price +7 %; §11). A replay of 2020–23 shows
that a buffer cannot absorb such a shock without overpricing calm years, so shocks are handled by
indexation and the buffer covers normal months.

### 4.4 Decision tool
A Streamlit app: product, horizon, list price, margin and scenario in; quote price, buffer,
validity, margin at risk and indexation trigger out, plus € per material and the 2021 replay. It
reads only the pipeline outputs, and runs on generated demo data without them.

## 5. Strategy (Goal B)
Question: in markets with **no SF6 regulation**, how does Schneider win a **voluntary** switch from
SM6 to SM AirSeT? Goal A feeds it: AirSeT's priced raw material is ≈ €75 dearer than RM6's
(≈ 0.6 % of the price), Eaton's SF6-free premium over the SF6 brands fell from +46 % (2017) to
+1 % (2026), and AirSeT quotes hold 6 months against 9 for RM6 because of material risk.

The answer is to price near parity, sell reliability and lifetime value rather than a green
premium, and add an indexation clause so AirSeT quotes hold as long as SM6. Three markets:
the US ([`GoalB_US.md`](goal_b/GoalB_US.md)), India ([`GoalB_India.md`](goal_b/GoalB_India.md)) and
Malaysia–Singapore ([`GoalB_SEA.md`](goal_b/GoalB_SEA.md)), each with target
segments, competition, value proposition, pricing, levers, a roadmap and win conditions.
