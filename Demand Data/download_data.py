import boto3
import os
# FIXED VERSION — two bugs corrected vs previous:
# 1. fetch_and_aggregate now uses out.electricity.total.energy_consumption only.
#    Old code summed all individual end-use columns + the total column,
#    double-counting every kWh ~2x.
# 2. to_hourly output is divided by 1000 (kWh -> MWh).
#    Old code left values in kWh, inflating expenditure by 1000x.
from botocore import UNSIGNED
from botocore.config import Config
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import os
os.chdir(r"C:\Users\egorg\OneDrive\Desktop\AmirisMischief\SYDE532Project\Demand Data")
# --- Config
BUCKET = "oedi-data-lake"
BASE = "nrel-pds-building-stock/end-use-load-profiles-for-us-building-stock/2024/resstock_amy2018_release_2/timeseries_individual_buildings/by_state/upgrade=0"
STATES_TO_USE = ["VA", "TX", "CA", "NY", "FL"]
N_BUILDINGS = int(os.getenv("N_BUILDINGS", "100"))

LOW_INCOME_BANDS  = ["<10000", "10000-14999", "15000-19999"]
HIGH_INCOME_BANDS = ["160000-179999", "180000-199999", "200000+"]

s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))

# ============================================================
# Step 1: List building IDs that actually exist in S3
# ============================================================
def get_available_ids_for_state(state):
    ids = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=f"{BASE}/state={state}/"):
        for obj in page.get("Contents", []):
            fname = obj["Key"].split("/")[-1]
            bldg_id = int(fname.split("-")[0])
            ids.append(bldg_id)
    return ids

print("Step 1: Listing available building IDs from S3...")
available_rows = []
for state in STATES_TO_USE:
    ids = get_available_ids_for_state(state)
    print(f"  {state}: {len(ids)} buildings in S3")
    for bid in ids:
        available_rows.append({"bldg_id": bid, "in.state": state})

available_df = pd.DataFrame(available_rows)

# ============================================================
# Step 2: Load metadata and join to confirmed-available IDs
# ============================================================
print("\nStep 2: Loading metadata...")
meta = pd.read_csv(
    "baseline_metadata_and_annual_results.csv",
    usecols=["bldg_id", "in.income", "in.state"]
)

merged = available_df.merge(meta, on=["bldg_id", "in.state"])
print(f"  Matched {len(merged)} buildings (confirmed in S3 + metadata)")

low_pool  = merged[merged["in.income"].isin(LOW_INCOME_BANDS)]
high_pool = merged[merged["in.income"].isin(HIGH_INCOME_BANDS)]
print(f"  Low income pool:  {len(low_pool)}")
print(f"  High income pool: {len(high_pool)}")

# ============================================================
# Step 3: State-balanced sampling
# ============================================================
def balanced_sample(pool, reference_pool, n, random_state=42):
    ref_dist = reference_pool["in.state"].value_counts(normalize=True)
    frames = []
    for state, frac in ref_dist.items():
        n_state = max(1, round(frac * n))
        state_pool = pool[pool["in.state"] == state]
        if len(state_pool) == 0:
            print(f"  Warning: no {state} buildings in pool, skipping")
            continue
        n_draw = min(n_state, len(state_pool))
        frames.append(state_pool.sample(n_draw, random_state=random_state))
    result = pd.concat(frames)
    if len(result) > n:
        result = result.sample(n, random_state=random_state)
    return result

reference   = low_pool if len(low_pool) < len(high_pool) else high_pool
low_sample  = balanced_sample(low_pool,  reference, N_BUILDINGS)
high_sample = balanced_sample(high_pool, reference, N_BUILDINGS)

print("\n=== State Distribution After Balancing ===")
print("\nLow income sample:")
print(low_sample["in.state"].value_counts(normalize=True).mul(100).round(1).to_string())
print("\nHigh income sample:")
print(high_sample["in.state"].value_counts(normalize=True).mul(100).round(1).to_string())

