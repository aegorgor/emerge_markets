import argparse
import csv
import shutil
import subprocess
from pathlib import Path


def read_co2_series(path: Path):
    rows = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ts, value = line.split(";", 1)
            rows.append((ts, float(value)))
    return rows


def write_co2_series(path: Path, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        for ts, value in rows:
            f.write(f"{ts};{value:.6f}\n")


def summarize_run(run_dir: Path):
    market_path = run_dir / "DayAheadMarketSingleZone.csv"
    demand_path = run_dir / "DemandTrader.csv"

    prices = {}
    weighted_sum = 0.0
    total_market_mwh = 0.0
    with market_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            ts = row["TimeStep"]
            p = float(row["ElectricityPriceInEURperMWH"])
            e = float(row["AwardedEnergyInMWH"])
            prices[ts] = p
            weighted_sum += p * e
            total_market_mwh += e

    demand_totals = {101: {"mwh": 0.0, "eur": 0.0}, 102: {"mwh": 0.0, "eur": 0.0}}
    with demand_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            agent = int(row["AgentId"])
            if agent not in demand_totals:
                continue
            ts = row["TimeStep"]
            awarded = float(row["AwardedEnergyInMWH"])
            demand_totals[agent]["mwh"] += awarded
            demand_totals[agent]["eur"] += awarded * prices.get(ts, 0.0)

    market_avg_price = weighted_sum / total_market_mwh if total_market_mwh else 0.0
    return {
        "market_avg_price_eur_per_mwh": market_avg_price,
        "market_total_awarded_mwh": total_market_mwh,
        "low_mwh": demand_totals[101]["mwh"],
        "low_eur": demand_totals[101]["eur"],
        "high_mwh": demand_totals[102]["mwh"],
        "high_eur": demand_totals[102]["eur"],
    }


def main():
    parser = argparse.ArgumentParser(description="Run AMIRIS for multiple carbon-tax levels and compare outputs.")
    parser.add_argument("--scenario-dir", default="Germany2019Alt")
    parser.add_argument("--levels", nargs="+", type=float, required=True, help="Absolute EUR/tCO2 values, e.g. 5 20 50")
    parser.add_argument("--out", default="Germany2019Alt/carbon_sweep_summary.csv")
    args = parser.parse_args()

    scenario_dir = Path(args.scenario_dir).resolve()
    co2_path = scenario_dir / "timeseries" / "co2_price.csv"
    scenario_path = scenario_dir / "scenario.yaml"
    output_summary = Path(args.out).resolve()
    backup_path = co2_path.with_suffix(".csv.bak")

    base_rows = read_co2_series(co2_path)
    shutil.copy2(co2_path, backup_path)

    results = []
    try:
        for level in args.levels:
            fixed_rows = [(ts, float(level)) for ts, _ in base_rows]
            write_co2_series(co2_path, fixed_rows)

            run_name = f"run_co2_{str(level).replace('.', 'p')}"
            run_dir = scenario_dir / run_name

            cmd = ["amiris", "run", "--scenario", str(scenario_path), "--output", run_name]
            subprocess.run(cmd, cwd=scenario_dir, check=True)

            summary = summarize_run(run_dir)
            summary["co2_level_eur_per_ton"] = level
            summary["run_dir"] = run_name
            results.append(summary)
    finally:
        shutil.copy2(backup_path, co2_path)
        backup_path.unlink(missing_ok=True)

    output_summary.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "co2_level_eur_per_ton",
        "run_dir",
        "market_avg_price_eur_per_mwh",
        "market_total_awarded_mwh",
        "low_mwh",
        "low_eur",
        "high_mwh",
        "high_eur",
    ]
    with output_summary.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Wrote comparison summary: {output_summary}")


if __name__ == "__main__":
    main()

