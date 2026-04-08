"""
comprehensive_analysis.py
─────────────────────────
Full analysis across all 12 policy scenarios (4x3 matrix):
  4 support schemes x 3 CO2 price levels

Support schemes:
  - Baseline (MPVAR+FIT): germany_baseline, low_co2, high_co2
  - No Support:           no_support, no_support_low_co2, no_support_high_co2
  - MPVAR Reduced (75%):  mpvar_reduced, mpvar_reduced_low_co2, mpvar_reduced_high_co2
  - FIT Only:             fit_scenario, fit_only_low_co2, fit_only_high_co2

CO2 price levels:
  - Low (0 EUR/t):       low_co2, no_support_low_co2, mpvar_reduced_low_co2, fit_only_low_co2
  - Baseline (~24 EUR/t): germany_baseline, no_support, mpvar_reduced, fit_scenario
  - High (65 EUR/t):     high_co2, no_support_high_co2, mpvar_reduced_high_co2, fit_only_high_co2

Sections:
  1. Market prices
  2. Generation mix by fuel type + RES share + curtailment
  3. Conventional operator profitability
  4. RES revenue & support (aggregated across all traders)
  5. Total support expenditure (system cost)
  6. Per-technology LCOE coverage ratio (market revenue vs LCOE)
  7. Storage (GenericFlexibilityTrader) analysis
"""

import pandas as pd
import numpy as np
import os

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Full 4x3 matrix: 12 runs
RUNS = [
    "germany_baseline",
    "low_co2",
    "high_co2",
    "no_support",
    "no_support_low_co2",
    "no_support_high_co2",
    "mpvar_reduced",
    "mpvar_reduced_low_co2",
    "mpvar_reduced_high_co2",
    "fit_scenario",
    "fit_only_low_co2",
    "fit_only_high_co2",
]

# Metadata for grouping and labelling
RUN_META = {
    "germany_baseline":       {"scheme": "Baseline (MPVAR+FIT)", "co2": "Baseline"},
    "low_co2":                {"scheme": "Baseline (MPVAR+FIT)", "co2": "Low"},
    "high_co2":               {"scheme": "Baseline (MPVAR+FIT)", "co2": "High"},
    "no_support":             {"scheme": "No Support",           "co2": "Baseline"},
    "no_support_low_co2":     {"scheme": "No Support",           "co2": "Low"},
    "no_support_high_co2":    {"scheme": "No Support",           "co2": "High"},
    "mpvar_reduced":          {"scheme": "MPVAR Reduced",        "co2": "Baseline"},
    "mpvar_reduced_low_co2":  {"scheme": "MPVAR Reduced",        "co2": "Low"},
    "mpvar_reduced_high_co2": {"scheme": "MPVAR Reduced",        "co2": "High"},
    "fit_scenario":           {"scheme": "FIT Only",             "co2": "Baseline"},
    "fit_only_low_co2":       {"scheme": "FIT Only",             "co2": "Low"},
    "fit_only_high_co2":      {"scheme": "FIT Only",             "co2": "High"},
}
SEP = ";"

# ── Agent ID → fuel/technology mappings ──────────────────────────────────────

CONV_AGENT_FUEL = {
    500: "Nuclear",
    501: "Lignite",
    502: "HardCoal",
    503: "Gas_CCGT",
    504: "Gas_OCGT",
    505: "Oil",
}

VRE_AGENT_TECH = {
    10: "PV",       20: "WindOn",    50: "RunOfRiver",
    52: "Biogas",   53: "OtherRES",
    60: "PV",       61: "PV",        62: "PV",       63: "PV",       64: "PV",
    70: "WindOn",   71: "WindOn",    72: "WindOn",   73: "WindOn",   74: "WindOn",
    80: "WindOff",  81: "WindOff",   82: "WindOff",  83: "WindOff",
}

VRE_AGENT_SUPPORT = {
    10: "FIT",   20: "FIT",   50: "FIT",
    52: "None",  53: "None",
    60: "MPVAR", 61: "MPVAR", 62: "MPVAR", 63: "MPVAR", 64: "MPVAR",
    70: "MPVAR", 71: "MPVAR", 72: "MPVAR", 73: "MPVAR", 74: "MPVAR",
    80: "MPVAR", 81: "MPVAR", 82: "MPVAR", 83: "MPVAR",
}

