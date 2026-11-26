# Forecasting copper, aluminium, plastics, epoxy and EUR/USD, and the shared bands

## Summary
- **10 targets** (`p3_models.P3_TARGETS`): copper D01 (€/t), S01 ($/t), S07 (EU index);
  aluminium D02, S02, S08; plastics S11 (EU), S13 (world); epoxy `EPX_RESIN`; EUR/USD S06.
- **8 models tested** with the backtest harness (origins 2020-01 → 2026-09, horizons 3 / 6 / 9).
- **Best P50: average of a damped trend and Chronos-2 with drivers.** It wins clearly on the
  smooth series (S08, S11, epoxy) and ties or loses slightly on exchange-traded prices (copper,
  aluminium €/t and $/t, EUR/USD), where the random walk stays the realistic choice.
- **Bands:** volatility-scaled bands (shared module `bands.py`) are the best at
  +6 / +9. Calm years now cover ≈ 80 %; crisis years (2020–22) still only 44–68 %.
- **Known data errors are ignored by every model and band** (epoxy May 2026): the final epoxy
  band at +9 is €4,188–6,421 instead of €2,697–14,095.
- **2021–22 surge: kept with equal weight.** Volatility scaling already divides crisis moves by
  the crisis volatility; extra down-weighting adds nothing in a fair test (§2b).
- **Volatility cap:** today's volatility counts at most 2× its usual level, so bands stay
  realistic after a wild spell (S11 at +9: +87 % → +42 %); better in both runs (§2c).
- **Final selection on the strict run (§3):** the blend in 7 of 30 cells
  (epoxy, S08, S11 at +3 / +6; S07 at +3), the random walk elsewhere.
- **Delivery:** `uv run python -m schneider_forecast.p3_selection` writes the 2026-09 forecasts
  and the selection's backtests (§5).

Numbers and § refer to [`eda_findings.md`](eda_findings.md); the harness is described in
[`data_pipeline.md`](data_pipeline.md).

## How to read the scores
| Score | Meaning | Good |
|---|---|---|
| P50 skill | 1 − P50 error ÷ error of "last value" (random walk) | > 0 |
| Band score | Interval score (band width + 10 × distance of any miss) vs the random walk with empirical bands | > 0 |
| Coverage | Share of actual prices inside P10–P90 | ≈ 0.80 |

Few independent errors exist (≈ 26 / 12 / 8 at +3 / +6 / +9, §7): differences of a few % are not
proof.

**Two backtest runs**: the *main* run cuts each series at its last value, as on the
real 2026-09 data; the *strict* run also drops the months not yet published at each origin
(`pub_lag`: 2 months for most of these series). Strict scores are lower and more honest. §1–§2c were
run on the main run; the final selection (§3) is decided on the strict run only.

## 1. Models (`src/schneider_forecast/p3_models.py`)
All follow the harness interface `model(history, target, horizon, origin) -> (p10, p50, p90)`.

| Model | Idea | License |
|---|---|---|
| `rw_empirical` (bar, in the run script) | Last value; band = past h-month change quantiles | — |
| `ets_damped` | Damped-trend exponential smoothing on log prices; band = past change spread around its P50 | statsmodels, BSD |
| `driver_qr` | Direct quantile regression (L1) on own and driver changes; drivers from the kept list (§6) | scikit-learn, BSD |
| `chronos_bolt` | Pretrained Chronos-Bolt small / base, zero-shot, local CPU | Apache-2.0 |
| `chronos2` | Pretrained Chronos-2, zero-shot, with or without drivers as past covariates, local CPU | Apache-2.0 |
| `blend_results` | Geometric mean of two models' quantiles (here `ets_damped` + `chronos2` with drivers) | — |

Pretrained models need the optional extra: `uv sync --extra pretrained` (PyTorch, ≈ 1 GB; CI does
not install it and their tests skip). Weights download once from Hugging Face; **no data leaves
the PC** (NDA).

### Average over the 10 targets, all periods (+3 / +6 / +9)
| Model | P50 skill | Band score | Coverage |
|---|---|---|---|
| Random walk, empirical bands | 0 / −4 / −7 % | 0 / 0 / 0 | 0.64 / 0.65 / 0.61 |
| Damped trend | +2 / 0 / −5 % | 0 / +3 / +1 % | 0.67 / 0.67 / 0.63 |
| Driver quantile regression | worse everywhere (overfits ≈ 100 rows) | −15 % | 0.57 / 0.56 / 0.57 |
| Chronos-Bolt small | −1 / −3 / −7 % | −2 / +1 / +5 % | 0.72 / 0.69 / 0.67 |
| Chronos-2 with drivers | +1 / −1 / −5 % | 0 / +1 / +4 % | 0.72 / 0.66 / 0.64 |
| **Damped trend + Chronos-2 with drivers** | **+3 / +1 / −2 %** | **+4 / +7 / +9 %** | 0.71 / 0.68 / 0.66 |

