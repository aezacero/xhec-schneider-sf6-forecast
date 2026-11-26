# Forecasting steel and stainless

Steel coils (L01, L03), stainless (L02), the EU and German steel price indices (S09, S10), the US
steel index (S12), nickel (S03), iron ore (S04) and zinc (S05). Code: `p2_models.py`,
`p2_selection.py`, `pooled.py`, `features.py`, `total_cost.py`.

Section numbers (§) refer to [`eda_findings.md`](eda_findings.md). The overall method is in
[`methodology.md`](methodology.md); the shared bands are in
[`forecasting_other.md`](forecasting_other.md) §2.

## Summary
- Every model predicts the h-month log change directly for each horizon (3, 6, 9 months), then
  converts it back to €/t or index. Prices are nominal.
- Every model uses the shared volatility-scaled band (half-life 3 months, volatility capped at
  2× its median), so models only differ in their P50.
- A model replaces the random walk only if its P50 is no worse in 2020–22 **and** in 2023–26 on
  the strict backtest (only data already published at each origin). The simpler model wins a tie.
- Final choice: a pooled MEPS model for the coils, the steel indices led by MEPS, Chronos-2 for
  stainless and zinc (+6 / +9), the random walk for nickel, iron ore and the US index.
- Forecasting each material and adding them up with the BOM (bottom-up) beats forecasting the
  product's total cost directly (top-down) at every horizon.

## Model interface
```python
def model(history, target, horizon, origin) -> tuple[float, float, float]:
    """Return (p10, p50, p90) in the target's own unit (€/t or index), not in log."""
```
- The harness (`backtest.py`) cuts `history` at each origin; models never cut data themselves.
  Main run: each series loses its last `gap_months`, as on the real 2026-09 forecast. Strict run:
  it loses `max(pub_lag, gap_months)`.
- Target month = origin + `horizon`, so L02 (which ends in 2026-08) is forecast 4 / 7 / 10 months
  from its last value without a special case.
- Models that fit on many series are objects with `fit()` and `predict()`;
  `run_backtest(..., refit_every=k)` refits every k origins.

## Models
| Model | Targets | P50 | Features kept |
|---|---|---|---|
| `meps_pooled` | L01, L03 | Median regression (L1, no intercept) trained on the 8 MEPS coil prices together | 1-month momentum, steel season (March up, June–July down, §5) |
| `steel_ppi_lead` | S09 ← L01, S10 ← L03 | Same model, pooled over the two indices | Own 1- and 3-month momentum, the latest 1-month change of the MEPS coil (published a month earlier) |
| Chronos-2 | L02 (+3 / +6 / +9), S05 (+6 / +9) | Pretrained model, zero-shot on the series' own history, local CPU | — |
| Random walk | S03, S04, S12, S05 (+3) | Last published value | — |

- Every change is in volatility units (log change ÷ EWMA volatility × √months), so the 8 coils
  share one scale. With all coefficients at zero the model is the random walk. With fewer than
  36 training rows (early origins for series that start in 2016-11) the P50 falls back to the
  last value.
- A feature stays only if its coefficient keeps the same sign when the model is fitted before and
  after 2020. This rule was set before looking at the backtest.
- At +9, the coils hold their 3-month P50 and the steel indices hold their 6-month P50, with the
  9-month band around it. The index catches up with MEPS within about 6 months; extrapolating
  further overshoots.

## Final selection
`uv run python -m schneider_forecast.p2_selection` (needs `uv sync --extra pretrained` for
Chronos-2) writes the forecasts at origin 2026-09 to `outputs/forecasts/p2_forecasts_202609.csv`
and the strict backtest of the selection to `outputs/backtest/p2_selected_strict.csv`.

| Target | +3 | +6 | +9 |
|---|---|---|---|
| L01, L03 | `meps_pooled` | `meps_pooled` | `meps_pooled` 3-month P50 held |
| S09, S10 | `steel_ppi_lead` | `steel_ppi_lead` | `steel_ppi_lead` 6-month P50 held |
| L02 | Chronos-2 | Chronos-2 | Chronos-2 |
| S05 | random walk | Chronos-2 | Chronos-2 |
| S03, S04, S12 | random walk | random walk | random walk |

## Results (strict run, origins 2020-01 to 2026-09)
P50 skill vs the random walk (1 − model error ÷ random-walk error), all periods:

| Target | +3 | +6 | +9 |
|---|---|---|---|
| S09 | +27 % | +22 % | +20 % |
| S10 | +24 % | +19 % | +20 % |
| L03 | +11 % | +8 % | +1 % |
| L01 | +11 % | +9 % | +1 % |
| L02 | +9 % | +9 % | +8 % |
| S05 | 0 | +10 % | +11 % |
| S03, S04, S12 | 0 | 0 | 0 |