# LCOE benchmarks per VRE agent (EUR/MWH) — from Germany2019 scenario YAML
AGENT_LCOE = {
    10: 120.0,  20: 85.0,   50: 100.0,
    60: 97.21,  61: 202.91, 62: 286.67, 63: 340.07, 64: 440.05,
    70: 70.58,  71: 79.65,  72: 87.24,  73: 94.17,  74: 100.26,
    80: 154.0,  81: 174.5,  82: 184.0,  83: 194.0,
}

RES_TECH = {"PV", "WindOn", "WindOff", "RunOfRiver", "Biogas", "OtherRES"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def load(run, filename):
    return pd.read_csv(os.path.join(PROJECT_DIR, run, filename), sep=SEP)


def load_if_exists(run, filename):
    path = os.path.join(PROJECT_DIR, run, filename)
    if not os.path.exists(path):
        return None
    return pd.read_csv(path, sep=SEP)


def section_header(title):
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: Market Prices
# ─────────────────────────────────────────────────────────────────────────────
section_header("SECTION 1: MARKET PRICES  (DayAheadMarketSingleZone.csv)")

price_rows = []
market_avg = {}  # keyed by run — reused in Section 6
for run in RUNS:
    df = load(run, "DayAheadMarketSingleZone.csv")
    p = df["ElectricityPriceInEURperMWH"]
    e = df["AwardedEnergyInMWH"]
    n = len(p)
    wavg = (p * e).sum() / e.sum() if e.sum() > 0 else np.nan
    market_avg[run] = wavg
    price_rows.append({
        "Run":                run,
        "Mean (EUR/MWH)":     round(p.mean(), 4),
        "Wtd Avg (EUR/MWH)":  round(wavg, 4),
        "% Hours = 0":        round((p == 0.0).sum() / n * 100, 2),
        "% Hours < 0":        round((p < 0.0).sum()  / n * 100, 2),
        "% Hours > 100":      round((p > 100).sum()  / n * 100, 2),
        "Max (EUR/MWH)":      round(p.max(), 2),
        "Std Dev":            round(p.std(), 4),
        "N Hours":            n,
    })

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)
price_df = pd.DataFrame(price_rows)
print(price_df.to_string(index=False))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: Generation Mix by Fuel Type + RES Share
# ─────────────────────────────────────────────────────────────────────────────
section_header("SECTION 2: GENERATION MIX BY FUEL TYPE  (TWh, % of total)")

TECHS = ["PV", "WindOn", "WindOff", "RunOfRiver", "Biogas", "OtherRES",
         "Nuclear", "Lignite", "HardCoal", "Gas_CCGT", "Gas_OCGT", "Oil"]

gen_rows = []
for run in RUNS:
    row = {"Run": run}

    # VRE operators (includes Biogas agent 52 via Biogas.csv)
    vre = load(run, "VariableRenewableOperator.csv")
    bio = load(run, "Biogas.csv")
    conv = load(run, "ConventionalPlantOperator.csv")

    # Group VRE by tech
    vre_gen = {}
    for agent_id, group in vre.groupby("AgentId"):
        tech = VRE_AGENT_TECH.get(agent_id, "Unknown")
        vre_gen[tech] = vre_gen.get(tech, 0.0) + group["AwardedEnergyInMWH"].sum()

    # Biogas
    vre_gen["Biogas"] = vre_gen.get("Biogas", 0.0) + bio["AwardedEnergyInMWH"].sum()

    # Conventional by fuel
    conv_gen = {}
    for agent_id, group in conv.groupby("AgentId"):
        fuel = CONV_AGENT_FUEL.get(agent_id, "Unknown")
        conv_gen[fuel] = conv_gen.get(fuel, 0.0) + group["AwardedEnergyInMWH"].sum()

    total_mwh = sum(vre_gen.values()) + sum(conv_gen.values())
    res_mwh   = sum(v for tech, v in vre_gen.items() if tech in RES_TECH)

    for tech in TECHS:
        mwh = vre_gen.get(tech, conv_gen.get(tech, 0.0))
        row[f"{tech} TWh"] = round(mwh / 1e6, 3)

    row["Total TWh"]    = round(total_mwh / 1e6, 3)
    row["RES Share %"]  = round(res_mwh / total_mwh * 100, 2) if total_mwh else 0.0
    row["Conv Share %"] = round((total_mwh - res_mwh) / total_mwh * 100, 2) if total_mwh else 0.0

    # VRE curtailment
    vre_offered = vre["OfferedEnergyInMWH"].sum()
    vre_awarded = vre["AwardedEnergyInMWH"].sum()
    row["VRE Curtailment %"] = round(
        (vre_offered - vre_awarded) / vre_offered * 100, 3
    ) if vre_offered > 0 else 0.0

    gen_rows.append(row)

