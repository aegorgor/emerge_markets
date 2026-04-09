"""
generate_plots.py
─────────────────
Generates presentation-ready figures from AMIRIS simulation outputs.
Figures saved to PROJECT_DIR/plots/

Full 4x3 matrix: 4 support schemes x 3 CO2 price levels = 12 scenarios.

  fig1_generation_mix.png     — Stacked generation by technology (4 support schemes at baseline CO2)
  fig2_price_distribution.png — Electricity price box plots (full 4x3 matrix)
  fig3_res_revenue.png        — RES revenue: market vs support breakdown per MWH
  fig4_support_cost.png       — Total support expenditure heatmap (4x3 matrix)
  fig5_lcoe_coverage.png      — Market coverage ratio vs LCOE by technology cluster
  fig6_conventional.png       — Conventional operator gross margin by fuel type
  fig7_storage.png            — Storage net revenue and cycle proxy across scenarios
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import os

# ─── Configuration ────────────────────────────────────────────────────────────

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PLOTS_DIR   = os.path.join(PROJECT_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)
SEP = ";"

# Full 4x3 matrix
RUNS = [
    "germany_baseline", "low_co2", "high_co2",
    "no_support", "no_support_low_co2", "no_support_high_co2",
    "mpvar_reduced", "mpvar_reduced_low_co2", "mpvar_reduced_high_co2",
    "fit_scenario", "fit_only_low_co2", "fit_only_high_co2",
]

# 4 support schemes (baseline CO2 run for each)
BASELINE_RUNS = ["germany_baseline", "no_support", "mpvar_reduced", "fit_scenario"]

# Matrix structure for 4x3 heatmaps
SCHEMES       = ["Baseline\n(MPVAR+FIT)", "No\nSupport", "MPVAR\nReduced", "FIT\nOnly"]
CO2_LEVELS    = ["Low CO₂\n(0 €/t)", "Baseline CO₂\n(~24 €/t)", "High CO₂\n(65 €/t)"]
MATRIX_RUNS   = [
    ["low_co2",           "germany_baseline", "high_co2"],
    ["no_support_low_co2","no_support",        "no_support_high_co2"],
    ["mpvar_reduced_low_co2","mpvar_reduced",  "mpvar_reduced_high_co2"],
    ["fit_only_low_co2",  "fit_scenario",      "fit_only_high_co2"],
]

SCENARIO_LABELS = {
    "germany_baseline":       "Baseline\n(MPVAR+FIT)",
    "low_co2":                "Low CO₂",
    "high_co2":               "High CO₂",
    "no_support":             "No\nSupport",
    "no_support_low_co2":     "No Sup.\nLow CO₂",
    "no_support_high_co2":    "No Sup.\nHigh CO₂",
    "mpvar_reduced":          "MPVAR\nReduced",
    "mpvar_reduced_low_co2":  "MPVAR Red.\nLow CO₂",
    "mpvar_reduced_high_co2": "MPVAR Red.\nHigh CO₂",
    "fit_scenario":           "FIT\nOnly",
    "fit_only_low_co2":       "FIT\nLow CO₂",
    "fit_only_high_co2":      "FIT\nHigh CO₂",
}

SCENARIO_SHORT = {
    "germany_baseline":       "Baseline",
    "low_co2":                "Baseline / Low CO₂",
    "high_co2":               "Baseline / High CO₂",
    "no_support":             "No Support",
    "no_support_low_co2":     "No Support / Low CO₂",
    "no_support_high_co2":    "No Support / High CO₂",
    "mpvar_reduced":          "MPVAR Reduced",
    "mpvar_reduced_low_co2":  "MPVAR Red. / Low CO₂",
    "mpvar_reduced_high_co2": "MPVAR Red. / High CO₂",
    "fit_scenario":           "FIT Only",
    "fit_only_low_co2":       "FIT Only / Low CO₂",
    "fit_only_high_co2":      "FIT Only / High CO₂",
}

# Colors by support scheme (used for baseline CO2 runs and matrix rows)
SCHEME_COLORS = {
    "germany_baseline": "#4C72B0",
    "no_support":       "#DD8452",
    "mpvar_reduced":    "#8172B2",
    "fit_scenario":     "#937860",
}

# CO2-level shading (light → dark within each scheme)
CO2_ALPHA = {"low": 0.5, "baseline": 1.0, "high": 0.75}

SCENARIO_COLORS = {
    "germany_baseline":       "#4C72B0",
    "low_co2":                "#4C72B0",
    "high_co2":               "#4C72B0",
    "no_support":             "#DD8452",
    "no_support_low_co2":     "#DD8452",
    "no_support_high_co2":    "#DD8452",
    "mpvar_reduced":          "#8172B2",
    "mpvar_reduced_low_co2":  "#8172B2",
    "mpvar_reduced_high_co2": "#8172B2",
    "fit_scenario":           "#937860",
    "fit_only_low_co2":       "#937860",
    "fit_only_high_co2":      "#937860",
}

CO2_HATCHES = {
    "low_co2": "//", "no_support_low_co2": "//", "mpvar_reduced_low_co2": "//", "fit_only_low_co2": "//",
    "high_co2": "xx", "no_support_high_co2": "xx", "mpvar_reduced_high_co2": "xx", "fit_only_high_co2": "xx",
    "germany_baseline": "", "no_support": "", "mpvar_reduced": "", "fit_scenario": "",
}

TECH_COLORS = {
    "PV":         "#FFD700",
    "WindOn":     "#87CEEB",
    "WindOff":    "#1E6FD9",
    "RunOfRiver": "#20B2AA",
    "Biogas":     "#5CB85C",
    "OtherRES":   "#ADFF2F",
    "Nuclear":    "#9370DB",
    "Lignite":    "#8B6914",
    "HardCoal":   "#808080",
    "Gas_CCGT":   "#FF8C00",
    "Gas_OCGT":   "#FFB347",
    "Oil":        "#2F4F4F",
}

CONV_AGENT_FUEL = {
    500: "Nuclear", 501: "Lignite", 502: "HardCoal",
    503: "Gas_CCGT", 504: "Gas_OCGT", 505: "Oil",
}

VRE_AGENT_TECH = {
    10: "PV",      20: "WindOn",    50: "RunOfRiver",
    52: "Biogas",  53: "OtherRES",
    60: "PV",      61: "PV",        62: "PV",       63: "PV",       64: "PV",
    70: "WindOn",  71: "WindOn",    72: "WindOn",   73: "WindOn",   74: "WindOn",
    80: "WindOff", 81: "WindOff",   82: "WindOff",  83: "WindOff",
}

AGENT_LCOE = {
    10: 120.0, 20: 85.0,   50: 100.0,
    60: 97.21, 61: 202.91, 62: 286.67, 63: 340.07, 64: 440.05,
    70: 70.58, 71: 79.65,  72: 87.24,  73: 94.17,  74: 100.26,
    80: 154.0, 81: 174.5,  82: 184.0,  83: 194.0,
}

# Ordered stack for generation mix chart
TECH_STACK = ["PV", "WindOn", "WindOff", "RunOfRiver", "Biogas", "OtherRES",
              "Nuclear", "Gas_CCGT", "Gas_OCGT", "HardCoal", "Lignite", "Oil"]
RES_TECH = {"PV", "WindOn", "WindOff", "RunOfRiver", "Biogas", "OtherRES"}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def load(run, f):
    return pd.read_csv(os.path.join(PROJECT_DIR, run, f), sep=SEP)

def load_if_exists(run, f):
    p = os.path.join(PROJECT_DIR, run, f)
    return pd.read_csv(p, sep=SEP) if os.path.exists(p) else None

def save_fig(fig, name):
    path = os.path.join(PLOTS_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved → {path}")

plt.rcParams.update({
    "font.family":      "DejaVu Sans",
    "font.size":        11,
    "axes.titlesize":   13,
    "axes.titleweight": "bold",
    "axes.labelsize":   11,
    "legend.fontsize":  9,
    "figure.facecolor": "white",
    "axes.facecolor":   "#F8F8F8",
    "axes.edgecolor":   "#CCCCCC",
    "axes.grid":        True,
    "grid.color":       "white",
    "grid.linewidth":   1.0,
    "xtick.color":      "#333333",
    "ytick.color":      "#333333",
})

# ─────────────────────────────────────────────────────────────────────────────
# Pre-compute generation data (shared across figs 1 & 3)
# ─────────────────────────────────────────────────────────────────────────────
print("Computing generation data...")

gen_by_run = {}   # {run: {tech: MWH}}
mkt_avg    = {}   # {run: weighted avg price}

for run in RUNS:
    vre  = load(run, "VariableRenewableOperator.csv")
    bio  = load(run, "Biogas.csv")
    conv = load(run, "ConventionalPlantOperator.csv")
    mkt  = load(run, "DayAheadMarketSingleZone.csv")

    g = {}
    for aid, grp in vre.groupby("AgentId"):
        t = VRE_AGENT_TECH.get(aid, "OtherRES")
        g[t] = g.get(t, 0.0) + grp["AwardedEnergyInMWH"].sum()
    g["Biogas"] = g.get("Biogas", 0.0) + bio["AwardedEnergyInMWH"].sum()
    for aid, grp in conv.groupby("AgentId"):
        t = CONV_AGENT_FUEL.get(aid, "Oil")
        g[t] = g.get(t, 0.0) + grp["AwardedEnergyInMWH"].sum()

    gen_by_run[run] = g
    p = mkt["ElectricityPriceInEURperMWH"]
    e = mkt["AwardedEnergyInMWH"]
    mkt_avg[run] = (p * e).sum() / e.sum() if e.sum() > 0 else 0.0

# ═════════════════════════════════════════════════════════════════════════════
# FIG 1 — Generation Mix by Technology
# ═════════════════════════════════════════════════════════════════════════════
print("Generating Fig 1: Generation Mix...")

fig, ax = plt.subplots(figsize=(10, 6))

# Show only baseline-CO2 runs (generation is identical across CO2 levels)
GEN_RUNS = BASELINE_RUNS
x     = np.arange(len(GEN_RUNS))
width = 0.65
bottoms = np.zeros(len(GEN_RUNS))
handles = []

for tech in TECH_STACK:
    vals = np.array([gen_by_run[r].get(tech, 0.0) / 1e6 for r in GEN_RUNS])
    ax.bar(x, vals, width, bottom=bottoms,
           color=TECH_COLORS[tech], label=tech, zorder=3)
    handles.append(mpatches.Patch(color=TECH_COLORS[tech], label=tech))
    bottoms += vals

# Annotate RES share
for i, run in enumerate(GEN_RUNS):
    g    = gen_by_run[run]
    res  = sum(g.get(t, 0) for t in RES_TECH) / 1e6
    tot  = sum(g.values()) / 1e6
    pct  = res / tot * 100 if tot else 0
    ax.text(i, tot + 0.5, f"{pct:.1f}%\nRES", ha="center", va="bottom",
            fontsize=8.5, color="#333333", fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels([SCENARIO_LABELS[r] for r in GEN_RUNS], fontsize=11)
ax.set_ylabel("Annual Generation (TWh)")
ax.set_title("Generation Mix by Technology\n(Baseline CO₂ — dispatch unchanged across support schemes)")
ax.set_ylim(0, 620)

# Separate RES / Conventional legend
res_patches  = [mpatches.Patch(color=TECH_COLORS[t], label=t) for t in TECH_STACK if t in RES_TECH]
conv_patches = [mpatches.Patch(color=TECH_COLORS[t], label=t) for t in TECH_STACK if t not in RES_TECH]

leg1 = ax.legend(handles=res_patches,  title="Renewable",     bbox_to_anchor=(1.01, 1),   loc="upper left", framealpha=0.9)
leg2 = ax.legend(handles=conv_patches, title="Conventional",  bbox_to_anchor=(1.01, 0.45),loc="upper left", framealpha=0.9)
ax.add_artist(leg1)

fig.tight_layout()
save_fig(fig, "fig1_generation_mix.png")


# ═════════════════════════════════════════════════════════════════════════════
# FIG 2 — Electricity Price Distributions (Box Plots)
# ═════════════════════════════════════════════════════════════════════════════
print("Generating Fig 2: Price Distributions...")

fig, ax = plt.subplots(figsize=(13, 5.5))

# 4x3 matrix: 4 scheme groups, 3 CO2 levels each
CO2_COLORS = {"low": "#55A868", "baseline": "#4C72B0", "high": "#C44E52"}
CO2_LABELS = {"low": "Low CO₂ (0 €/t)", "baseline": "Baseline CO₂ (~24 €/t)", "high": "High CO₂ (65 €/t)"}
CO2_KEYS   = ["low", "baseline", "high"]

# Map each matrix cell to its CO2 key
RUN_CO2_KEY = {
    "low_co2": "low",            "germany_baseline": "baseline",  "high_co2": "high",
    "no_support_low_co2": "low", "no_support": "baseline",        "no_support_high_co2": "high",
    "mpvar_reduced_low_co2": "low","mpvar_reduced": "baseline",   "mpvar_reduced_high_co2": "high",
    "fit_only_low_co2": "low",   "fit_scenario": "baseline",      "fit_only_high_co2": "high",
}

bw    = 0.28
group = 0
tick_positions = []
tick_labels    = []
plotted_co2    = set()

for si, scheme_row in enumerate(MATRIX_RUNS):
    for ci, co2key in enumerate(CO2_KEYS):
        run = scheme_row[ci]
        mkt = load(run, "DayAheadMarketSingleZone.csv")
        prices = mkt["ElectricityPriceInEURperMWH"].values
        pos = si * 4 + ci
        bp  = ax.boxplot(
            [prices], positions=[pos], widths=bw,
            patch_artist=True,
            medianprops=dict(color="black", linewidth=1.8),
            whiskerprops=dict(linewidth=1.2),
            capprops=dict(linewidth=1.2),
            flierprops=dict(marker="o", markersize=1.5, alpha=0.25, linestyle="none"),
        )
        bp["boxes"][0].set_facecolor(CO2_COLORS[co2key])
        bp["boxes"][0].set_alpha(0.82)
        if co2key not in plotted_co2:
            plotted_co2.add(co2key)

    tick_positions.append(si * 4 + 1)
    tick_labels.append(SCHEMES[si])
    if si < len(MATRIX_RUNS) - 1:
        ax.axvline(si * 4 + 3.5, color="#BBBBBB", lw=1, linestyle="--")

ax.set_xticks(tick_positions)
ax.set_xticklabels(tick_labels, fontsize=11)
ax.set_ylabel("Electricity Price (EUR/MWH)")
ax.set_title("Day-Ahead Market Price Distribution: 4×3 Scenario Matrix\n"
             "(8,760 hourly observations per scenario, Germany 2019)")
ax.set_ylim(-5, 140)
ax.axhline(0,   color="#C44E52", linestyle="--", lw=0.8, alpha=0.6)
ax.axhline(100, color="#8172B2", linestyle="--", lw=0.8, alpha=0.6)
ax.set_xlim(-0.5, 15.5)

co2_patches = [mpatches.Patch(color=CO2_COLORS[k], alpha=0.82, label=CO2_LABELS[k]) for k in CO2_KEYS]
ax.legend(handles=co2_patches, loc="upper right", framealpha=0.9, title="CO₂ Price Level")

fig.tight_layout()
save_fig(fig, "fig2_price_distribution.png")


# ═════════════════════════════════════════════════════════════════════════════
# FIG 3 — RES Revenue: Market vs Support Breakdown
# ═════════════════════════════════════════════════════════════════════════════
print("Generating Fig 3: RES Revenue Decomposition...")

fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

# Collect data for all 12 runs, grouped by scheme (4 groups x 3 CO2)
def get_res_revenue(run):
    sup_recv, sup_ref, mkt_rev, awarded = 0.0, 0.0, 0.0, 0.0
    for fname in ("RenewableTrader.csv", "SystemOperatorTrader.csv", "NoSupportTrader.csv"):
        df = load_if_exists(run, fname)
        if df is None:
            continue
        sup_recv += df["ReceivedSupportInEUR"].sum()
        sup_ref  += df["RefundedSupportInEUR"].sum()
        mkt_rev  += df["ReceivedMarketRevenues"].sum()
        awarded  += df["AwardedEnergyInMWH"].sum()
    net_sup = sup_recv - sup_ref
    total_sup = 0.0
    for fname in ("RenewableTrader.csv", "SystemOperatorTrader.csv"):
        df = load_if_exists(run, fname)
        if df is not None:
            total_sup += df["ReceivedSupportInEUR"].sum() - df["RefundedSupportInEUR"].sum()
    return {
        "mkt_mwh": mkt_rev / awarded if awarded else 0,
        "sup_mwh": net_sup / awarded if awarded else 0,
        "sup_b":   total_sup / 1e9,
    }

CO2_COLORS_3 = {"low": "#55A868", "baseline": "#4C72B0", "high": "#C44E52"}
CO2_LABELS_3 = {"low": "Low CO₂", "baseline": "Baseline CO₂", "high": "High CO₂"}
bw = 0.26

ax1 = axes[0]
ax2 = axes[1]

group_centers = []
tick_labels_g = []
pos = 0
for si, (scheme_runs, scheme_lbl) in enumerate(zip(MATRIX_RUNS, SCHEMES)):
    co2_offsets = [-bw, 0, bw]
    for ci, (run, co2key) in enumerate(zip(scheme_runs, ["low", "baseline", "high"])):
        d   = get_res_revenue(run)
        x_  = pos + co2_offsets[ci]
        col = CO2_COLORS_3[co2key]
        # Market portion: CO2 colour with hatching to distinguish from support
        ax1.bar(x_, d["mkt_mwh"], bw * 0.95, color=col, alpha=0.85,
                hatch="///", zorder=3, edgecolor="white",
                label=CO2_LABELS_3[co2key] if si == 0 else "")
        # Support portion: solid CO2 colour, stacked on top
        ax1.bar(x_, d["sup_mwh"], bw * 0.95, bottom=d["mkt_mwh"],
                color=col, alpha=0.85, zorder=3, edgecolor="white")
        ax2.bar(x_, d["sup_b"],   bw * 0.95, color=CO2_COLORS_3[co2key], alpha=0.85,
                zorder=3, edgecolor="white")
    group_centers.append(pos)
    tick_labels_g.append(scheme_lbl)
    if si < len(MATRIX_RUNS) - 1:
        ax1.axvline(pos + 0.55, color="#DDDDDD", lw=1)
        ax2.axvline(pos + 0.55, color="#DDDDDD", lw=1)
    pos += 1.5

VRE_CAPACITY = {
    10: 32510, 20: 2355,  50: 5268,
    60: 8424,  61: 4474,  62: 1292,  63: 847,   64: 207,
    70: 3848,  71: 5735,  72: 14134, 73: 14670, 74: 12811,
    80: 673,   81: 79,    82: 2108,  83: 4644,
}
avg_lcoe_wtd = (sum(AGENT_LCOE[a] * VRE_CAPACITY[a] for a in AGENT_LCOE)
                / sum(VRE_CAPACITY.values()))
ax1.axhline(avg_lcoe_wtd, color="#C44E52", linestyle="--", lw=1.5, zorder=4,
            label=f"Avg LCOE ({avg_lcoe_wtd:.0f} EUR/MWH)")

ax1.set_xticks(group_centers)
ax1.set_xticklabels(tick_labels_g, fontsize=9.5)
ax1.set_ylabel("Revenue (EUR / MWH Awarded)")
ax1.set_title("RES Revenue per MWH:\nMarket (hatched) + Support (solid) — coloured by CO₂ level")

# Combine legend: CO2 colors + pattern keys + LCOE line
from matplotlib.lines import Line2D
co2_patches_3 = [mpatches.Patch(color=CO2_COLORS_3[k], alpha=0.85, label=CO2_LABELS_3[k])
                 for k in ["low", "baseline", "high"]]
mkt_patch  = mpatches.Patch(facecolor="#888888", hatch="///", alpha=0.85, label="Market revenue (hatched)")
sup_patch  = mpatches.Patch(facecolor="#888888", alpha=0.85, label="Support payment (solid)")
lcoe_line  = Line2D([0], [0], color="#C44E52", linestyle="--", lw=1.5, label=f"Avg LCOE ({avg_lcoe_wtd:.0f} EUR/MWH)")
ax1.legend(handles=co2_patches_3 + [mkt_patch, sup_patch, lcoe_line],
           fontsize=8, framealpha=0.9, loc="upper right")
ax1.set_ylim(0, 165)

ax2.set_xticks(group_centers)
ax2.set_xticklabels(tick_labels_g, fontsize=9.5)
ax2.set_ylabel("Total Net Support (EUR Billion)")
ax2.set_title("Total Support Expenditure\nby Scheme and CO₂ Level")
ax2.set_ylim(0, 27)

fig.suptitle("RES Revenue Decomposition and Support Cost — 4×3 Matrix", fontsize=13, fontweight="bold", y=1.01)
fig.tight_layout()
save_fig(fig, "fig3_res_revenue.png")


# ═════════════════════════════════════════════════════════════════════════════
# FIG 4 — LCOE Coverage Ratio by Technology Cluster
# ═════════════════════════════════════════════════════════════════════════════
print("Generating Fig 4: LCOE Coverage Ratio...")

# Focus on 3 key scenarios for clarity
KEY_RUNS   = ["low_co2", "germany_baseline", "high_co2"]
KEY_LABELS = ["Low CO₂ (0 €/t)", "Baseline CO₂ (~24 €/t)", "High CO₂ (65 €/t)"]
KEY_COLORS = ["#55A868", "#4C72B0", "#C44E52"]   # green / blue / red by CO₂ level

# Order agents: PV clusters, then WindOn, then WindOff, then others
AGENT_ORDER = [10, 60, 61, 62, 63, 64,
               20, 70, 71, 72, 73, 74,
               80, 81, 82, 83,
               50]
AGENT_X_LABELS = {
    10: "PV\n(FIT)",
    60: "PV\nCl1", 61: "PV\nCl2", 62: "PV\nCl3", 63: "PV\nCl4", 64: "PV\nCl5",
    20: "W-On\n(FIT)",
    70: "WOn\nCl1", 71: "WOn\nCl2", 72: "WOn\nCl3", 73: "WOn\nCl4", 74: "WOn\nCl5",
    80: "WOff\nCl1", 81: "WOff\nCl2", 82: "WOff\nCl3", 83: "WOff\nCl4",
    50: "Run-of-\nRiver",
}

n_agents  = len(AGENT_ORDER)
n_groups  = len(KEY_RUNS)
bar_w     = 0.25
x_base    = np.arange(n_agents)

fig, ax = plt.subplots(figsize=(15, 6))

for gi, (run, label, color) in enumerate(zip(KEY_RUNS, KEY_LABELS, KEY_COLORS)):
    offsets   = x_base + (gi - 1) * bar_w
    coverages = [mkt_avg[run] / AGENT_LCOE[a] * 100 for a in AGENT_ORDER]
    ax.bar(offsets, coverages, bar_w, label=label, color=color, alpha=0.85,
           zorder=3, edgecolor="white")

# 100% reference line
ax.axhline(100, color="#C44E52", linestyle="--", lw=2, zorder=4,
           label="100% — full LCOE recovery from market")

# Technology group separators and labels
group_bounds = [(0, 5, "PV Clusters"), (6, 11, "Wind Onshore Clusters"),
                (12, 15, "Wind Offshore Clusters"), (16, 16, "Run-of-River")]
for start, end, label in group_bounds:
    mid = (start + end) / 2
    ax.text(mid, -12, label, ha="center", fontsize=8.5, style="italic",
            color="#555555")
    if start > 0:
        ax.axvline(start - 0.5, color="#BBBBBB", lw=1, linestyle="-", zorder=1)

ax.set_xticks(x_base)
ax.set_xticklabels([AGENT_X_LABELS[a] for a in AGENT_ORDER], fontsize=8)
ax.set_ylabel("Market Coverage Ratio (% of LCOE)")
ax.set_title("Spot Market Coverage of LCOE by Technology Cluster\n"
             "Coverage = Weighted-Avg Market Price ÷ Cluster LCOE  |  Gap below 100% = support required")
ax.legend(loc="upper right", framealpha=0.9)
ax.set_ylim(-18, 120)
ax.yaxis.set_major_formatter(mticker.PercentFormatter())

# Shade the "needs support" region
ax.axhspan(0, 100, alpha=0.05, color="#C44E52", zorder=0)

fig.tight_layout()
save_fig(fig, "fig4_lcoe_coverage.png")


# ═════════════════════════════════════════════════════════════════════════════
# FIG 5 — Conventional Operator Gross Margin by Fuel Type
# ═════════════════════════════════════════════════════════════════════════════
print("Generating Fig 5: Conventional Operator Profitability...")

KEY_RUNS2   = ["low_co2", "germany_baseline", "high_co2"]
KEY_LABELS2 = ["Low CO₂ (0 €/t)", "Baseline CO₂ (~24 €/t)", "High CO₂ (65 €/t)"]
KEY_COL2    = ["#55A868", "#4C72B0", "#C44E52"]   # green / blue / red by CO₂ level
FUELS       = ["Nuclear", "Lignite", "HardCoal", "Gas_CCGT", "Gas_OCGT"]
FUEL_NICE   = {"Nuclear": "Nuclear", "Lignite": "Lignite",
               "HardCoal": "Hard Coal", "Gas_CCGT": "Gas\n(CCGT)", "Gas_OCGT": "Gas\n(OCGT)"}

# Build margin data
margins = {run: {} for run in KEY_RUNS2}
rev_mwh = {run: {} for run in KEY_RUNS2}

for run in KEY_RUNS2:
    conv = load(run, "ConventionalPlantOperator.csv")
    for aid, grp in conv.groupby("AgentId"):
        fuel = CONV_AGENT_FUEL.get(aid)
        if fuel not in FUELS:
            continue
        rev  = grp["ReceivedMoneyInEUR"].sum()
        vc   = grp["VariableCostsInEUR"].sum()
        mwh  = grp["AwardedEnergyInMWH"].sum()
        margins[run][fuel] = (rev - vc) / mwh if mwh else 0
        rev_mwh[run][fuel] = rev / mwh if mwh else 0

fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

x_f   = np.arange(len(FUELS))
bar_w = 0.26

# Left: Gross Margin per MWH
ax1 = axes[0]
for gi, (run, label, color) in enumerate(zip(KEY_RUNS2, KEY_LABELS2, KEY_COL2)):
    vals = [margins[run].get(f, 0) for f in FUELS]
    ax1.bar(x_f + (gi - 1) * bar_w, vals, bar_w, label=label,
            color=color, alpha=0.88, zorder=3, edgecolor="white")

ax1.axhline(0, color="black", lw=1.5, zorder=5)
ax1.set_xticks(x_f)
ax1.set_xticklabels([FUEL_NICE[f] for f in FUELS])
ax1.set_ylabel("Gross Margin (EUR / MWH)")
ax1.set_title("Gross Margin (Revenue − Variable Cost)\nper MWH Dispatched")
ax1.legend(framealpha=0.9)
ax1.set_ylim(-20, 55)

# Annotate sign changes
for gi, run in enumerate(KEY_RUNS2):
    for fi, fuel in enumerate(FUELS):
        val = margins[run].get(fuel, 0)
        if abs(val) > 3:
            yoff = val + 1.5 if val >= 0 else val - 2.5
            ax1.text(fi + (gi - 1) * bar_w, yoff, f"{val:.0f}",
                     ha="center", fontsize=7, color="#333333")

# Right: Revenue per MWH vs market avg
ax2 = axes[1]
for gi, (run, label, color) in enumerate(zip(KEY_RUNS2, KEY_LABELS2, KEY_COL2)):
    vals = [rev_mwh[run].get(f, 0) for f in FUELS]
    ax2.bar(x_f + (gi - 1) * bar_w, vals, bar_w, label=label,
            color=color, alpha=0.88, zorder=3, edgecolor="white")

# Market avg price reference — use neutral grays to avoid clashing with bar colors
for run, label, color, ls in zip(KEY_RUNS2, KEY_LABELS2, KEY_COL2, ["-", "--", ":"]):
    ax2.axhline(mkt_avg[run], color=color, lw=1.8, linestyle=ls,
                alpha=0.9, label=f"Mkt avg ({label}: {mkt_avg[run]:.0f} EUR/MWH)")

ax2.set_xticks(x_f)
ax2.set_xticklabels([FUEL_NICE[f] for f in FUELS])
ax2.set_ylabel("Revenue (EUR / MWH)")
ax2.set_title("Revenue per MWH vs Market Price\n(Nuclear & Lignite dispatch most hours → avg revenue ≈ market avg)")
handles, labels = ax2.get_legend_handles_labels()
ax2.legend(handles[3:], labels[3:], fontsize=8, framealpha=0.9, loc="upper left")

fig.suptitle("Conventional Operator Profitability Under CO₂ Price Variation",
             fontsize=14, fontweight="bold", y=1.01)
fig.tight_layout()
save_fig(fig, "fig5_conventional.png")


# ═════════════════════════════════════════════════════════════════════════════
# FIG 6 — Storage Performance
# ═════════════════════════════════════════════════════════════════════════════
print("Generating Fig 6: Storage Performance...")

# Use CO2-level runs to show CO2 effect on storage, grouped by scheme
STORAGE_RUNS = [
    "low_co2", "germany_baseline", "high_co2",
]
STORAGE_LABELS = ["Low CO₂\n(0 €/t)", "Baseline CO₂\n(~24 €/t)", "High CO₂\n(65 €/t)"]
STORAGE_COLORS = ["#55A868", "#4C72B0", "#C44E52"]

storage_data = []
for run in STORAGE_RUNS:
    df = load(run, "GenericFlexibilityTrader.csv")
    ch   = df["AwardedChargeEnergyInMWH"].sum()
    dis  = df["AwardedDischargeEnergyInMWH"].sum()
    rev  = df["ReceivedMoneyInEUR"].sum()
    vc   = df["VariableCostsInEUR"].sum()
    net  = rev - vc
    mean_stored = df["StoredEnergyInMWH"].mean()
    cycles = dis / mean_stored if mean_stored > 0 else 0
    rev_per_dis = net / dis if dis > 0 else 0
    storage_data.append({
        "run": run,
        "charge_twh": ch / 1e6,
        "discharge_twh": dis / 1e6,
        "net_rev_m": net / 1e6,
        "rev_per_mwh": rev_per_dis,
        "cycles": cycles,
    })

fig, axes = plt.subplots(1, 3, figsize=(13, 5))
x      = np.arange(len(STORAGE_RUNS))
width  = 0.5
colors = STORAGE_COLORS
labels = STORAGE_LABELS

# Panel 1: Charge vs Discharge
ax1 = axes[0]
ch_vals  = [d["charge_twh"] for d in storage_data]
dis_vals = [d["discharge_twh"] for d in storage_data]
ax1.bar(x - 0.18, ch_vals,  0.36, label="Charge",    color="#9ecae1", zorder=3, edgecolor="white")
ax1.bar(x + 0.18, dis_vals, 0.36, label="Discharge", color="#3182bd", zorder=3, edgecolor="white")
ax1.set_xticks(x)
ax1.set_xticklabels(labels, fontsize=8.5)
ax1.set_ylabel("Energy (TWh)")
ax1.set_title("Storage Throughput:\nCharge vs Discharge")
ax1.legend(framealpha=0.9)

# Panel 2: Net Revenue
ax2 = axes[1]
net_vals = [d["net_rev_m"] for d in storage_data]
bars = ax2.bar(x, net_vals, width, color=colors, alpha=0.88, zorder=3, edgecolor="white")
for bar, val in zip(bars, net_vals):
    ax2.text(bar.get_x() + bar.get_width() / 2, val + 1.5,
             f"€{val:.0f}M", ha="center", fontsize=8, color="#333333")
ax2.set_xticks(x)
ax2.set_xticklabels(labels, fontsize=8.5)
ax2.set_ylabel("Net Revenue (EUR Million)")
ax2.set_title("Storage Net Revenue\n(Revenue − Variable Costs)")
ax2.set_ylim(0, 160)
ax2.axhline(0, color="black", lw=1)

# Panel 3: Revenue per MWH + Cycle proxy (dual axis)
ax3 = axes[2]
rev_mwh_vals = [d["rev_per_mwh"] for d in storage_data]
cycle_vals   = [d["cycles"] for d in storage_data]

bars3 = ax3.bar(x, rev_mwh_vals, width, color=colors, alpha=0.88, zorder=3, edgecolor="white")
ax3.set_ylabel("Net Revenue per MWH Discharged (EUR)", color="#333333")
ax3.set_xticks(x)
ax3.set_xticklabels(labels, fontsize=8.5)
ax3.set_title("Revenue per MWH & Cycle Count")
ax3.set_ylim(0, 30)

ax3b = ax3.twinx()
ax3b.plot(x, cycle_vals, "s--", color="#C44E52", lw=2, ms=7, zorder=5, label="Cycle count")
ax3b.set_ylabel("Annual Cycle Count Proxy", color="#C44E52")
ax3b.tick_params(axis="y", labelcolor="#C44E52")
ax3b.set_ylim(1400, 2100)
ax3b.legend(loc="upper right", fontsize=9)

for bar, val in zip(bars3, rev_mwh_vals):
    ax3.text(bar.get_x() + bar.get_width() / 2, val + 0.4,
             f"{val:.1f}", ha="center", fontsize=8, color="#333333")

fig.suptitle("Energy Storage (Battery) Performance Across Policy Scenarios",
             fontsize=14, fontweight="bold", y=1.01)
fig.tight_layout()
save_fig(fig, "fig6_storage.png")


# ═════════════════════════════════════════════════════════════════════════════
# FIG 7 — 4×3 Support Cost Heatmap
# ═════════════════════════════════════════════════════════════════════════════
print("Generating Fig 7: 4×3 Support Cost Heatmap...")

def get_total_support_b(run):
    total = 0.0
    for fname in ("RenewableTrader.csv", "SystemOperatorTrader.csv"):
        df = load_if_exists(run, fname)
        if df is not None:
            total += df["ReceivedSupportInEUR"].sum() - df["RefundedSupportInEUR"].sum()
    return total / 1e9

def get_avg_price(run):
    return mkt_avg[run]

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# ── Left: Total support cost heatmap ─────────────────────────────────────────
support_matrix = np.array([
    [get_total_support_b(run) for run in row] for row in MATRIX_RUNS
])

ax1 = axes[0]
im1 = ax1.imshow(support_matrix, cmap="YlOrRd", aspect="auto", vmin=0, vmax=22)
cbar1 = fig.colorbar(im1, ax=ax1, fraction=0.04, pad=0.03)
cbar1.set_label("Total Support (B€/year)", fontsize=10)

for r in range(4):
    for c in range(3):
        val = support_matrix[r, c]
        ax1.text(c, r, f"€{val:.1f}B", ha="center", va="center",
                 fontsize=11, fontweight="bold",
                 color="white" if val > 11 else "#333333")

ax1.set_xticks(range(3))
ax1.set_xticklabels(CO2_LEVELS, fontsize=9.5)
ax1.set_yticks(range(4))
ax1.set_yticklabels(SCHEMES, fontsize=10)
ax1.set_title("Total RES Support Expenditure\n(€ Billion / Year)", fontsize=12, fontweight="bold")

# ── Right: Average market price heatmap ──────────────────────────────────────
price_matrix = np.array([
    [get_avg_price(run) for run in row] for row in MATRIX_RUNS
])

ax2 = axes[1]
im2 = ax2.imshow(price_matrix, cmap="RdYlGn_r", aspect="auto", vmin=15, vmax=70)
cbar2 = fig.colorbar(im2, ax=ax2, fraction=0.04, pad=0.03)
cbar2.set_label("Avg Market Price (EUR/MWH)", fontsize=10)

for r in range(4):
    for c in range(3):
        val = price_matrix[r, c]
        ax2.text(c, r, f"{val:.1f}", ha="center", va="center",
                 fontsize=12, fontweight="bold",
                 color="white" if val > 50 else "#333333")

ax2.set_xticks(range(3))
ax2.set_xticklabels(CO2_LEVELS, fontsize=9.5)
ax2.set_yticks(range(4))
ax2.set_yticklabels(SCHEMES, fontsize=10)
ax2.set_title("Average Day-Ahead Market Price\n(EUR/MWH)", fontsize=12, fontweight="bold")

fig.suptitle("4×3 Scenario Matrix Summary: Support Cost and Market Prices",
             fontsize=14, fontweight="bold", y=1.02)
fig.tight_layout()
save_fig(fig, "fig7_matrix_heatmap.png")

# ═════════════════════════════════════════════════════════════════════════════
# FIG 8 — Consumer Cost of Support (Household Bill Decomposition)
# ═════════════════════════════════════════════════════════════════════════════
print("Generating Fig 8: Consumer Cost of Support...")

HOUSEHOLD_MWH = 3.5   # 3,500 kWh reference household

def get_consumer_costs(run):
    dem = load(run, "DemandTrader.csv")
    total_demand = dem["AwardedEnergyInMWH"].sum()

    total_support = 0.0
    for fname in ("RenewableTrader.csv", "SystemOperatorTrader.csv"):
        df = load_if_exists(run, fname)
        if df is not None:
            total_support += (df["ReceivedSupportInEUR"].sum()
                              - df["RefundedSupportInEUR"].sum())

    levy_mwh  = total_support / total_demand if total_demand > 0 else 0.0
    mkt_price = mkt_avg[run]  # weighted avg already computed
    return {
        "energy": mkt_price  * HOUSEHOLD_MWH,
        "levy":   levy_mwh   * HOUSEHOLD_MWH,
        "total":  (mkt_price + levy_mwh) * HOUSEHOLD_MWH,
        "levy_mwh": levy_mwh,
        "mkt_mwh":  mkt_price,
    }

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# ── Left: Stacked household bill by scheme group (4 groups × 3 CO2 bars) ─────
ax1 = axes[0]
CO2_COLORS_C = {"low": "#55A868", "baseline": "#4C72B0", "high": "#C44E52"}
CO2_KEY_MAP  = {
    "low_co2":               "low",  "germany_baseline":       "baseline", "high_co2":               "high",
    "no_support_low_co2":    "low",  "no_support":             "baseline", "no_support_high_co2":    "high",
    "mpvar_reduced_low_co2": "low",  "mpvar_reduced":          "baseline", "mpvar_reduced_high_co2": "high",
    "fit_only_low_co2":      "low",  "fit_scenario":           "baseline", "fit_only_high_co2":      "high",
}

bw = 0.26
group_centers = []
pos = 0
for si, scheme_runs in enumerate(MATRIX_RUNS):
    offsets = [-bw, 0, bw]
    for ci, run in enumerate(scheme_runs):
        c = get_consumer_costs(run)
        co2key = CO2_KEY_MAP[run]
        col = CO2_COLORS_C[co2key]
        x_  = pos + offsets[ci]
        ax1.bar(x_, c["energy"], bw * 0.92, color="#B0C4DE", alpha=0.9, zorder=3, edgecolor="white")
        ax1.bar(x_, c["levy"],   bw * 0.92, bottom=c["energy"],
                color=col, alpha=0.85, zorder=3, edgecolor="white")
    group_centers.append(pos)
    if si < len(MATRIX_RUNS) - 1:
        ax1.axvline(pos + 0.55, color="#DDDDDD", lw=1)
    pos += 1.5

ax1.set_xticks(group_centers)
ax1.set_xticklabels(SCHEMES, fontsize=10)
ax1.set_ylabel("Annual Cost (EUR / household)")
ax1.set_title("Household Electricity Bill Decomposition\n(3,500 kWh/yr reference household)")
ax1.set_ylim(0, 390)

# Legend
from matplotlib.lines import Line2D
energy_patch = mpatches.Patch(color="#B0C4DE", alpha=0.9, label="Energy cost (market price)")
co2_patches_c = [mpatches.Patch(color=CO2_COLORS_C[k], alpha=0.85,
                                label=f"Support levy — {'Low' if k=='low' else 'Baseline' if k=='baseline' else 'High'} CO₂")
                 for k in ["low", "baseline", "high"]]
ax1.legend(handles=[energy_patch] + co2_patches_c, fontsize=8.5, framealpha=0.9, loc="upper left")

# ── Right: Support levy per MWH heatmap (4×3) ───────────────────────────────
ax2 = axes[1]
levy_matrix = np.array([
    [get_consumer_costs(run)["levy_mwh"] for run in row] for row in MATRIX_RUNS
])

im = ax2.imshow(levy_matrix, cmap="YlOrRd", aspect="auto", vmin=0, vmax=42)
cbar = fig.colorbar(im, ax=ax2, fraction=0.04, pad=0.03)
cbar.set_label("Support Levy (EUR/MWH consumed)", fontsize=10)

for r in range(4):
    for c in range(3):
        val = levy_matrix[r, c]
        ax2.text(c, r, f"€{val:.1f}", ha="center", va="center",
                 fontsize=12, fontweight="bold",
                 color="white" if val > 25 else "#333333")

ax2.set_xticks(range(3))
ax2.set_xticklabels(CO2_LEVELS, fontsize=9.5)
ax2.set_yticks(range(4))
ax2.set_yticklabels(SCHEMES, fontsize=10)
ax2.set_title("Support Levy per MWH Consumed\n(EUR/MWH — socialised across all demand)", fontsize=11, fontweight="bold")

fig.suptitle("Consumer Cost of RES Support: 4×3 Scenario Matrix",
             fontsize=13, fontweight="bold", y=1.02)
fig.tight_layout()
save_fig(fig, "fig8_consumer_cost.png")

# ─────────────────────────────────────────────────────────────────────────────
print()
print("All 8 figures saved to:", PLOTS_DIR)
print()
