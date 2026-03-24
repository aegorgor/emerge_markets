"""
plot_income_comparison.py
=========================
Produces comparison plots for low- and high-income household electricity demand
and costs derived from the AMIRIS carbon-sweep simulation.

Data sources
------------
- Demand Data/demand_low_income.csv   : per-household hourly load (MWh)
- Demand Data/demand_high_income.csv  : same for high-income households
- Germany2019Alt/carbon_sweep_summary.csv : AMIRIS market-clearing results

Income assumptions
-------------------
- Low income  : $15,000 USD/year  (midpoint of <$10k–$20k bands sampled)
- High income : $200,000 USD/year (representative of $160k–$200k+ bands)
- EUR → USD conversion: 1 EUR = 1.12 USD (2018/2019 average rate)

Note on AMIRIS costs
---------------------
The AMIRIS simulation uses German 2019 *wholesale* electricity prices. These
are significantly lower than US retail tariffs (no distribution/tax markup).
The figures represent the market-clearing cost component only, applied here as
a stylised proxy for how carbon-price pass-through affects each income group.

Usage
-----
    python plot_income_comparison.py
    python plot_income_comparison.py --out-dir my_plots
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

# ── Income parameters ────────────────────────────────────────────────────────
LOW_INCOME_USD  = 15_000
HIGH_INCOME_USD = 200_000
EUR_TO_USD      = 1.12

# ── Colours ──────────────────────────────────────────────────────────────────
C_LOW  = "#E07B54"
C_HIGH = "#4A90D9"

plt.rcParams.update({
    "font.family": "sans-serif",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "--",
    "figure.dpi": 150,
})


# ── Data loading ─────────────────────────────────────────────────────────────

def load_demand(base_dir: Path) -> tuple[pd.Series, pd.Series]:
    low  = pd.read_csv(base_dir / "demand_low_income.csv",  index_col=0, parse_dates=True).iloc[:, 0]
    high = pd.read_csv(base_dir / "demand_high_income.csv", index_col=0, parse_dates=True).iloc[:, 0]
    low  = low[~low.index.duplicated(keep="first")].iloc[:8760]
    high = high[~high.index.duplicated(keep="first")].iloc[:8760]
    return low, high


def load_sweep(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path).sort_values("co2_level_eur_per_ton").reset_index(drop=True)
    return df


def per_household_cost(sweep: pd.DataFrame, low_mwh: float, high_mwh: float) -> pd.DataFrame:
    df = sweep.copy()
    price = df["market_avg_price_eur_per_mwh"]
    df["low_cost_usd"]       = price * low_mwh  * EUR_TO_USD
    df["high_cost_usd"]      = price * high_mwh * EUR_TO_USD
    df["low_pct_income"]     = df["low_cost_usd"]  / LOW_INCOME_USD  * 100
    df["high_pct_income"]    = df["high_cost_usd"] / HIGH_INCOME_USD * 100
    df["regressivity_ratio"] = df["low_pct_income"] / df["high_pct_income"]
    df["absolute_gap_usd"]   = df["high_cost_usd"] - df["low_cost_usd"]
    df["burden_gap_pct"]     = df["low_pct_income"] - df["high_pct_income"]
    return df


def save(fig: plt.Figure, path: Path) -> None:
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path}")


# ── Plot 1: Annual average daily load profile ─────────────────────────────────

def plot_daily_profile(low: pd.Series, high: pd.Series, out: Path) -> None:
    lk = low  * 1000
    hk = high * 1000
    ld = lk.groupby(lk.index.hour).mean()
    hd = hk.groupby(hk.index.hour).mean()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(ld.index, ld.values, color=C_LOW,  lw=2.5, label="Low Income (<$20 k)")
    ax.plot(hd.index, hd.values, color=C_HIGH, lw=2.5, label="High Income (>$160 k)")
    ax.fill_between(ld.index, ld.values, alpha=0.15, color=C_LOW)
    ax.fill_between(hd.index, hd.values, alpha=0.15, color=C_HIGH)
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("Average Load (kWh / hr · household)")
    ax.set_title("Annual Average Daily Load Profile — per Household")
    ax.set_xticks(range(0, 24, 2))
    ax.legend()
    fig.tight_layout()
    save(fig, out)


# ── Plot 2: Demand difference & ratio by hour ─────────────────────────────────

def plot_demand_difference(low: pd.Series, high: pd.Series, out: Path) -> None:
    lk = low  * 1000
    hk = high * 1000
    diff  = (hk - lk).groupby((hk - lk).index.hour).mean()
    ratio = (hk / lk).replace([np.inf, -np.inf], np.nan).groupby(
            (hk / lk).index.hour).mean()

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    ax = axes[0]
    colors = [C_HIGH if v >= 0 else C_LOW for v in diff.values]
    ax.bar(diff.index, diff.values, color=colors, alpha=0.85)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("kWh / hr · household")
    ax.set_title("High − Low Income Demand Difference")
    ax.set_xticks(range(0, 24, 2))

    ax = axes[1]
    ax.plot(ratio.index, ratio.values, color=C_HIGH, lw=2.5, marker="o", ms=5)
    ax.axhline(1.0, color="black", lw=0.8, ls="--")
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("Ratio (High / Low)")
    ax.set_title("High-to-Low Demand Ratio by Hour of Day")
    ax.set_xticks(range(0, 24, 2))

    fig.suptitle("Demand Differences: Low vs High Income Households", fontweight="bold")
    fig.tight_layout()
    save(fig, out)


# ── Plot 3: Seasonal daily profiles ──────────────────────────────────────────

def plot_seasonal(low: pd.Series, high: pd.Series, out: Path) -> None:
    lk = low  * 1000
    hk = high * 1000
    seasons = {
        "Winter (Dec–Feb)": [12, 1, 2],
        "Spring (Mar–May)": [3, 4, 5],
        "Summer (Jun–Aug)": [6, 7, 8],
        "Autumn (Sep–Nov)": [9, 10, 11],
    }
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), sharey=True)
    for ax, (name, months) in zip(axes.flat, seasons.items()):
        ml = lk.index.month.isin(months)
        mh = hk.index.month.isin(months)
        ld = lk[ml].groupby(lk[ml].index.hour).mean()
        hd = hk[mh].groupby(hk[mh].index.hour).mean()
        ax.plot(ld.index, ld.values, color=C_LOW,  lw=2.2, label="Low Income (<$20 k)")
        ax.plot(hd.index, hd.values, color=C_HIGH, lw=2.2, label="High Income (>$160 k)")
        ax.fill_between(ld.index, ld.values, alpha=0.12, color=C_LOW)
        ax.fill_between(hd.index, hd.values, alpha=0.12, color=C_HIGH)
        ax.set_title(name)
        ax.set_xlabel("Hour of Day")
        ax.set_xticks(range(0, 24, 4))
        ax.legend(fontsize=8)
    for ax in axes[:, 0]:
        ax.set_ylabel("Avg Load (kWh / hr · household)")
    fig.suptitle("Seasonal Daily Load Profiles — per Household", fontsize=13, fontweight="bold")
    fig.tight_layout()
    save(fig, out)


# ── Plot 4: % of income vs CO₂ (the core regressivity story) ─────────────────

def plot_pct_income(df: pd.DataFrame, out: Path) -> None:
    x      = df["co2_level_eur_per_ton"].values
    lo_pct = df["low_pct_income"].values
    hi_pct = df["high_pct_income"].values

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x, lo_pct, "o-", color=C_LOW,  lw=2.5, ms=8,
            label=f"Low Income (~${LOW_INCOME_USD:,}/yr)")
    ax.plot(x, hi_pct, "s-", color=C_HIGH, lw=2.5, ms=8,
            label=f"High Income (~${HIGH_INCOME_USD:,}/yr)")
    ax.fill_between(x, hi_pct, lo_pct, alpha=0.10, color="gray")

    # Low income labels: above each point, left-aligned
    for xi, l in zip(x, lo_pct):
        ax.annotate(f"{l:.2f}%", (xi, l), textcoords="offset points",
                    xytext=(0, 10), ha="center", fontsize=9, color=C_LOW,
                    fontweight="bold")

    # High income labels: above each point (gap to low-income line is always >2%)
    for xi, h in zip(x, hi_pct):
        ax.annotate(f"{h:.3f}%", (xi, h), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=9, color=C_HIGH,
                    fontweight="bold")

    ax.set_ylim(0, lo_pct.max() * 1.18)
    ax.set_xlabel("CO₂ Price (EUR / tonne)")
    ax.set_ylabel("Electricity Cost as % of Annual Income")
    ax.set_title(
        "Electricity Cost Burden as % of Annual Income\n"
        f"Low ≈ ${LOW_INCOME_USD:,}/yr  |  High ≈ ${HIGH_INCOME_USD:,}/yr"
    )
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{y:.1f}%"))
    ax.legend(loc="upper left")
    fig.tight_layout()
    save(fig, out)


# ── Plot 5: Absolute cost vs CO₂ — same ratio, growing gap ───────────────────

def plot_absolute_cost_and_gap(df: pd.DataFrame, out: Path) -> None:
    x      = df["co2_level_eur_per_ton"].values
    lo_c   = df["low_cost_usd"].values
    hi_c   = df["high_cost_usd"].values
    gap    = df["absolute_gap_usd"].values

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]
    ax.plot(x, lo_c, "o-", color=C_LOW,  lw=2.5, ms=8, label="Low Income")
    ax.plot(x, hi_c, "s-", color=C_HIGH, lw=2.5, ms=8, label="High Income")
    ax.fill_between(x, lo_c, hi_c, alpha=0.10, color="gray", label="Absolute gap")
    # Alternate label sides to avoid overlap with lines
    for i, (xi, l, h) in enumerate(zip(x, lo_c, hi_c)):
        side = -30 if i % 2 == 0 else 10
        ax.annotate(f"${l:,.0f}", (xi, l), textcoords="offset points",
                    xytext=(side, 0), va="center", fontsize=8, color=C_LOW)
        ax.annotate(f"${h:,.0f}", (xi, h), textcoords="offset points",
                    xytext=(side, 0), va="center", fontsize=8, color=C_HIGH)
    ax.set_xlim(-12, 112)   # padding so left-side labels don't clip
    ax.set_xlabel("CO₂ Price (EUR / tonne)")
    ax.set_ylabel("Annual Electricity Cost (USD / household)")
    ax.set_title("Absolute Electricity Cost per Household")
    ax.legend()

    ax = axes[1]
    ax.bar(x, gap, width=8, color="#5A5A8B", alpha=0.85)
    for xi, g in zip(x, gap):
        ax.text(xi, g + 5, f"${g:,.0f}", ha="center", va="bottom", fontsize=9)
    ax.set_xlabel("CO₂ Price (EUR / tonne)")
    ax.set_ylabel("USD / household / year")
    ax.set_title("Absolute Dollar Gap: High minus Low Cost\n(High earns ~13× more but only pays ~$50–$135 more)")

    fig.suptitle(
        "Same Proportional Demand Ratio → Growing Absolute Dollar Gap",
        fontweight="bold", fontsize=12
    )
    fig.tight_layout()
    save(fig, out)


# ── Plot 6: Regressivity ratio ────────────────────────────────────────────────

def plot_regressivity(df: pd.DataFrame, out: Path) -> None:
    x     = df["co2_level_eur_per_ton"].values
    ratio = df["regressivity_ratio"].values

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(x, ratio, "D-", color="#8B1A1A", lw=2.5, ms=9,
            label="Burden ratio (Low % ÷ High %)")
    ax.axhline(1.0, color="gray", lw=1, ls="--", label="Proportional baseline")
    ax.fill_between(x, 1.0, ratio, alpha=0.15, color="#8B1A1A")
    # Single centred annotation instead of one per point (they're all identical)
    mid_x = x[len(x) // 2]
    mid_r = ratio[len(ratio) // 2]
    ax.annotate(f"Constant {mid_r:.1f}× across all CO₂ levels",
                xy=(mid_x, mid_r), xytext=(mid_x, mid_r - 3.5),
                ha="center", fontsize=10, color="#8B1A1A",
                arrowprops=dict(arrowstyle="->", color="#8B1A1A", lw=1.2))
    # Y-axis: keep baseline visible and leave headroom above the ratio line
    ax.set_ylim(0, ratio.max() * 1.25)
    ax.set_xlabel("CO₂ Price (EUR / tonne)")
    ax.set_ylabel("Regressivity Ratio")
    ax.set_title(
        "Regressivity of the Carbon-Inclusive Electricity Bill\n"
        "(Low-income burden %) ÷ (High-income burden %)"
    )
    ax.legend()
    fig.tight_layout()
    save(fig, out)


# ── Plot 7: The dual story — absolute gap grows, relative ratio is flat ───────

def plot_dual_story(df: pd.DataFrame, out: Path) -> None:
    """
    Two-panel summary: left shows % of income for both groups (relative burden
    diverges visually due to log scale); right shows that the regressivity ratio
    is constant while the absolute gap grows — the central policy insight.
    """
    x      = df["co2_level_eur_per_ton"].values
    lo_pct = df["low_pct_income"].values
    hi_pct = df["high_pct_income"].values
    ratio  = df["regressivity_ratio"].values
    gap    = df["absolute_gap_usd"].values

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Left: % of income on a log y-axis so both lines are readable
    ax = axes[0]
    ax.semilogy(x, lo_pct, "o-", color=C_LOW,  lw=2.5, ms=8,
                label=f"Low Income (~${LOW_INCOME_USD:,}/yr)")
    ax.semilogy(x, hi_pct, "s-", color=C_HIGH, lw=2.5, ms=8,
                label=f"High Income (~${HIGH_INCOME_USD:,}/yr)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{y:.2f}%"))
    ax.yaxis.set_minor_formatter(mticker.NullFormatter())
    ax.set_xlabel("CO₂ Price (EUR / tonne)")
    ax.set_ylabel("Electricity Cost as % of Income (log scale)")
    ax.set_title("% of Income Burden (log scale)")
    ax.legend()

    # Right: absolute gap (bar) + regressivity ratio (line, secondary axis)
    ax = axes[1]
    ax2 = ax.twinx()
    ax.bar(x, gap, width=7, color="#5A5A8B", alpha=0.6, label="Absolute gap (USD)")
    for xi, g in zip(x, gap):
        ax.text(xi, g + 1, f"${g:,.0f}", ha="center", va="bottom", fontsize=9, color="#5A5A8B")
    ax2.plot(x, ratio, "D-", color="#8B1A1A", lw=2.5, ms=8, label="Regressivity ratio (×)")
    # Single annotation for the flat ratio — avoids pile-up
    ax2.annotate(f"Flat at {ratio[0]:.1f}×",
                 xy=(x[-1], ratio[-1]), xytext=(-40, 12),
                 textcoords="offset points", fontsize=9, color="#8B1A1A",
                 arrowprops=dict(arrowstyle="->", color="#8B1A1A", lw=1))
    ax2.set_ylim(ratio[0] * 0.5, ratio[0] * 1.5)  # tighten so ratio line sits mid-panel
    ax.set_xlabel("CO₂ Price (EUR / tonne)")
    ax.set_ylabel("Absolute Dollar Gap (USD / household / year)", color="#5A5A8B")
    ax2.set_ylabel("Regressivity Ratio (Low % ÷ High %)", color="#8B1A1A")
    ax2.tick_params(axis="y", colors="#8B1A1A")
    ax.set_title("Absolute Gap Grows, but Relative Burden Ratio is Flat\n"
                 "(Inelastic demand: low income can't cut back)")

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)

    fig.suptitle(
        "The Regressivity Story: A Growing Dollar Burden on a Fixed Proportional Gap",
        fontweight="bold", fontsize=11
    )
    fig.tight_layout()
    save(fig, out)


# ── Plot 8: Carbon tax increment cost — who pays more per $10/t step ──────────

def plot_marginal_cost(df: pd.DataFrame, out: Path) -> None:
    """
    Cost increase per $10/t CO₂ increment, in absolute USD and as % of income.
    Highlights that both groups pay the same proportional increment per step,
    but low income households feel it much harder as a share of their budget.
    """
    co2  = df["co2_level_eur_per_ton"].values
    lo_c = df["low_cost_usd"].values
    hi_c = df["high_cost_usd"].values

    # Compute step-by-step increments
    step_co2 = co2[1:]
    d_lo_abs = np.diff(lo_c)
    d_hi_abs = np.diff(hi_c)
    d_lo_pct = d_lo_abs / LOW_INCOME_USD  * 100
    d_hi_pct = d_hi_abs / HIGH_INCOME_USD * 100

    w = 4
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]
    ax.bar(step_co2 - w/2, d_lo_abs, width=w, color=C_LOW,  alpha=0.85, label="Low Income")
    ax.bar(step_co2 + w/2, d_hi_abs, width=w, color=C_HIGH, alpha=0.85, label="High Income")
    ax.set_xlabel("CO₂ Price Step (EUR / tonne)")
    ax.set_ylabel("Additional Cost (USD / household / year)")
    ax.set_title("Absolute Cost Increase per 20 EUR/t CO₂ Step")
    ax.set_xticks(step_co2)
    ax.set_xticklabels([f"0→{int(c)}" for c in step_co2], fontsize=8)
    ax.legend()

    ax = axes[1]
    ax.bar(step_co2 - w/2, d_lo_pct, width=w, color=C_LOW,  alpha=0.85, label="Low Income")
    ax.bar(step_co2 + w/2, d_hi_pct, width=w, color=C_HIGH, alpha=0.85, label="High Income")
    # Label only low income bars (high income bars are too small for inline labels)
    for xi, l in zip(step_co2, d_lo_pct):
        ax.text(xi - w/2, l + 0.005, f"{l:.2f}%", ha="center", va="bottom", fontsize=8.5, color=C_LOW)
    # Add a single bracket/note for high income since all values are near zero
    ax.annotate(
        f"High income: {d_hi_pct[0]:.3f}–{d_hi_pct[-1]:.3f}% per step",
        xy=(step_co2[0] + w/2, d_hi_pct[0]),
        xytext=(step_co2[2], d_lo_pct.mean() * 0.4),
        fontsize=8, color=C_HIGH,
        arrowprops=dict(arrowstyle="->", color=C_HIGH, lw=0.8)
    )
    ax.set_ylim(0, d_lo_pct.max() * 1.35)
    ax.set_xlabel("CO₂ Price Step (EUR / tonne)")
    ax.set_ylabel("Additional Burden (% of Annual Income)")
    ax.set_title("Income Burden Increase per 20 EUR/t CO₂ Step\n"
                 "(Low income feels each step ~12× harder)")
    ax.set_xticks(step_co2)
    ax.set_xticklabels([f"0→{int(c)}" for c in step_co2], fontsize=8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{y:.2f}%"))
    ax.legend()

    fig.suptitle("Marginal Cost of Each CO₂ Price Increment", fontweight="bold")
    fig.tight_layout()
    save(fig, out)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demand-dir", type=Path, default=Path("Demand Data"))
    parser.add_argument("--sweep-csv",  type=Path, default=Path("Germany2019Alt/carbon_sweep_summary.csv"))
    parser.add_argument("--out-dir",    type=Path, default=Path("plots/income_comparison"))
    args = parser.parse_args()

    low, high = load_demand(args.demand_dir)
    low_mwh   = float(low.sum())
    high_mwh  = float(high.sum())

    print(f"Per-household annual demand:")
    print(f"  Low income  : {low_mwh*1000:.1f} kWh/yr")
    print(f"  High income : {high_mwh*1000:.1f} kWh/yr")
    print(f"  Ratio       : {high_mwh/low_mwh:.4f}×")

    sweep = load_sweep(args.sweep_csv)
    df    = per_household_cost(sweep, low_mwh, high_mwh)

    print("\nPer-household cost summary:")
    print(f"  {'CO2':>8}  {'Low USD':>10}  {'Low %inc':>9}  {'High USD':>10}  {'High %inc':>10}  {'Regress.':>9}")
    for _, r in df.iterrows():
        print(f"  {r['co2_level_eur_per_ton']:>8.0f}  "
              f"${r['low_cost_usd']:>9,.0f}  {r['low_pct_income']:>8.2f}%  "
              f"${r['high_cost_usd']:>9,.0f}  {r['high_pct_income']:>9.3f}%  "
              f"{r['regressivity_ratio']:>8.1f}×")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nSaving plots to: {args.out_dir.resolve()}")

    plot_daily_profile(low, high,          args.out_dir / "01_daily_profile.png")
    plot_demand_difference(low, high,      args.out_dir / "02_demand_difference.png")
    plot_seasonal(low, high,               args.out_dir / "03_seasonal_profiles.png")
    plot_pct_income(df,                    args.out_dir / "04_pct_income.png")
    plot_absolute_cost_and_gap(df,         args.out_dir / "05_absolute_cost_and_gap.png")
    plot_regressivity(df,                  args.out_dir / "06_regressivity.png")
    plot_dual_story(df,                    args.out_dir / "07_dual_story.png")
    plot_marginal_cost(df,                 args.out_dir / "08_marginal_cost.png")

    print("\nDone.")


if __name__ == "__main__":
    main()