gen_df = pd.DataFrame(gen_rows)

print("\n  Renewable generation (TWh):")
res_cols = ["Run"] + [f"{t} TWh" for t in TECHS if t in RES_TECH]
print(gen_df[res_cols].to_string(index=False))

print("\n  Conventional generation (TWh):")
conv_cols = ["Run"] + [f"{t} TWh" for t in TECHS if t not in RES_TECH]
print(gen_df[conv_cols].to_string(index=False))

print("\n  System totals:")
summary_cols = ["Run", "Total TWh", "RES Share %", "Conv Share %", "VRE Curtailment %"]
print(gen_df[summary_cols].to_string(index=False))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: Conventional Operator Profitability
# ─────────────────────────────────────────────────────────────────────────────
section_header("SECTION 3: CONVENTIONAL OPERATOR PROFITABILITY  (ConventionalPlantOperator.csv)")

conv_rows = []
for run in RUNS:
    conv = load(run, "ConventionalPlantOperator.csv")
    for agent_id, group in conv.groupby("AgentId"):
        fuel = CONV_AGENT_FUEL.get(agent_id, f"Agent{agent_id}")
        revenue  = group["ReceivedMoneyInEUR"].sum()
        var_cost = group["VariableCostsInEUR"].sum()
        fix_cost = group["FixedCostsInEUR"].sum()
        awarded  = group["AwardedEnergyInMWH"].sum()
        co2_t    = group["Co2EmissionsInT"].sum()
        gross_margin = revenue - var_cost
        rev_per_mwh  = revenue / awarded if awarded > 0 else np.nan
        gm_per_mwh   = gross_margin / awarded if awarded > 0 else np.nan
        conv_rows.append({
            "Run":              run,
            "Fuel":             fuel,
            "Awarded MWH":      round(awarded,       0),
            "Revenue (EUR)":    round(revenue,       0),
            "VarCost (EUR)":    round(var_cost,      0),
            "Gross Margin (EUR)": round(gross_margin, 0),
            "Rev/MWH":          round(rev_per_mwh,   4),
            "GM/MWH":           round(gm_per_mwh,    4),
            "CO2 kt":           round(co2_t / 1e3,   2),
            "GM > 0?":          "YES" if gross_margin > 0 else "no",
        })

conv_prof_df = pd.DataFrame(conv_rows)

print("\n  -- Revenue & Costs per fuel type (all runs) --")
cols_a = ["Run", "Fuel", "Awarded MWH", "Revenue (EUR)", "VarCost (EUR)", "Gross Margin (EUR)", "GM > 0?"]
print(conv_prof_df[cols_a].to_string(index=False))

print("\n  -- Per-MWH metrics & CO2 --")
cols_b = ["Run", "Fuel", "Rev/MWH", "GM/MWH", "CO2 kt"]
print(conv_prof_df[cols_b].to_string(index=False))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: RES Revenue & Support (all traders combined)
# ─────────────────────────────────────────────────────────────────────────────
section_header("SECTION 4: RES REVENUE & SUPPORT  (all trader CSVs combined)")