Chronos-Bolt base was no better than small and 3× slower. A stronger L1 penalty did not rescue
`driver_qr`.

### P50 skill per target (%, +3 / +6 / +9)
| Target | Damped trend | Chronos-Bolt | Chronos-2 + drivers | **Blend** |
|---|---|---|---|---|
| S08 aluminium PPI | +30 / +16 / −1 | +26 / +13 / −2 | +30 / +13 / +4 | **+30 / +19 / +8** |
| S11 plastics PPI EU | +6 / +11 / +3 | +2 / +4 / −4 | +17 / +15 / +7 | **+12 / +14 / +8** |
| EPX_RESIN | +8 / +3 / −5 | −6 / −13 / −18 | +6 / +2 / −4 | **+8 / +3 / −3** |
| S07 copper PPI | +5 / +4 / +2 | −1 / 0 / −12 | −2 / −5 / −12 | +3 / +1 / −3 |
| D02 aluminium €/t | −3 / −4 / −11 | −4 / −4 / −10 | +1 / +1 / +3 | −1 / +1 / −2 |
| S02 aluminium $/t | −4 / −7 / −8 | 0 / +1 / +1 | −1 / −1 / −3 | −1 / −2 / −3 |
| S06 EUR/USD | −1 / −9 / −12 | +4 / +6 / +10 | −8 / −6 / −3 | −2 / −5 / −5 |
| D01 copper €/t | +2 / +2 / +3 | −6 / −3 / −6 | −8 / −10 / −13 | −2 / −2 / −3 |
| S01 copper $/t | −2 / −4 / −5 | −8 / −7 / −6 | −9 / −10 / −15 | −5 / −5 / −7 |
| S13 plastics PPI world | −9 / −15 / −18 | −8 / −25 / −26 | +3 / −7 / −9 | −1 / −8 / −11 |

Reading: smooth series (PPIs, epoxy) trend, so models win; exchange-traded prices (LME metals, FX)
behave as random walks (§5), so no model reliably beats the last value.

## 2. Bands (`src/schneider_forecast/bands.py`, shared)
Shared by every model in the project.

| Method | Idea | Verdict |
|---|---|---|
| `rw_vol_scaled` / `with_vol_bands(model)` | Past h-month changes ÷ EWMA volatility at their start; quantiles × volatility today. Reacts within 1–2 months of a shock | **Kept** (halflife 3 months) |
| `calibrate_results` | Rescale bands so past forecasts covered 80 % (all or last 12 / 24 / 36 outcomes) | Rejected: an h-month miss is known only h months later, so bands widen after the shock and stay too wide |
| `adaptive_results` | Adaptive conformal: widen after each known miss, narrow after each hit | Rejected: same delay |
| `envelope_results` | Wider of two bands | No gain over volatility scaling |

Average over the 10 targets, blend P50 (+3 / +6 / +9):

| Band | Band score | Coverage all | 2020–22 | 2023–26 |
|---|---|---|---|---|
| Blend's own band | **+4** / +7 / +9 % | 0.71 / 0.68 / 0.66 | 0.57 / 0.43 / 0.38 | 0.82 / 0.85 / 0.83 |
| Volatility-scaled, halflife 3 | +1 / **+9** / **+14** % | 0.76 / 0.73 / 0.70 | 0.68 / 0.56 / 0.44 | 0.82 / 0.83 / 0.85 |
| Volatility-scaled, halflife 6 / 12 | +1 / +9 / +9 % · +1 / +6 / +5 % | ≈ 0.76 / 0.74 / 0.70 | lower | wider than needed |
| Adaptive (γ = 0.05) | +2 / +3 / +2 % | 0.77 / 0.76 / 0.72 | 0.65 / 0.54 / 0.46 | 0.85 / 0.90 / 0.89 |

Halflife 2 ties with 3; 3 is steadier in calm years.

### 2b. The 2021–22 surge: down-weighting tested (EDA §5)
Volatility-scaled bands (halflife 3) around the blend P50, with past moves weighted by start month
(`move_weights`): crisis moves (starting 2021–22) counting ½ or ¼, or time decay (a move 36 / 60
months old counts half).