# ============================================================
# Step 4: Fetch parquets and aggregate
# FIX: use out.electricity.total.energy_consumption only.
# Old code summed all individual end-use columns AND the total
# column, double-counting every kWh roughly 2x.
# ============================================================
def fetch_and_aggregate(sample_df, label):
    print(f"\nStep 4: Fetching buildings for [{label}]...")
    series_list = []
    for i, (_, row) in enumerate(sample_df.iterrows()):
        key = f"{BASE}/state={row['in.state']}/{row['bldg_id']}-0.parquet"
        try:
            obj = s3.get_object(Bucket=BUCKET, Key=key)
            df = pd.read_parquet(BytesIO(obj["Body"].read()))

            if "timestamp" in df.columns:
                df = df.set_index("timestamp")

            # Use only the pre-aggregated total — avoids double-counting sub-columns
            s = df["out.electricity.total.energy_consumption"]
            s = s[~s.index.duplicated(keep="first")]

            if len(s) > 0:
                span_days = (s.index.max() - s.index.min()).total_seconds() / (24 * 3600)
                if span_days < 300:
                    raise ValueError(f"Truncated time series ({span_days:.1f} days)")

            series_list.append(s)
            if (i + 1) % 10 == 0:
                print(f"  {i+1}/{len(sample_df)} done...")
        except Exception as e:
            print(f"  Skipped {row['bldg_id']}: {e}")

    if not series_list:
        raise ValueError(f"No buildings loaded for {label}")

    combined = pd.concat(series_list, axis=1)
    combined = combined.loc[~combined.index.duplicated(keep="first")]
    return combined.mean(axis=1)

low_profile  = fetch_and_aggregate(low_sample,  "low_income")
high_profile = fetch_and_aggregate(high_sample, "high_income")

# ============================================================
# Step 5: Resample to hourly, convert kWh -> MWh, and save
# FIX: divide by 1000. Old code left values in kWh, inflating
# expenditure calculations by a factor of 1000.
# ============================================================
def to_hourly(profile):
    profile = profile.copy()
    idx = profile.index

    if isinstance(idx, pd.DatetimeIndex):
        dt_index = idx
    else:
        idx_num = pd.to_numeric(idx, errors="coerce")
        if idx_num.notna().all():
            mx = float(idx_num.max())
            if mx <= 10000:
                dt_index = pd.to_datetime(idx_num, unit="h", origin="2018-01-01")
            elif mx <= 40000000:
                dt_index = pd.to_datetime(idx_num, unit="s", origin="2018-01-01")
            else:
                dt_index = pd.to_datetime(idx_num)
        else:
            dt_index = pd.to_datetime(idx)

    profile.index = dt_index
    profile = profile[~profile.index.duplicated(keep="first")]
    return profile.resample("h").sum()

low_hourly  = to_hourly(low_profile)  / 1000  # kWh -> MWh
high_hourly = to_hourly(high_profile) / 1000  # kWh -> MWh

low_hourly.to_csv("demand_low_income.csv",   header=["load_mwh"])
high_hourly.to_csv("demand_high_income.csv", header=["load_mwh"])

print(f"\nCSVs saved.")
print(f"  Low income  annual total: {low_hourly.sum():.2f} MWh  (expected ~10-15 MWh)")
print(f"  High income annual total: {high_hourly.sum():.2f} MWh (expected ~15-25 MWh)")

# ============================================================
# Plotting
# ============================================================
low  = low_hourly
high = high_hourly
if isinstance(low,  pd.DataFrame): low  = low.iloc[:,  0]
if isinstance(high, pd.DataFrame): high = high.iloc[:, 0]

low_label  = "Low Income (<$20k)"
high_label = "High Income (>$160k)"
if hasattr(low,  "name"): low.name  = low_label
if hasattr(high, "name"): high.name = high_label

COLORS = {"low": "#E07B54", "high": "#4A90D9"}
plt.rcParams.update({
    "font.family": "sans-serif",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "--",
    "figure.dpi": 150,
})

# Plot 1: Annual average daily profile
fig, ax = plt.subplots(figsize=(10, 5))
low_daily  = low.groupby(low.index.hour).mean()
high_daily = high.groupby(high.index.hour).mean()
ax.plot(low_daily.index,  low_daily.values,  color=COLORS["low"],  lw=2.5, label=low_label)
ax.plot(high_daily.index, high_daily.values, color=COLORS["high"], lw=2.5, label=high_label)
ax.fill_between(low_daily.index,  low_daily.values,  alpha=0.15, color=COLORS["low"])
ax.fill_between(high_daily.index, high_daily.values, alpha=0.15, color=COLORS["high"])
ax.set_xlabel("Hour of Day")
ax.set_ylabel("Average Load (MWh)")
ax.set_title("Annual Average Daily Load Profile")
ax.set_xticks(range(0, 24, 2))
ax.legend()
plt.tight_layout()
plt.savefig("plot1_daily_profile.png")
plt.close()
print("Saved plot1_daily_profile.png")

