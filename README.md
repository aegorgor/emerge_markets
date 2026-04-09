# SYDE 532 Project — Electricity Market Policy Analysis

## Project Overview

This repository contains two complementary analyses of electricity market policy using
AMIRIS, an agent-based wholesale electricity market simulator calibrated to Germany 2019.

---

## Part 1: Carbon Tax Regressivity Analysis (Egor Gorlov)

Investigates whether carbon taxes on electricity disproportionately burden low-income
households compared to high-income households.

### Methodology
1. **Data Collection**: Real US residential load profiles from NREL ResStock are
   stratified by household income to create income-specific demand curves.
2. **Market Simulation**: These demand curves are fed into AMIRIS across carbon tax
   levels ranging from 0–100 EUR/t CO₂.
3. **Cost Analysis**: Per-household electricity costs are calculated at each tax level
   and expressed as a percentage of household income.

### Main Findings
The analysis reveals a consistent regressivity ratio of approximately 12× across all
carbon tax levels. At a €0 carbon price, low-income households spend 2.79% of their
$15,000 annual income on electricity versus 0.23% for high-income households earning
$200,000. This gap widens in absolute terms as carbon taxes increase, but the
proportional disparity remains stable because demand is modeled as inelastic.

### Limitations
Costs reflect wholesale market prices only and exclude retail markups. They serve as
a stylised proxy for comparing relative burden between income groups.

### Scripts
- `carbon_tax_sweep.py` — runs AMIRIS across CO₂ price levels
- `analyze_carbon_sweep.py` — tabular analysis of results
- `plot_income_comparison.py` — generates 8 comparison visualizations

---

## Part 2: RES Support Scheme Matrix Analysis (Juan Segovia)

Evaluates four renewable energy support schemes across three CO₂ price levels using
a fully factorial 4×3 experiment design (12 scenarios total).

### Support Schemes
- **Baseline (MPVAR + FIT)**: Germany 2019 policy mix
- **No Support**: zero subsidy counterfactual
- **MPVAR Reduced**: 25% reduction in market premium reference prices
- **FIT Only**: feed-in tariff at full LCOE rate for all VRE

### CO₂ Price Levels
- **Low**: 0 EUR/t (pre-ETS collapse counterfactual)
- **Baseline**: ~24 EUR/t (actual 2019 EEX data)
- **High**: 65 EUR/t (~2022 EU ETS levels)

### Main Findings
- Market prices are scheme-invariant; only CO₂ price shifts merit order
- MPVAR support cost falls 42% as CO₂ rises from 0 → 65 EUR/t; FIT is CO₂-invariant
- FIT fiscal cost premium over MPVAR is +15% at low CO₂, +28% at baseline, +61% at high CO₂
- CO₂ pass-through rate is ~0.58–0.62 EUR/MWH per EUR/t, consistent with hard coal as marginal plant

### Scripts
- `matrix_analysis/setup_matrix_scenarios.py` — generates all 12 scenario configs
- `matrix_analysis/comprehensive_analysis.py` — full 4×3 analysis, outputs CSV
- `matrix_analysis/generate_plots.py` — produces 8 figures

### Reproducing the Analysis
1. Install dependencies: `pip install amirispy pandas matplotlib`
2. Download the AMIRIS JAR and place it in `matrix_analysis/`
3. Add large timeseries profiles to `matrix_analysis/Germany2019/timeseries/`
   (solar, wind, load CSVs — gitignored due to size)
4. Run `setup_matrix_scenarios.py` to generate scenario configs
5. Run each scenario with `amiris run --scenario <config>/scenario.yaml --output <name>`
6. Run `comprehensive_analysis.py` then `generate_plots.py`

---

## Dependencies
- Python 3.10+
- `amirispy` 3.3.2
- Java 11+ (for AMIRIS)
- `pandas`, `matplotlib`, `numpy`

