# Models, data, AI tools and licences

This lists every model, library, data source and AI tool we used, with its licence, plus how long
a full run takes and what it emits. Library versions are pinned in `uv.lock`.

## Models used in the final forecast
| Model | Where we use it | Part | Licence | Code |
|---|---|---|---|---|
| Random walk with volatility-scaled bands (half-life 3 months, volatility capped at 2× normal) | The baseline for everything, and the final choice for copper, aluminium, EUR/USD, nickel, iron ore, US steel, S13 and most +9 forecasts | Forecasting | Our own code (numpy, pandas) | `bands.py` |
| Pooled median regression on the 8 MEPS coil series (`meps_pooled`) | L01 and L03 (carbon and galvanised steel); the +9 forecast reuses the +3 one | Steel models | scikit-learn `QuantileRegressor` (BSD-3-Clause) with the HiGHS solver (MIT) | `p2_models.py` |
| Steel price index led by MEPS (`steel_ppi_lead`) | S09 and S10; the +9 forecast reuses the +6 one | Steel models | scikit-learn (BSD-3-Clause) | `p2_models.py` |
| Chronos-2, run locally without training | L02 (stainless) at +3, +6 and +9; S05 (zinc) at +6 and +9 | Steel models | Apache-2.0 for the code and the `amazon/chronos-2` weights; PyTorch is BSD-3-Clause | `p3_models.py` |
| Average of a damped-trend model and Chronos-2 with drivers | Epoxy, S08 and S11 at +3 and +6; S07 at +3 | Other materials | statsmodels (BSD-3-Clause), Chronos-2 (Apache-2.0) | `p3_models.py` |
| Product cost index from a joint simulation of the materials (`simulate_index`) | The six product-index rows and the quote rules | Pricing | Our own code (numpy, pandas) | `pricing.py` |

## Models we tested and dropped
| Model | Why we dropped it | Part |
|---|---|---|
| Quantile regression on drivers (`driver_qr`) | With about 100 rows it overfits and loses to the random walk | Other materials |
| Chronos-Bolt, small and base | No better than Chronos-2, and the base model is three times slower | Other materials |
| One quantile model for all materials (`PooledQuantileModel`) | Only helps EU price indices and MEPS steel at +3 | Steel models |
| Forecasting each product's total cost directly | Adding up the material forecasts is better at every horizon | Steel models |
| Calibrating bands on past misses, adaptive bands | A miss is only known once the horizon has passed, so the bands react too late | Other materials |
| Extra crisis buffer on quotes | It counts volatility twice and overprices after a shock | Pricing |
| Naive cost index (`naive_index_band`) | Only used as the baseline in the index backtest | Pricing |

All of these are our own code or use the libraries below under the same licences.

## Libraries
| Library | Version | What for | Licence |
|---|---|---|---|
| pandas | 3.1.1 | Data handling | BSD-3-Clause |
| numpy | 2.5.5 | Numerics | BSD-3-Clause |
| scikit-learn | 1.9.1 | Quantile regression | BSD-3-Clause |
| SciPy | 1.18.1 | Ships the HiGHS solver scikit-learn uses | BSD-3-Clause (HiGHS: MIT) |
| statsmodels | 0.15.0 | Damped-trend exponential smoothing | BSD-3-Clause |
| matplotlib | 3.11.2 | Plots | Matplotlib licence (based on the PSF licence) |
| openpyxl | 3.1.5 | Reading the Excel files | MIT |
| CodeCarbon | 3.3.2 | Energy and CO₂ estimate of each backtest run | MIT |
| chronos-forecasting | 2.3.2 | Chronos-2 (optional, `uv sync --extra pretrained`) | Apache-2.0 |
| PyTorch | 2.15.0 | Runs Chronos (optional) | BSD-3-Clause |
| transformers | 5.23.0 | Loads Chronos (optional) | Apache-2.0 |
| ruff, pytest | dev only | Linting and tests | MIT |

## Data sources
The terms below come from the source catalogs Schneider provided in `data/raw/csv/`. All data stays
on our machines under the challenge NDA and is never committed.

| Source | Series | Terms |
|---|---|---|
| IMF commodity prices, via FRED | S01–S05, E01–E03, E05–E08, E22 | Free |
| Eurostat | S07–S11, E13–E16, E20, E21 | Free, CC BY 4.0 |
| US Bureau of Labor Statistics, via FRED | S12, S13, E17, E18 | Free |
| European Central Bank | S06, E23, E24 | Free |
| Ember | E09–E11 | Free, CC BY 4.0 |
| Bank of Japan and JEPX | E04, E12, E19 | Free, with the source cited |
| MEPS and CRU steel prices (steel workbook) | L01–L03 and the MEPS coils | Licensed, shared by Schneider under NDA |
| LME monthly prices | `LME_*` columns | Shared by Schneider |
| Epoxy prices, BOM files, RMU price benchmark (synthetic) | `EPX_*`, BOM, RMU prices | Shared by Schneider under NDA |
| Supplier balance sheets (PitchBook exports) | Procurement levers | Licensed, shared under NDA; supplier names never appear in outputs |

## AI tools
| Tool | What we used it for | Who | Terms |
|---|---|---|---|
| Claude, including Claude Code (Anthropic) | Helping write and review code, tests and docs, and summarise research. Every result was checked with tests and backtests | All four of us | Anthropic terms of service |
| Granola | Taking and summarising our team meeting notes; not used for any forecast or analysis | Team | Granola terms of service |

Chronos-2 is a forecasting model, not an assistant, so it is listed with the models above.

## Runtime and CO₂
One full rebuild (`data`, `p2_selection`, `p3_selection`, `pricing`, `submit`) on a laptop CPU
(Apple M4). CodeCarbon estimates the energy each backtest uses from the processor's power draw and
how busy it is, then converts it to CO₂ with the average carbon intensity of the French grid (set
in the code, so the estimate is the same wherever it runs). It works offline and logs the result in
`outputs/backtest/*_run.json`. Only the backtests are tracked; the other steps take about 6 seconds.

| Step | Runtime | CO₂ (kg) |
|---|---|---|
| Data pipeline | 1 s | not tracked |
| Steel selection, with its strict backtest (9 s of it) | 22 s | 1.9 × 10⁻⁶ |
| Other-material selection, with its strict and main backtests (13 s of it) | 20 s | 2.4 × 10⁻⁶ |
| Pricing, with the index backtest and 2021 replay | 4 s | not tracked |
| Submission | 1 s | not tracked |
| Total | 48 s | 4.3 × 10⁻⁶ (about 0.004 g) |

Measured with Chronos already installed. The first run also downloads the Chronos-2
weights from Hugging Face once; that is a download only, no data is sent.

This leaves out the exploration runs behind the dropped models; we measured about 2 to 6 × 10⁻⁵ kg
per backtest run. Nothing ran on a GPU or in the cloud.