res_rows = []
for run in RUNS:
    sup_recv   = 0.0
    sup_refund = 0.0
    mkt_rev    = 0.0
    awarded    = 0.0

    for fname in ("RenewableTrader.csv", "SystemOperatorTrader.csv", "NoSupportTrader.csv"):
        df = load_if_exists(run, fname)
        if df is None:
            continue
        sup_recv   += df["ReceivedSupportInEUR"].sum()
        sup_refund += df["RefundedSupportInEUR"].sum()
        mkt_rev    += df["ReceivedMarketRevenues"].sum()
        awarded    += df["AwardedEnergyInMWH"].sum()

    net_sup    = sup_recv - sup_refund
    total_rev  = net_sup + mkt_rev
    mkt_share  = mkt_rev    / total_rev * 100 if total_rev else np.nan
    sup_share  = net_sup    / total_rev * 100 if total_rev else np.nan
    rev_per_mwh = total_rev / awarded if awarded else np.nan

    res_rows.append({
        "Run":                  run,
        "Awarded MWH":          round(awarded,       0),
        "Net Support (EUR)":    round(net_sup,       0),
        "Market Rev (EUR)":     round(mkt_rev,       0),
        "Total Rev (EUR)":      round(total_rev,     0),
        "Total Rev/MWH":        round(rev_per_mwh,   4),
        "Market Share %":       round(mkt_share,     2),
        "Support Share %":      round(sup_share,     2),
    })

res_df = pd.DataFrame(res_rows)
print(res_df.to_string(index=False))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: Total Support Expenditure (system cost)
# ─────────────────────────────────────────────────────────────────────────────
section_header("SECTION 5: TOTAL SUPPORT EXPENDITURE  (RenewableTrader + SystemOperatorTrader)")

# Also compute total RES MWH (VRE + Biogas) for cost-per-MWH metric
sup_rows = []
for run in RUNS:
    vre_mwh = load(run, "VariableRenewableOperator.csv")["AwardedEnergyInMWH"].sum()
    bio_mwh = load(run, "Biogas.csv")["AwardedEnergyInMWH"].sum()
    total_res_mwh = vre_mwh + bio_mwh

    sup_total = 0.0
    ref_total = 0.0
    for fname in ("RenewableTrader.csv", "SystemOperatorTrader.csv"):
        df = load_if_exists(run, fname)
        if df is None:
            continue
        sup_total += df["ReceivedSupportInEUR"].sum()
        ref_total += df["RefundedSupportInEUR"].sum()

    net_support = sup_total - ref_total
    sup_per_mwh = net_support / total_res_mwh if total_res_mwh else np.nan

    sup_rows.append({
        "Run":                      run,
        "Gross Support (EUR)":      round(sup_total,     0),
        "Refunded Support (EUR)":   round(ref_total,     0),
        "Net Support (EUR)":        round(net_support,   0),
        "Total RES MWH":            round(total_res_mwh, 0),
        "Net Support/MWH (EUR)":    round(sup_per_mwh,   4),
    })

sup_df = pd.DataFrame(sup_rows)
print(sup_df.to_string(index=False))

# FIT vs baseline highlight
baseline_sup = sup_df.loc[sup_df["Run"] == "germany_baseline", "Net Support (EUR)"].values[0]
fit_sup      = sup_df.loc[sup_df["Run"] == "fit_scenario",     "Net Support (EUR)"].values[0]
print(f"\n  FIT vs MPVAR (baseline) support cost: "
      f"fit={fit_sup:,.0f} EUR  baseline={baseline_sup:,.0f} EUR  "
      f"diff={fit_sup - baseline_sup:+,.0f} EUR "
      f"({(fit_sup/baseline_sup - 1)*100:+.1f}%)")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6: Per-Technology LCOE Coverage Ratio
# ─────────────────────────────────────────────────────────────────────────────
section_header("SECTION 6: PER-TECHNOLOGY LCOE COVERAGE (market revenue vs LCOE)")
print("  Method: coverage_ratio = scenario_market_weighted_avg_price / agent_LCOE")
print("  Interpretation: % of LCOE covered by spot market alone (support = LCOE - market)\n")

