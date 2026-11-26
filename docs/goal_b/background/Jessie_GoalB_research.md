# Jessie Goal B research

Neutral inputs for the Goal B proposals: what Schneider asked, and what the team's data and Goal A
work already show. **No recommendations here**: the proposal is in
[`Jessie_GoalB_proposal.md`](Jessie_GoalB_proposal.md). Sources: Schneider's slides
(`X_HEC_2026_Pres.pdf`, page numbers as printed), [`eda_findings.md`](../../eda_findings.md) (§),
[`pricing.md`](../../pricing.md), [`forecasting_other.md`](../../forecasting_other.md), the 18/11 Q&A.

## 1. The question (slides p14, p17)
> In markets with **no SF6 regulation (APAC, Middle East, Americas)**, what strategy wins the
> voluntary SF6-free switch? Without a mandate, the switch must be commercial: leverage **RM price
> convergence, data center ESG requirements and TCO**, and show how RM prediction supports the
> argument.

Expected outputs (p15): target markets & segments · value proposition · commercial & pricing
approach · adoption levers · roadmap & win conditions (= B1–B5, methodology §5). Forecast accuracy
and strategy quality count **equally** (p16).

**Products:** the question names **SM6 → SM AirSeT** (switchgear modules); our data (BOM, prices)
covers **RM6 → RM AirSeT** (ring main units, same SF6 vs SF6-free choice). Treat the RM figures as
the proxy and say so.

## 2. What Schneider says about the context (slides)
| Fact | Slide |
|---|---|
| SwitchGear division ≈ $2B, target $4B in 2–3 years | project overview |
| Group revenue €40.2bn (FY 2025), 160k employees, > 100 countries | p7 |
| Global data center market $584B (2026), +25.7 % a year, $1.32T projected by 2030; 90 %+ of new capacity pre-leased before delivery | p13 |
| Data center capacity demand ×4 between 2023 and 2030 (McKinsey) | p4 |
| "Every new data center needs medium-voltage switchgear to connect to the grid" | p13 |
| ETO contracts lock prices for 3 / 6 / 9 months: cost moves after signing hit margin | p13–14 |
| RM AirSeT (solid insulation, vacuum interruption) "carries a higher cost structure and thinner margin" | p14 |
| Build the case "despite higher upfront cost": TCO, customer ESG and decarbonisation goals, avoided SF6 lifecycle risks, RM outlook | p14 |
| Schneider: #1 World's Most Sustainable Company 2024–26 (Corporate Knights), CDP A-list 15 years, EcoVadis top 1 % | p8 |
| SF6 is phased out in Europe by regulation; outside Europe no regulation pushes customers away from SF6 | project overview |

Q&A 18/11: the **US and China** are Schneider's major markets; the **UK** is a likely next step;
no global country-by-country study is expected (pick a few markets and justify them).

## 3. Raw-material cost: AirSeT vs RM6 (our data, v1 BOM of 20/11)
| | RM AirSeT | RM6 |
|---|---|---|
| Priced raw-material cost per unit (Sep 2026) | **€975** | **€900** |
| Share of the 2026 Schneider P50 price (€12,233) | 8.0 % | 7.4 % |
| Cost weights | copper 37 %, carbon steel 29 %, stainless 21 %, plastics 11 % | copper 54 %, stainless 17 %, carbon steel 13 %, plastics 12 % |
| Copper mass | 28.5 kg | 38.8 kg |

- **On priced raw material, AirSeT costs more than RM6:** +€122 (Jan 2021), +€264 peak (Apr 2022),
  **+€75 today**. The copper rally narrowed the gap (RM6 has more copper) but did not reverse it.
- **Gap outlook** (P4 joint simulation of P2 / P3 forecasts), AirSeT − RM6, P10 / P50 / P90:
  +6 months €67 / €86 / €111; +9 months €58 / €75 / €118. AirSeT stays dearer in 9 draws out of 10.
- **Version warning:** older team docs (12 Nov BOM, methodology §5, overview) say "RM6 is ≈ €98
  dearer". That BOM had no copper in AirSeT; Schneider's latest BOM (v1, the reference) does.
- The +€75 gap is ≈ 0.6 % of the unit price: raw material is a small share of price; the rest is
  processing, bought parts, engineering, channel and margin (EDA §11).

## 4. Raw-material outlook and risk per product (P2 / P3 forecasts, P4)
Cost index, 100 = Sep 2026, P10 / P50 / P90:

