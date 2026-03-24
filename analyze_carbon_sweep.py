"""
Analyze and plot results from carbon_tax_sweep.py (carbon_sweep_summary.csv).

Uses only the standard library for tables. Plots need matplotlib:
  py -3 -m pip install matplotlib

Usage:
  python analyze_carbon_sweep.py
  python analyze_carbon_sweep.py --csv Germany2019Alt/carbon_sweep_summary.csv --out-dir plots/carbon_sweep
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def load_summary(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            out = {}
            for k, v in row.items():
                if k is None:
                    continue
                v = (v or "").strip()
                if not v:
                    out[k] = None
                else:
                    try:
                        out[k] = float(v) if "." in v or v.replace("-", "").isdigit() else v
                    except ValueError:
                        out[k] = v
            rows.append(out)
    rows.sort(key=lambda r: float(r.get("co2_level_eur_per_ton") or 0))
    return rows


def _fmt(x, spec=",.2f"):
    if x is None:
        return ""
    try:
        return format(float(x), spec)
    except (TypeError, ValueError):
        return str(x)


def print_analysis(rows: list[dict]) -> None:
    print("=" * 72)
    print("CARBON TAX SWEEP — SUMMARY")
    print("=" * 72)
    print("\nPer scenario (sorted by CO2 level EUR/t):\n")
    hdr = (
        f"{'CO2 EUR/t':>10}  {'Mkt EUR/MWh':>12}  {'Low MWh':>12}  {'Low EUR':>14}  "
        f"{'High MWh':>12}  {'High EUR':>14}"
    )
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        co2 = float(r.get("co2_level_eur_per_ton") or 0)
        print(
            f"{co2:>10.1f}  "
            f"{_fmt(r.get('market_avg_price_eur_per_mwh')):>12}  "
            f"{_fmt(r.get('low_mwh')):>12}  "
            f"{_fmt(r.get('low_eur')):>14}  "
            f"{_fmt(r.get('high_mwh')):>12}  "
            f"{_fmt(r.get('high_eur')):>14}"
        )

    print("\n--- Derived metrics ---")
    print(
        f"{'CO2 EUR/t':>10}  {'High-Low EUR':>14}  "
        f"{'Low avg EUR/MWh':>16}  {'High avg EUR/MWh':>16}"
    )
    print("-" * 62)
    for r in rows:
        low_m = float(r["low_mwh"] or 0)
        high_m = float(r["high_mwh"] or 0)
        low_e = float(r["low_eur"] or 0)
        high_e = float(r["high_eur"] or 0)
        gap = high_e - low_e
        la = low_e / low_m if low_m else float("nan")
        ha = high_e / high_m if high_m else float("nan")
        co2 = float(r["co2_level_eur_per_ton"] or 0)
        print(
            f"{co2:>10.1f}  {gap:>14,.2f}  {la:>14,.2f}  {ha:>14,.2f}"
        )

    baseline = rows[0]
    b_co2 = baseline.get("co2_level_eur_per_ton")
    b_low_e = float(baseline.get("low_eur") or 0)
    b_high_e = float(baseline.get("high_eur") or 0)
    b_mkt = float(baseline.get("market_avg_price_eur_per_mwh") or 0)
    print(f"\n--- % change vs lowest CO2 in file (baseline = {b_co2} EUR/t) ---")
    for r in rows:
        co2 = r.get("co2_level_eur_per_ton")
        low_e = float(r.get("low_eur") or 0)
        high_e = float(r.get("high_eur") or 0)
        mkt = float(r.get("market_avg_price_eur_per_mwh") or 0)
        low_pct = (low_e / b_low_e - 1) * 100 if b_low_e else float("nan")
        high_pct = (high_e / b_high_e - 1) * 100 if b_high_e else float("nan")
        m_pct = (mkt / b_mkt - 1) * 100 if b_mkt else float("nan")
        print(
            f"  CO2 {float(co2):>6.1f} EUR/t:  market price {m_pct:+6.1f}%  |  "
            f"low exp {low_pct:+6.1f}%  |  high exp {high_pct:+6.1f}%"
        )

    low_mwhs = [float(r["low_mwh"] or 0) for r in rows]
    high_mwhs = [float(r["high_mwh"] or 0) for r in rows]
    print("\n--- Energy (MWh) stability across scenarios ---")
    print(
        f"  low_mwh  min={min(low_mwhs):.4f}  max={max(low_mwhs):.4f}  "
        f"(flat if same demand series)"
    )
    print(f"  high_mwh min={min(high_mwhs):.4f}  max={max(high_mwhs):.4f}")
    print("=" * 72)


def plot_results(rows: list[dict], out_dir: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print(
            "\nSkipping plots (matplotlib not installed). "
            "Run: py -3 -m pip install matplotlib"
        )
        return

    x = [float(r["co2_level_eur_per_ton"]) for r in rows]
    mkt = [float(r["market_avg_price_eur_per_mwh"]) for r in rows]
    low_eur = [float(r["low_eur"]) for r in rows]
    high_eur = [float(r["high_eur"]) for r in rows]
    low_m = [float(r["low_mwh"]) for r in rows]
    high_m = [float(r["high_mwh"]) for r in rows]
    low_avg = [le / lm if lm else 0 for le, lm in zip(low_eur, low_m)]
    high_avg = [he / hm if hm else 0 for he, hm in zip(high_eur, high_m)]

    out_dir.mkdir(parents=True, exist_ok=True)

    fig1, ax1 = plt.subplots(figsize=(8, 5))
    ax1.plot(x, mkt, "o-", label="Market (weighted avg)", lw=2)
    ax1.plot(x, low_avg, "s--", label="Low-income (101) avg EUR/MWh", lw=2)
    ax1.plot(x, high_avg, "^--", label="High-income (102) avg EUR/MWh", lw=2)
    ax1.set_xlabel("CO2 price (EUR/t)")
    ax1.set_ylabel("EUR per MWh")
    ax1.set_title("Electricity price vs carbon tax level")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    fig1.tight_layout()
    p1 = out_dir / "carbon_sweep_prices.png"
    fig1.savefig(p1, dpi=150)
    plt.close(fig1)
    print(f"Saved: {p1}")

    fig2, ax2 = plt.subplots(figsize=(8, 5))
    n = len(x)
    if n == 1:
        w = 5.0
        xs = x
    else:
        span = max(x) - min(x)
        w = span / max(n * 2.5, 1)
    for i, xi in enumerate(x):
        ax2.bar(xi - w * 0.25, low_eur[i], width=w * 0.45, label="Low (101)" if i == 0 else "")
        ax2.bar(xi + w * 0.25, high_eur[i], width=w * 0.45, label="High (102)" if i == 0 else "")
    ax2.set_xlabel("CO2 price (EUR/t)")
    ax2.set_ylabel("Annual expenditure (EUR)")
    ax2.set_title("Community electricity cost vs carbon tax")
    handles, labels = ax2.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax2.legend(by_label.values(), by_label.keys())
    ax2.grid(True, axis="y", alpha=0.3)
    fig2.tight_layout()
    p2 = out_dir / "carbon_sweep_expenditure.png"
    fig2.savefig(p2, dpi=150)
    plt.close(fig2)
    print(f"Saved: {p2}")

    gap = [h - l for h, l in zip(high_eur, low_eur)]
    fig3, ax3 = plt.subplots(figsize=(8, 5))
    ax3.plot(x, gap, "o-", color="darkred", lw=2, markersize=8)
    ax3.set_xlabel("CO2 price (EUR/t)")
    ax3.set_ylabel("EUR/year")
    ax3.set_title("Expenditure gap: high-income vs low-income (102 − 101)")
    ax3.grid(True, alpha=0.3)
    fig3.tight_layout()
    p3 = out_dir / "carbon_sweep_inequality_gap.png"
    fig3.savefig(p3, dpi=150)
    plt.close(fig3)
    print(f"Saved: {p3}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze/plot carbon sweep summary CSV.")
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("Germany2019Alt/carbon_sweep_summary.csv"),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("plots/carbon_sweep"),
    )
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args()

    if not args.csv.is_file():
        raise SystemExit(f"CSV not found: {args.csv.resolve()}")

    rows = load_summary(args.csv)
    if not rows:
        raise SystemExit("CSV is empty.")

    print_analysis(rows)
    if not args.no_plot:
        plot_results(rows, args.out_dir)


if __name__ == "__main__":
    main()