lcoe_rows = []
for run in RUNS:
    mkt_price = market_avg[run]
    vre = load(run, "VariableRenewableOperator.csv")

    for agent_id, lcoe in sorted(AGENT_LCOE.items()):
        tech    = VRE_AGENT_TECH.get(agent_id, "?")
        support = VRE_AGENT_SUPPORT.get(agent_id, "?")
        agent_mwh = vre.loc[vre["AgentId"] == agent_id, "AwardedEnergyInMWH"].sum()

        # Market-only revenue per MWH = spot price (all VRE bid near zero)
        coverage = mkt_price / lcoe if lcoe else np.nan
        net_support_needed = max(0.0, lcoe - mkt_price)

        lcoe_rows.append({
            "Run":                  run,
            "AgentId":              agent_id,
            "Tech":                 tech,
            "Support Scheme":       support if run != "fit_scenario" else "FIT",
            "LCOE (EUR/MWH)":       lcoe,
            "Mkt Price (EUR/MWH)":  round(mkt_price, 4),
            "Coverage Ratio":       round(coverage, 4),
            "Support Needed (EUR/MWH)": round(net_support_needed, 4),
            "Awarded MWH":          round(agent_mwh, 0),
        })

lcoe_df = pd.DataFrame(lcoe_rows)

# Print summary: coverage ratio by run (averaged across agents, weighted by MWH)
print("  Weighted-average market coverage ratio by run:")
print(f"  {'Run':<22}  {'Wtd Coverage':>14}  {'Wtd Support Needed (EUR/MWH)':>28}")
print("  " + "-" * 68)
for run in RUNS:
    sub = lcoe_df[lcoe_df["Run"] == run].copy()
    sub = sub[sub["Awarded MWH"] > 0]
    if sub.empty:
        continue
    wtd_cov = (sub["Coverage Ratio"] * sub["Awarded MWH"]).sum() / sub["Awarded MWH"].sum()
    wtd_sup = (sub["Support Needed (EUR/MWH)"] * sub["Awarded MWH"]).sum() / sub["Awarded MWH"].sum()
    print(f"  {run:<22}  {wtd_cov:>14.4f}  {wtd_sup:>28.4f}")

print("\n  Per-cluster detail for germany_baseline and fit_scenario:")
for run in ["germany_baseline", "fit_scenario"]:
    print(f"\n  [{run}]")
    sub = lcoe_df[lcoe_df["Run"] == run][
        ["AgentId", "Tech", "Support Scheme", "LCOE (EUR/MWH)",
         "Mkt Price (EUR/MWH)", "Coverage Ratio", "Support Needed (EUR/MWH)", "Awarded MWH"]
    ]
    print(sub.to_string(index=False))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7: Storage Analysis (GenericFlexibilityTrader.csv)
# ─────────────────────────────────────────────────────────────────────────────
section_header("SECTION 7: STORAGE ANALYSIS  (GenericFlexibilityTrader.csv)")

storage_rows = []
for run in RUNS:
    df = load(run, "GenericFlexibilityTrader.csv")

    charge    = df["AwardedChargeEnergyInMWH"].sum()
    discharge = df["AwardedDischargeEnergyInMWH"].sum()
    revenue   = df["ReceivedMoneyInEUR"].sum()
    var_cost  = df["VariableCostsInEUR"].sum()
    net_rev   = revenue - var_cost

    mean_stored = df["StoredEnergyInMWH"].mean()
    cycle_proxy = discharge / mean_stored if mean_stored > 0 else np.nan

    rev_per_mwh_dis = net_rev / discharge if discharge > 0 else np.nan
    roundtrip = discharge / charge if charge > 0 else np.nan

    storage_rows.append({
        "Run":                    run,
        "Charge MWH":             round(charge,         0),
        "Discharge MWH":          round(discharge,      0),
        "Round-trip Eff.":        round(roundtrip,      4),
        "Revenue (EUR)":          round(revenue,        0),
        "VarCost (EUR)":          round(var_cost,       0),
        "Net Revenue (EUR)":      round(net_rev,        0),
        "Net Rev/MWH dis.":       round(rev_per_mwh_dis, 4),
        "Cycle Count Proxy":      round(cycle_proxy,    2),
        "Net Rev > 0?":           "YES" if net_rev > 0 else "no",
    })

storage_df = pd.DataFrame(storage_rows)
print(storage_df.to_string(index=False))

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8: Consumer Cost of Support (Support Levy Analysis)
# ─────────────────────────────────────────────────────────────────────────────
section_header("SECTION 8: CONSUMER COST OF SUPPORT  (support levy per MWH consumed)")