| Weighting | Band score all (+3 / +6 / +9) | 2023–26 (fair test) | 2020–22 |
|---|---|---|---|
| Equal weights | −0.1 / +9.2 / +13.7 % | −10.7 / −8.7 / +0.1 % | +8.2 / +20.7 / +22.3 % |
| Crisis × ½ | −0.7 / +10.3 / +14.7 % | −10.7 / −8.6 / −1.0 % | +7.1 / +22.5 / +24.7 % |
| Crisis × ¼ | −0.9 / +10.1 / +14.3 % | −10.7 / −8.8 / −1.3 % | +6.9 / +22.3 / +24.2 % |
| Decay 36 months | −3.0 / +7.9 / +12.8 % | −12.5 / −10.9 / −3.9 % | +4.4 / +20.1 / +23.4 % |
| Decay 60 months | −2.0 / +8.7 / +13.4 % | −12.0 / −10.2 / −2.7 % | +5.9 / +21.0 / +23.6 % |

- The crisis weight looks slightly better overall, but only in 2020–22, where it uses hindsight
  (in 2021 nobody knew the surge would end in 2022). In 2023–26, the fair test, it adds nothing.
- Time decay is slightly worse everywhere.
- **Decision: keep 2021–22 with equal weight.** Volatility scaling is the principled
  down-weighting: a +30 % move in a ×3-volatility month counts like +10 % in a calm month.
- The damped trend and Chronos cannot be weighted by month (sequential fit / pretrained), so the
  test covers the bands, where the surge mattered most.

### 2c. Volatility cap
At the 2026-09 origin, S11's volatility is 3.6× its usual level (+11 % in one month this year).
Uncapped, its +9 band reached +87 %, while its largest 9-month rise ever is +30 %: one wild month
does not make a slow index's 9-month move 3.6× larger. Two guards were tested on the random walk
with volatility bands (band score, average over the 10 targets, +3 / +6 / +9):

| Guard | Strict run, all | Main run, all | Final +9 band S11 / S13 |
|---|---|---|---|
| None | +6.6 / +12.9 / +13.4 % | −0.6 / +9.8 / +15.1 % | +87 % / +44 % |
| **Cap at 2× median volatility** | **+7.7 / +14.8 / +14.4 %** | **+0.1 / +11.4 / +16.7 %** | **+42 % / +30 %** |
| Cap at 1.5× | +6.9 / +14.1 / +14.0 % | −0.5 / +10.5 / +16.1 % | +30 % / +22 % |
| Clip to the largest past move | +8.8 / +13.8 / +13.3 % | +1.0 / +11.7 / +15.2 % | +31 % / +40 % |

The 2× cap improves both runs at every horizon, calm years included, so it is the default
(`bands.MAX_VOL_RATIO = 2`; `max_vol_ratio=None` switches it off). Copper and aluminium are not
affected (volatility ≤ 1.2× normal); aluminium's +50 % at +9 matches its history (+56 %).

## 3. Final selection
**Rule (the same for the steel models):** the blend replaces the random walk for a
target × horizon only if its P50 is no worse than the random walk in 2020–22 **and** in 2023–26
on the **strict** run. Otherwise the simpler model (random walk) is kept. This replaces the
earlier "one model per group" proposal, which failed at +9 (the blend loses in 2023–26 for all
four smooth series there). Adding the main run as a second check would only drop S11 at +3
(main 2023–26: −3 %); a −3 % tolerance per period changes nothing.

Blend P50 skill vs the random walk on the strict run (%), as 2020–22 / 2023–26 → choice
(main run in brackets, for information):

| Target | +3 | +6 | +9 |
|---|---|---|---|
| EPX_RESIN | +2 / +16 → **blend** (+11 / +21) | +3 / +1 → **blend** (+5 / +1) | +4 / −16 → RW |
| S08 | +24 / +21 → **blend** (+36 / +21) | +11 / +13 → **blend** (+19 / +20) | +15 / −26 → RW |
| S11 | +16 / +4 → **blend** (+25 / −3) | +15 / +4 → **blend** (+14 / +15) | +13 / −7 → RW |
| S07 | +2 / +1 → **blend** (+4 / +2) | 0 / −2 → RW | +4 / −6 → RW |
| D01, D02, S01, S02, S06, S13 | fails in at least one period → RW | RW | RW |

| Target | +3 | +6 | +9 |
|---|---|---|---|
| EPX_RESIN, S08, S11 | blend, own band | blend, volatility band | random walk |
| S07 | blend, own band | random walk | random walk |
| D01, S01, D02, S02, S06, S13 | random walk | random walk | random walk |

Random walk = last value + volatility band (halflife 3, 2× cap). Blend = geometric mean of
`ets_damped` and `chronos2` with drivers.

**Selection backtest** (average over the 10 targets, +3 / +6 / +9):

