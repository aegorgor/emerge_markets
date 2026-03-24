# SYDE 532 Project — Carbon Tax Regressivity Analysis

Investigates whether a carbon tax on electricity is regressive: does it impose
a disproportionately larger burden (as a share of income) on low-income
households than on high-income households?

**Approach:**
1. Pull real US residential load profiles from NREL ResStock, stratified by
   household income, to build income-specific demand curves.
2. Feed those demand curves into AMIRIS (a German wholesale electricity market
   simulator) across a range of carbon tax levels (0–100 EUR/t CO₂).
3. Compute per-household electricity costs at each tax level and express them
   as a fraction of household income.

---

## Repository Structure

```
SYDE532Project/
├── Demand Data/
│   ├── download_data.py                   # Step 1 — downloads demand profiles
│   ├── demand_low_income.csv              # Output: per-household hourly load (MWh), low income
│   ├── demand_high_income.csv             # Output: per-household hourly load (MWh), high income
│   └── baseline_metadata_and_annual_results.csv  # NREL ResStock metadata (income labels, states)
│
├── Germany2019Alt/                        # AMIRIS scenario (Germany 2019 wholesale market)
│   ├── scenario.yaml                      # Top-level scenario definition
│   ├── schema.yaml                        # AMIRIS schema
│   ├── amiris-core_4.0.0-jar-with-dependencies.jar  # AMIRIS engine
│   ├── agents/                            # Agent definitions (demand, conventionals, renewables…)
│   ├── contracts/                         # Contract definitions between agents
│   ├── timeseries/                        # Fuel prices, generation profiles, CO₂ price series
│   │   └── demand/
│   │       ├── demand_low_income.csv      # AMIRIS-format demand for low-income trader (agent 101)
│   │       └── demand_high_income.csv     # AMIRIS-format demand for high-income trader (agent 102)
│   ├── carbon_sweep_summary.csv           # Step 2 output: market prices + MWh + EUR per agent
│   ├── README.md                          # AMIRIS scenario documentation
│   └── LICENCE.md
│
├── carbon_tax_sweep.py                    # Step 2 — runs AMIRIS at each CO₂ level, writes summary
├── analyze_carbon_sweep.py                # Optional: tabular analysis of carbon_sweep_summary.csv
├── plot_income_comparison.py              # Step 3 — generates all comparison plots
│
└── plots/
    └── income_comparison/
        ├── 01_daily_profile.png           # Annual avg hourly load, low vs high income
        ├── 02_demand_difference.png       # Hour-by-hour demand gap and ratio
        ├── 03_seasonal_profiles.png       # Seasonal daily profiles (all 4 seasons)
        ├── 04_pct_income.png              # Electricity cost as % of income vs CO₂ price  ← key
        ├── 05_absolute_cost_and_gap.png   # Absolute USD cost and dollar gap per household
        ├── 06_regressivity.png            # Regressivity ratio (low burden % / high burden %)
        ├── 07_dual_story.png              # Log-scale burden + flat ratio vs growing gap
        └── 08_marginal_cost.png           # Additional burden per 20 EUR/t CO₂ step
```

---

## How to Reproduce

### Prerequisites
```
pip install boto3 pandas numpy matplotlib pyarrow
```
AMIRIS must be installed and on your PATH (`amiris --version` should work).

### Step 1 — Download demand profiles (requires internet, ~30 min)
```
cd "Demand Data"
python download_data.py
```
Pulls 100 low-income and 100 high-income ResStock buildings from AWS S3
(NREL OEDI, public, no credentials needed). Samples are state-balanced across
VA, TX, CA, NY, FL to remove geographic confounding. Outputs
`demand_low_income.csv` and `demand_high_income.csv` (per-household averages,
MWh/hr, hourly for 2018).

Income bands sampled:
- **Low income:** `<$10k`, `$10–15k`, `$15–20k`
- **High income:** `$160–180k`, `$180–200k`, `$200k+`

### Step 2 — Run AMIRIS carbon sweep
```
python carbon_tax_sweep.py --levels 0 20 40 60 80 100
```
For each CO₂ price level (EUR/tonne), overwrites `Germany2019Alt/timeseries/co2_price.csv`
with a flat series at that level, runs AMIRIS, then reads `DayAheadMarketSingleZone.csv`
and `DemandTrader.csv` to record MWh consumed and EUR spent by each demand agent.
Results are written to `Germany2019Alt/carbon_sweep_summary.csv`.

### Step 3 — Generate plots
```
python plot_income_comparison.py
```
Produces 8 plots in `plots/income_comparison/`. Per-household costs are derived
as `market_avg_price × per_household_annual_MWh`, where annual MWh comes from
the `Demand Data/` CSVs (the canonical per-household series).

---

## Key Findings

| CO₂ (EUR/t) | Low-income cost | % of $15k income | High-income cost | % of $200k income | Regressivity |
|---|---|---|---|---|---|
| 0   | $419/yr  | 2.79% | $467/yr  | 0.23% | **12×** |
| 20  | $558/yr  | 3.72% | $622/yr  | 0.31% | **12×** |
| 40  | $702/yr  | 4.68% | $783/yr  | 0.39% | **12×** |
| 60  | $851/yr  | 5.67% | $949/yr  | 0.47% | **12×** |
| 80  | $1,006/yr| 6.71% | $1,123/yr| 0.56% | **12×** |
| 100 | $1,167/yr| 7.78% | $1,302/yr| 0.65% | **12×** |

The regressivity ratio is **flat at ~12×** across all carbon tax levels because
demand is inelastic in the model (neither group reduces consumption in response
to price). This means every $20/t increase adds roughly $140 to the low-income
bill — which is ~0.93% of their annual income — versus only 0.08% for high
earners. The absolute dollar gap grows, but the proportional disparity is
locked in by the income ratio, not the carbon price level.

> **Note on costs:** AMIRIS models the German 2019 *wholesale* electricity
> market. Figures above reflect the market-clearing cost component only and do
> not include retail markups (distribution, taxes). They serve as a stylised
> proxy for comparing the relative burden between income groups under a carbon
> price, not as absolute US electricity bill estimates.

---

## Income Assumptions

| Group | Representative income | Source |
|---|---|---|
| Low income  | $15,000/yr | Midpoint of sampled bands (<$10k–$20k) |
| High income | $200,000/yr | Representative of $160k–$200k+ bands |

EUR → USD conversion: 1 EUR = 1.12 USD (2018/2019 average rate).

---

## Notes

- `Demand Data/` contains a nested `.git` folder from an earlier standalone
  repo — it can be safely ignored.
- AMIRIS run output folders (`run_co2_*/`) are not committed; re-run Step 2
  to regenerate them. Only `carbon_sweep_summary.csv` is kept as the
  authoritative result.