# Typical German household electricity consumption
HOUSEHOLD_KWH = 3500.0   # kWh/year (Bundesnetzagentur reference household)
HOUSEHOLD_MWH = HOUSEHOLD_KWH / 1000.0

consumer_rows = []
for run in RUNS:
    # Total demand consumed (from DemandTrader — AwardedEnergyInMWH)
    dem_df       = load(run, "DemandTrader.csv")
    total_demand = dem_df["AwardedEnergyInMWH"].sum()   # MWH

    # Total net support paid out (MPVAR + FIT, net of any refunds)
    total_support = 0.0
    for fname in ("RenewableTrader.csv", "SystemOperatorTrader.csv"):
        df = load_if_exists(run, fname)
        if df is not None:
            total_support += (df["ReceivedSupportInEUR"].sum()
                              - df["RefundedSupportInEUR"].sum())

    # Weighted-average market price (consumer energy cost)
    mkt_df        = load(run, "DayAheadMarketSingleZone.csv")
    p             = mkt_df["ElectricityPriceInEURperMWH"]
    e             = mkt_df["AwardedEnergyInMWH"]
    wtd_mkt_price = (p * e).sum() / e.sum() if e.sum() > 0 else 0.0

    # Per-MWH metrics
    support_levy_mwh  = total_support / total_demand if total_demand > 0 else 0.0
    total_cost_mwh    = wtd_mkt_price + support_levy_mwh

    # Annual household bill components
    hh_energy_cost    = wtd_mkt_price   * HOUSEHOLD_MWH
    hh_support_levy   = support_levy_mwh * HOUSEHOLD_MWH
    hh_total          = total_cost_mwh  * HOUSEHOLD_MWH

    # Support levy as share of total consumer cost
    levy_share_pct    = (support_levy_mwh / total_cost_mwh * 100
                         if total_cost_mwh > 0 else 0.0)

    meta = RUN_META[run]
    consumer_rows.append({
        "Run":                     run,
        "Scheme":                  meta["scheme"],
        "CO2 Level":               meta["co2"],
        "Total Demand (TWh)":      round(total_demand / 1e6, 2),
        "Total Support (B€)":      round(total_support / 1e9, 2),
        "Market Price (€/MWH)":    round(wtd_mkt_price,     2),
        "Support Levy (€/MWH)":    round(support_levy_mwh,  2),
        "Total Cost (€/MWH)":      round(total_cost_mwh,    2),
        "HH Energy Cost (€/yr)":   round(hh_energy_cost,    0),
        "HH Support Levy (€/yr)":  round(hh_support_levy,   0),
        "HH Total Cost (€/yr)":    round(hh_total,          0),
        "Levy Share of Bill (%)":   round(levy_share_pct,    1),
    })

consumer_df = pd.DataFrame(consumer_rows)
print(consumer_df.to_string(index=False))

# ─────────────────────────────────────────────────────────────────────────────
# Save all sections to CSV
# ─────────────────────────────────────────────────────────────────────────────
output_path = os.path.join(PROJECT_DIR, "comprehensive_analysis.csv")
with open(output_path, "w", newline="") as f:
    f.write("SECTION 1: MARKET PRICES\n")
    price_df.to_csv(f, index=False)
    f.write("\nSECTION 2: GENERATION MIX\n")
    gen_df.to_csv(f, index=False)
    f.write("\nSECTION 3: CONVENTIONAL OPERATOR PROFITABILITY\n")
    conv_prof_df.to_csv(f, index=False)
    f.write("\nSECTION 4: RES REVENUE AND SUPPORT\n")
    res_df.to_csv(f, index=False)
    f.write("\nSECTION 5: TOTAL SUPPORT EXPENDITURE\n")
    sup_df.to_csv(f, index=False)
    f.write("\nSECTION 6: LCOE COVERAGE RATIO\n")
    lcoe_df.to_csv(f, index=False)
    f.write("\nSECTION 7: STORAGE ANALYSIS\n")
    storage_df.to_csv(f, index=False)
    f.write("\nSECTION 8: CONSUMER COST OF SUPPORT\n")
    consumer_df.to_csv(f, index=False)

print()
print(f"  Results saved → {output_path}")
print()