Every choice is no worse than the random walk in 2020–22 and in 2023–26.

P10–P90 coverage (target 0.80):

| Target | +3 | +6 | +9 |
|---|---|---|---|
| L01 | 0.73 | 0.80 | 0.81 |
| L03 | 0.81 | 0.81 | 0.82 |
| L02 | 0.81 | 0.68 | 0.68 |
| S09 | 0.76 | 0.77 | 0.79 |
| S10 | 0.76 | 0.83 | 0.83 |
| Mean of the 9 targets | 0.80 | 0.81 | 0.81 |
| Mean, 2020–22 | 0.61 | 0.62 | 0.57 |
| Mean, 2023–26 | 0.93 | 0.93 | 0.95 |

- On average the band is on target, but it is too narrow in shocks and too wide in calm years
  (L01 and L03 cover 1.00 in 2023–26 at +3 / +6). This comes from the shared band, not the P50
  models: the random-walk cells show the same pattern.
- Stainless at +6 / +9 is too narrow (0.68; 0.47 / 0.41 in 2020–22).
- Overlapping windows leave about 26 / 12 / 8 independent errors at +3 / +6 / +9, so small
  differences are not proof.

## Forecasts at origin 2026-09
P50 change vs the last value, +3 / +6 / +9: L01 +1.8 / +4.9 / +1.8 %, L03 +1.1 / +3.9 / +1.1 %,
S09 +1.4 / +1.7 / +1.7 %, S10 +1.8 / +2.5 / +2.5 %, L02 −1.5 / −0.9 / −2.8 % (from Aug 2026),
S05 0 / −5.1 / −11.3 % (after +26 % in 6 months), S03 / S04 / S12 flat. The +9 band goes from
−4 / +13 % (S10) to −13 / +50 % (S12).

## Total cost: top-down vs bottom-up
**Question:** is it better to forecast a product's total raw-material cost directly (top-down)
or to forecast each material and add them up with the BOM (bottom-up)?

The total cost (`total_cost.py`) is Σ kg × price per kg over the priced v1 BOM lines; only the
masses are fixed, so the history uses no later prices. The total is known only when its slowest
line is (stainless: 3-month publication lag).

P50 skill vs the top-down random walk, strict run (+3 / +6 / +9):

| Approach | AirSeT | RM6 |
|---|---|---|
| **Bottom-up, chosen material models** | **+14 / +14 / +8 %** | **+12 / +10 / +6 %** |
| Bottom-up, random walk per material | +10 / +9 / +7 % | +9 / +7 / +6 % |
| Top-down, damped trend | −5 / −3 / +1 % | −4 / −2 / −2 % |
| Top-down, momentum + steel season | +1 / −2 / −13 % | −1 / −5 / −17 % |

- Bottom-up wins at every horizon for both products, in both periods.
- Two sources of the gain: fresher data (each material enters from its own last month, while the
  total waits for its slowest line), worth +7 to +10 %; and better material models, worth another
  3–5 points.
- No top-down model beats the random walk on the total.
- The product cost index in the pricing step is therefore built bottom-up
  ([`pricing.md`](pricing.md)).

## Tried and dropped
| Idea | Result |
|---|---|
| One pooled quantile model for all 19 materials (`pooled.py`) | Mean skill −1 / −10 / −15 % strict; wins only on EU price indices and MEPS steel at +3 |
| Stainless with nickel and EUR/USD, or nickel only | Signs flip before and after 2020; loses to the random walk. Nickel is known only a month before stainless and its effect lasts 1–2 months |
| Zinc and TTF gas as steel drivers | Gas flips sign at +6 / +9 on the coils; on the steel indices worse at +3 on the strict run |
| Momentum by material group in the pooled model | No gain; momentum is noise for exchange-traded prices |
| Training on each coil alone, or on the 4 German coils | Same at +3, worse at +6 / +9; the 8-coil pool is more stable |
| Chronos-Bolt | Loses almost everywhere on steel |
| Blend of damped trend and Chronos-2 on stainless | Wins in 2020–22 only; Chronos-2 alone is positive in both periods |
| Carrying each material's last price forward, then forecasting the total | Same P50 as bottom-up with random walks; narrower, worse bands |

## Future work
1. HAC (Newey-West) standard errors or a block bootstrap for the kept features, for
   explainability only: training rows overlap, so plain p-values are too optimistic.
2. Metals from the latest exchange price instead of the monthly average (test on copper with
   the LME cash series).
3. Distance from the 12-month high in `meps_pooled`.