| Run | P50 skill | Coverage all | 2020–22 | 2023–26 |
|---|---|---|---|---|
| Strict | +4.3 / +2.4 / 0 % | 0.72 / 0.70 / 0.72 | 0.52 / 0.46 / 0.43 | 0.86 / 0.86 / 0.89 |
| Main | +6.1 / +3.6 / 0 % | 0.74 / 0.71 / 0.70 | 0.62 / 0.53 / 0.42 | 0.83 / 0.84 / 0.87 |

- On average the P50 beats the random walk in both periods of both runs (+9 is the random walk).
- Coverage is ≈ 0.85 in calm years (slightly wide, as for steel) and below target in the
  crisis: no tested method fixes both (§2, §4).

**Final forecasts at 2026-09** (P50, band as % of P50):

| Target | +3 | +6 | +9 |
|---|---|---|---|
| D01 copper €/t | 12,571 (−9 / +10 %) | 12,571 (−12 / +15 %) | 12,571 (−11 / +22 %) |
| D02 aluminium €/t | 2,852 (−11 / +19 %) | 2,852 (−14 / +28 %) | 2,852 (−13 / +50 %) |
| EPX_RESIN €/t | 4,863 (−6 / +8 %) | 4,861 (−13 / +20 %) | 4,866 (−14 / +32 %) |
| S11 plastics EU (index) | 112.9 (−5 / +7 %) | 112.5 (−11 / +26 %) | 113.6 (−15 / +42 %) |
| S06 EUR/USD | 1.151 (−3 / +4 %) | 1.151 (−5 / +5 %) | 1.151 (−5 / +8 %) |

Bands lean upward: past moves of these series were mostly up (EDA §5, fat right tails).

## 4. Limits and open points
| Issue | Status |
|---|---|
| Epoxy May 2026 data error | Every model and band skips months flagged as `error` (`bands.target_logs`, transformation M1); the final epoxy band at +9 is €4,188–6,421 instead of €2,697–14,095 |
| Crisis bands too narrow (2020–22 coverage 43–52 % in the final selection) | Stated as a limit; shocks are handled by indexation in the quote rules, not by wider bands |
| Calm-year coverage ≈ 0.86–0.89, slightly above 0.80 | A property of the band, not the P50; acceptable for a buyer's buffer |
| Several targets per material (copper D01 / S01 / S07, aluminium D02 / S02 / S08, plastics S11 / S13) | All forecast; the cost index uses D01, D02, S11 and EPX_RESIN |
| Pooled model on these targets | Beats the naive on S08 / S11, but the blend is equal or better, so the blend is kept |

## 5. Outputs
One command, same layout as `p2_selection`:
```bash
uv sync --extra pretrained                        # once: Chronos-2 (local CPU)
uv run python -m schneider_forecast.data          # clean data
uv run python -m schneider_forecast.p3_selection  # forecasts + backtests
```
| File (`outputs/`, never committed) | Content | Used by |
|---|---|---|
| `forecasts/p3_forecasts_202609.csv` | 30 rows (10 targets × 3 horizons) at origin 2026-09: `target_type, target_id, origin_month, horizon_m, target_month, unit, p10, p50, p90, model_name` | The submission builder adds `team_id`, `region`, `ai_tools` |
| `backtest/p3_selected_strict.csv`, `p3_selected.csv` | The selection replayed at every origin since 2020: `p10, p50, p90, actual, last_value` per origin × target × horizon | The cost-index backtest |

Code: `p3_selection.SELECTION` (target × horizon → model), `p3_selected` (harness model),
`final_forecasts`. Runtime ≈ 3 min on a laptop CPU.

## How to reproduce the comparisons
```python
from functools import partial
from schneider_forecast.backtest import run_backtest
from schneider_forecast.bands import rw_vol_scaled
from schneider_forecast.metrics import score
from schneider_forecast.p3_models import P3_TARGETS, blend_results, chronos2, ets_damped

targets = list(P3_TARGETS)
ets = run_backtest(ets_damped, "p3_ets_damped", targets=targets)
c2 = run_backtest(partial(chronos2, covariates=True), "p3_chronos2_cov", targets=targets)
vol = run_backtest(partial(rw_vol_scaled, halflife=3), "p3_rw_vol_hl3", targets=targets)
blend = blend_results("p3_blend", ets, c2)
score(blend)
```
Runtime on a laptop CPU: ≈ 40 s (damped trend), ≈ 90 s (Chronos-2), ≈ 10 s (volatility bands);
CO₂ ≈ 2–6 × 10⁻⁵ kg per run (codecarbon, logged in `outputs/backtest/*_run.json`).