# Plot 2: Seasonal profiles
fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
seasons = {"Winter (Dec–Feb)": [12, 1, 2], "Summer (Jun–Aug)": [6, 7, 8]}
for ax, (season_name, months) in zip(axes, seasons.items()):
    low_s  = low[low.index.month.isin(months)].groupby(
              low[low.index.month.isin(months)].index.hour).mean()
    high_s = high[high.index.month.isin(months)].groupby(
              high[high.index.month.isin(months)].index.hour).mean()
    ax.plot(low_s.index,  low_s.values,  color=COLORS["low"],  lw=2.5, label=low_label)
    ax.plot(high_s.index, high_s.values, color=COLORS["high"], lw=2.5, label=high_label)
    ax.fill_between(low_s.index,  low_s.values,  alpha=0.15, color=COLORS["low"])
    ax.fill_between(high_s.index, high_s.values, alpha=0.15, color=COLORS["high"])
    ax.set_title(season_name)
    ax.set_xlabel("Hour of Day")
    ax.set_xticks(range(0, 24, 2))
    ax.legend()
axes[0].set_ylabel("Average Load (MWh)")
fig.suptitle("Seasonal Daily Load Profiles", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig("plot2_seasonal_profiles.png")
plt.close()
print("Saved plot2_seasonal_profiles.png")

# Plot 3: Load duration curve
fig, ax = plt.subplots(figsize=(10, 5))
low_sorted  = np.sort(low.dropna().values)[::-1]
high_sorted = np.sort(high.dropna().values)[::-1]
ax.plot(np.linspace(0, 100, len(low_sorted)),  low_sorted,  color=COLORS["low"],  lw=2, label=low_label)
ax.plot(np.linspace(0, 100, len(high_sorted)), high_sorted, color=COLORS["high"], lw=2, label=high_label)
ax.set_xlabel("% of Hours Exceeded")
ax.set_ylabel("Load (MWh)")
ax.set_title("Load Duration Curve")
ax.legend()
plt.tight_layout()
plt.savefig("plot3_load_duration.png")
plt.close()
print("Saved plot3_load_duration.png")

# Plot 4: Monthly average consumption
fig, ax = plt.subplots(figsize=(11, 5))
low_monthly  = low.resample("ME").mean()
high_monthly = high.resample("ME").mean()
x = np.arange(len(low_monthly))
w = 0.35
ax.bar(x - w/2, low_monthly.values,  w, color=COLORS["low"],  alpha=0.85, label=low_label)
ax.bar(x + w/2, high_monthly.values, w, color=COLORS["high"], alpha=0.85, label=high_label)
ax.set_xticks(x)
ax.set_xticklabels([m.strftime("%b") for m in low_monthly.index], rotation=45)
ax.set_ylabel("Average Hourly Load (MWh)")
ax.set_title("Monthly Average Load")
ax.legend()
plt.tight_layout()
plt.savefig("plot4_monthly.png")
plt.close()
print("Saved plot4_monthly.png")

# Plot 5: Summary stats
def load_stats(s):
    return {
        "Peak (95th pct)": np.percentile(s.dropna(), 95),
        "Mean":            s.mean(),
        "Base (5th pct)":  np.percentile(s.dropna(), 5),
        "Peak/Base Ratio": np.percentile(s.dropna(), 95) / max(np.percentile(s.dropna(), 5), 1e-6),
    }

stats_low  = load_stats(low)
stats_high = load_stats(high)

fig, ax = plt.subplots(figsize=(8, 5))
metrics = ["Peak (95th pct)", "Mean", "Base (5th pct)"]
x = np.arange(len(metrics))
w = 0.35
ax.bar(x - w/2, [stats_low[m]  for m in metrics], w, color=COLORS["low"],  alpha=0.85, label=low_label)
ax.bar(x + w/2, [stats_high[m] for m in metrics], w, color=COLORS["high"], alpha=0.85, label=high_label)
ax.set_xticks(x)
ax.set_xticklabels(metrics)
ax.set_ylabel("Load (MWh)")
ax.set_title("Load Characteristics Summary")
ax.legend()
ratio_low  = stats_low["Peak/Base Ratio"]
ratio_high = stats_high["Peak/Base Ratio"]
ax.text(0.98, 0.95,
        f"Peak/Base ratio\nLow Income: {ratio_low:.1f}x\nHigh Income: {ratio_high:.1f}x",
        transform=ax.transAxes, ha="right", va="top",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="gray", alpha=0.8),
        fontsize=9)
plt.tight_layout()
plt.savefig("plot5_load_stats.png")
plt.close()
print("Saved plot5_load_stats.png")

print("\n=== Summary Statistics (State-Balanced) ===")
for label, stats in [("Low Income", stats_low), ("High Income", stats_high)]:
    print(f"\n{label}:")
    for k, v in stats.items():
        print(f"  {k}: {v:.6f}")