| Product | +3 | +6 | +9 |
|---|---|---|---|
| AirSeT | 95.0 / 100.0 / 109.0 | 93.7 / 101.9 / 118.5 | 91.9 / 100.7 / 126.3 |
| RM6 | 93.5 / 99.7 / 108.0 | 91.3 / 101.0 / 116.5 | 91.7 / 100.3 / 124.5 |

| | AirSeT | RM6 |
|---|---|---|
| Margin at risk at P90, +3 / +6 / +9 (margin 20 % assumed) | €88 / €180 / €256 | €72 / €148 / €220 |
| Risk buffer, share of price, +3 / +6 / +9 | 0.7 / 1.3 / 2.0 % | 0.6 / 1.1 / 1.8 % |
| Quotation validity (P4 rule) | 6 months | 9 months |

- Middle case: costs about flat (copper is a random walk; steel P50 up ≈ 4–5 % at +6).
- Copper is at a record in 2026 (+45 % year on year, ≈ 2.4× 2019; EDA §5).
- 2021 replay (P4): a fixed price lost up to 28 % (AirSeT) / 22 % (RM6) of margin on 2021–22
  purchases; buffers cannot absorb such a shock without losing tenders; indexation can.

## 5. Competitors and prices (EDA §9, §11)
RMU price benchmark (synthetic, EUR ex-VAT, yearly P50, no configuration split):

| Brand | P50 2026 | vs Schneider | Change 2026 | Avg yearly change 2018–25 |
|---|---|---|---|---|
| SwitchGear Company | €9,154 | −25.2 % | +32.3 % | +3.0 % |
| Ormazabal | €9,652 | −21.1 % | +35.8 % | +2.8 % |
| **Eaton (SF6-free)** | €11,560 | −5.5 % | **+8.4 %** | +0.9 % |
| **Schneider Electric** | €12,233 | — | +40.0 % | +2.4 % |
| ABB | €12,273 | +0.3 % | +39.8 % | +2.6 % |
| Siemens | €13,762 | +12.5 % | +33.4 % | +2.6 % |

- Eaton (Xiria) is the **only SF6-free** product in the benchmark; **SM / RM AirSeT is not in it**.
- Eaton's premium over the SF6 brands' average: **+46 % (2017) → +1 % (2026)**; it was the most
  expensive brand until 2025 and is now cheaper than Schneider. The cause is not in the data.
- 2026 is a step change for every SF6 brand (+32 to +40 %); Eaton +8 %.
- Schneider prices most consistently (narrowest P10–P90 band, 28 % of P50).
- The RMU file has one "Schneider" price: **no separate SM6 vs AirSeT selling price** in our data.
- Teardown benchmark: material ≈ 80 % of competitor should-cost; one real price (Siemens 8DJH
  €15,530, ≈ 4.7× its should-cost of €3,307).

## 6. Price vs cost history (EDA §11)
| Year | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026* |
|---|---|---|---|---|---|---|---|---|---|
| RM6 material cost | +0.6 % | −5.6 % | −3.5 % | +58.2 % | +8.7 % | −16.6 % | +0.2 % | −1.6 % | +20.6 % |
| Schneider price | +0.9 % | +0.3 % | −0.8 % | +6.7 % | +7.3 % | +1.2 % | +3.8 % | +0.1 % | +40.0 % |

\* Jan–Sep 2026. 2021: cost absorbed; 2026: more than passed on.

## 7. Supply side (P4 procurement levers; suppliers anonymised)
- 9 suppliers: 2 strong, 4 to watch, 3 fragile (EBITDA margin, current ratio, interest coverage).
  No link from supplier to part, so not tied to RM6 or AirSeT.
- Schneider already buys steel parts on public indices (CR, HDG coil; 1-month lead time); the
  AirSeT plant is in Hungary (German indices), the RM6 plant in France.

## 8. What our data cannot answer (desk research needed)
| Topic | Needed for |
|---|---|
| SF6 rules outside the EU (US federal / California, China, UK, Middle East, APAC) and their timing | B1, B3, B5 |
| SF6 lifecycle costs: handling, leak checks, reporting, end-of-life recovery; carbon price of a leak (SF6 GWP ≈ 23,500 × CO₂) | B3 (TCO) |
| Customer ESG demand: data center operators' Scope 1 / 2 / 3 targets, procurement criteria | B1, B3 |
| Market sizes and growth by country / segment (data centers, utilities, industry, buildings) | B1 |
| Competitors' SF6-free offers beyond Eaton (ABB, Siemens, others) and their prices | B2 |
| SM6 vs SM AirSeT selling prices, Schneider's margin and cost base | B4 (asked at the 23/11 Q&A) |

## 9. Pending
- **23/11 Q&A answers** (margin, cost base, scored proxy, RMU price configuration): add here when
  recorded.

## 10. Desk research (24/11)
Public sources, mostly regulators, company results and vendor pages; vendor claims are marked.
Check dates and wording before quoting them in the deck.

### Regulation
| Fact | Source |
|---|---|
| EU F-gas Regulation (EU) 2024/573: no SF6 in new MV switchgear ≤ 24 kV from 1 Jan 2026; 24–52 kV from 2030; HV 2028 / 2032 | [Umweltbundesamt factsheet](https://www.umweltbundesamt.de/system/files/document/Factsheet_Schaltanlagen.pdf), [Syke](https://www.syke.fi/en/about-us/news/transition-sf6-free-electrical-switchgear-will-begin-2026), [Schneider blog](https://blog.se.com/datacenter/2025/07/18/is-your-data-center-ready-for-the-ban-on-sf6-mv-switchgear-in-the-eu/) |
| California (CARB) amended its SF6 rule in 2021 with a phase-out schedule for new SF6 gas-insulated equipment by voltage and rating (proposal: 2025 for the lowest classes, up to 2031); exemptions possible; lead-time challenges reported in 2026 | [CARB](https://ww2.arb.ca.gov/our-work/programs/elec-tandd/about), [2020 slides](https://ww2.arb.ca.gov/sites/default/files/2020-07/sf6-gis-reg-slides-07132020.pdf), [17 CCR § 95352](https://regulations.justia.com/states/california/title-17/division-3/chapter-1/subchapter-10/article-4/subarticle-3-1/section-95352), [CARB board 2026](https://ww2.arb.ca.gov/sites/default/files/barcu/board/books/2026/022626/26-1-1bis.pdf) |
| UK: no ban yet; Defra's F-gas review considers SF6; gov.uk report on pathways to SF6-free distribution networks | [gov.uk pathways](https://www.gov.uk/government/publications/pathways-to-sf6-free-distribution-networks), [Parliament answer](https://parallelparliament.co.uk/question/46922/sulphur-hexafluoride) |
| China: no MV rule found; State Grid ordered SF6-free 420 kV (2024) and 550 kV (connected 2026) equipment, linked to carbon neutrality 2060 (vendor source) | [Hitachi Energy](https://www.hitachienergy.com/news-and-events/features/2026/07/leading-the-charge-state-grid-corporation-of-china-decarbonization-journey), [420 kV](https://www.hitachienergy.com/ca/en/news-and-events/customer-stories/the-big-switch-china-powers-its-very-first-420-kv-sf6-free-switchgear) |
| Singapore carbon tax covers SF6: S$45 / t CO₂e in 2026, S$50–80 targeted by 2030, for facilities emitting ≥ 25,000 t CO₂e a year | [NCCS](https://www.nccs.gov.sg/singapores-climate-action/mitigation-efforts/carbontax/), [NEA](https://www.nea.gov.sg/OUR-SERVICES/CLIMATE-CHANGE-ENERGY-EFFICIENCY/CLIMATE-CHANGE/CARBON-TAX) |
| CSRD: in-scope companies (incl. non-EU groups via EU entities) report material Scope 3; suppliers are not obliged to report but receive data requests | [Anthesis](https://www.anthesisgroup.com/insights/scope-3-reporting-csrd/), [Avetta](https://www.avetta.com/blog/eu-corporate-sustainability-reporting-directive-csrd-why-many-companies-are-building-now-before-they-are-fully-in-scope), [Linklaters](https://sustainablefutures.linklaters.com/post/102n2xc/eu-corporate-sustainability-reporting-directive-impact-of-csrd-on-non-eu-companies) |

### SF6 in equipment
| Fact | Source |
|---|---|
| Most MV switchgear holds < 5 kg SF6; some Schneider RMUs ≈ 0.6–0.7 kg (on the rating plate) | [gov.uk guidance](https://www.gov.uk/guidance/how-to-operate-or-service-high-voltage-switchgear-containing-sf6), [Schneider FAQ](https://www.se.com/uk/en/faqs/FA29745) |
| Sealed units leak < 0.1 % a year; operating life > 30 years (ABB) | [ABB SafeRing & SafePlus](https://www.abb.com/global/en/areas/electrification/medium-voltage/switchgear/gas-insulated/safering-safeplus) |
| SF6 GWP: 23,500 (IPCC AR5) or 24,300 (AR6); listed as Scope 1 fugitive gas in emission databases | [Climatiq](https://www.climatiq.io/data/emission-factor/d507cfcf-d208-4e39-8b03-43664c8dece2), [Schneider](https://blog.se.com/infrastructure-and-grid/smart-grid/2021/01/12/why-providing-alternatives-to-sf6-and-other-greenhouse-gases-is-important-for-carbon-reduction-initiatives/) |
| Worked example: 2 kg SF6 ≈ 48 t CO₂e stored; at 0.1 % a year ≈ 50 kg CO₂e leaked | Computed from the two lines above |

### Markets (data centers)
| Fact | Source |
|---|---|
| India: 2.2 GW (2025) → 12 GW (2030), ≈ +40 % a year | [DataCenterNews](https://datacenternews.asia/story/india-s-data-centre-capacity-set-to-hit-12-gw-by-2030) |
| Southeast Asia: pipeline ≈ 4× running capacity; Malaysia > 6 GW planned (Johor); APAC pipeline 19.4 GW (2025) | [TNW](https://thenextweb.com/news/southeast-asia-data-centre-investment-malaysia-johor-2031) |
| Middle East: IT capacity 1.3 → 6.3 GW by 2030 (ABI); third-party capacity ≈ 0.5 → 1.5 GW (narrower measure) | [ABI Research](https://abiresearch.com/blog/data-center-capacity-growth-forecast), [Computer Weekly](https://www.computerweekly.com/feature/Middle-East-datacentre-capacity-set-to-triple-by-2030) |
| Global: +97 GW 2025–2030, up to 200 GW by 2030 (JLL) | [JLL](https://www.jll.com/en-au/insights/data-center-outlook.html) |
| Morocco: Dakhla 500 MW green data center (studies launched Apr 2026); Tetouan 386 MW (developer with no track record) and other 500 MW plans; capacity largely aimed at European workloads; analysts expect delays; Dakhla is in Western Sahara | [Medias24](https://medias24.com/2026/04/17/dakhla-500-mw-green-data-center-megaproject-launched-to-bolster-moroccos-digital-sovereignty-1661807/), [DCD](https://datacenterdynamics.com/en/news/us-ai-startup-plans-massive-386mw-data-center-in-morocco), [Le360](https://en.le360.ma/economy/moroccos-data-center-capacity-set-to-surge-as-ai-and-cloud-investment-accelerates-report-says_MYVV3TMHRJHN7MNV3WDYZSZERQ/), [TelQuel](https://telquel.ma/2026/05/05/moroccos-risky-bet-on-ai-mega-data-centers_1986659), [WSRW](https://wsrw.org/en/news/morocco-plans-massive-ai-center-in-occupied-western-sahara) |
| Hyperscaler targets: Microsoft carbon negative 2030; Meta net zero across value chain 2030; Google 24/7 carbon-free energy 2030; Amazon net zero 2040; voluntary, not binding | [S&P Global](https://www.spglobal.com/energy/en/news-research/latest-news/electric-power/092326-path-to-net-zero-ai-build-out-tests-tech-sectors-emissions-trajectory), [NewClimate](https://newclimate.org/sites/default/files/2025-06/newclimate-publication-ccrm2025-tech-Jun25.pdf) |

### Competitors
| Fact | Source |
|---|---|
| Eaton: Xiria air-insulated SF6-free since 2002, > 150,000 panels sold (vendor); revenue $27.4B in 2025; Electrical Americas data center orders ≈ +200 % in Q4 2025 | [Eaton FAQ](https://www.eaton.com/no/no-no/markets/utilities/tomorrowsgrid/air-insulated-switchgear-sf6-free-eaton/knowledge-center/faq-guide-to-sf6-free.html), [Eaton Q4 2025](https://www.nasdaq.com/press-release/eaton-reports-record-fourth-quarter-2025-results-accelerating-orders-and-continued) |
| ABB: SafeRing Air / SafePlus Air, dry air + vacuum, same footprint and interface as SF6 models, in use since 2020 (vendor) | [ABB SF6-free](https://www.abb.com/global/en/areas/electrification/medium-voltage/switchgear/sf6-free) |
| Siemens: SF6-free MV offer not verified in this search | — |

### Schneider AirSeT (vendor claims)
| Fact | Source |
|---|---|
| Pure air insulation + shunt vacuum interruption; up to 40-year life; up to 40 % less maintenance with EcoCare; digital monitoring (thermal, environmental, remote app, partial discharge with EcoCare, breaker wear) | [SM AirSeT](https://www.se.com/my/en/product-range/21830291-sm-airset/), [catalogue](https://download.schneider-electric.com/doc/NRJCAT21009EN/NRJCAT21009EN%20(web).pdf) |
