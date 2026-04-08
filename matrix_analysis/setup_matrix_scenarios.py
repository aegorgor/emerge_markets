#!/usr/bin/env python3
"""
Create the 5 missing scenario config directories for the 4x3 matrix:
  - no_support_high_co2_config
  - mpvar_reduced_low_co2_config
  - mpvar_reduced_high_co2_config
  - fit_only_low_co2_config
  - fit_only_high_co2_config

CO2 price conventions (constant for full 2019 simulation year):
  - Low CO2:      0.0 EUR/t  (matches existing low_co2 run, ~pre-ETS collapse)
  - High CO2:    65.0 EUR/t  (matches existing high_co2 run, ~2022 EU ETS levels)
  - Baseline CO2: actual 2019 EEX time-varying data (untouched)

Support policy conventions:
  - no_support:     all MPVAR Lcoe = 0.0, all FIT TsFit = 0.0 in SupportPolicy
  - mpvar_reduced:  MPVAR Lcoe x 0.75 (25% reduction), FIT TsFit unchanged
  - fit_only:       already in fit_scenario_config (all MPVAR -> FIT at LCOE rate)
"""

import os
import shutil
import re

PROJECT  = os.path.dirname(os.path.abspath(__file__))
G2019    = os.path.join(PROJECT, "Germany2019")
FIT_BASE = os.path.join(PROJECT, "fit_scenario_config")

# ─────────────────────────────────────────────────────────────────────────────
# CO2 timeseries helpers
# ─────────────────────────────────────────────────────────────────────────────
CO2_HIGH = 65.0   # EUR/t
CO2_LOW  = 0.0    # EUR/t

CO2_TS_TEMPLATE = (
    "2019-01-01_00:00:00;{price:.1f}\n"
    "2020-01-01_00:00:00;0.0\n"
    "2021-01-01_00:00:00;0.0\n"
)

def write_constant_co2(path, price):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(CO2_TS_TEMPLATE.format(price=price))


# ─────────────────────────────────────────────────────────────────────────────
# RenewablesAndPolicy.yaml transformations
# ─────────────────────────────────────────────────────────────────────────────
MPVAR_MULTIPLIER = 0.75  # 25% reduction in MPVAR reference price

def transform_no_support(yaml_text):
    """Zero out all FIT TsFit values and MPVAR Lcoe values in SupportPolicy."""
    # Zero FIT TsFit values (e.g., TsFit: 120.0 -> TsFit: 0.0)
    yaml_text = re.sub(r'(TsFit:\s*)\d+\.?\d*', r'\g<1>0.0', yaml_text)
    # Zero MPVAR Lcoe values (e.g., Lcoe: 97.21 -> Lcoe: 0.0)
    yaml_text = re.sub(r'(Lcoe:\s*)\d+\.?\d*', r'\g<1>0.0', yaml_text)
    return yaml_text


def transform_mpvar_reduced(yaml_text):
    """Multiply all MPVAR Lcoe values by MPVAR_MULTIPLIER; leave FIT TsFit unchanged."""
    def replace_lcoe(m):
        orig = float(m.group(2))
        new  = round(orig * MPVAR_MULTIPLIER, 2)
        return f"{m.group(1)}{new}"
    yaml_text = re.sub(r'(Lcoe:\s*)(\d+\.?\d*)', replace_lcoe, yaml_text)
    return yaml_text


# ─────────────────────────────────────────────────────────────────────────────
# Directory creation helpers
# ─────────────────────────────────────────────────────────────────────────────
def copy_config(src, dst, run_id):
    """Deep-copy a scenario config directory, updating scenario.yaml runId."""
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

    # Update runId in scenario.yaml
    sc_path = os.path.join(dst, "scenario.yaml")
    with open(sc_path) as f:
        text = f.read()
    text = re.sub(r'(runId:\s*")[^"]*(")', f'\\g<1>{run_id}\\g<2>', text)
    with open(sc_path, "w") as f:
        f.write(text)
    print(f"  Created {os.path.basename(dst)}/ with runId={run_id}")


def apply_policy_transform(config_dir, transform_fn):
    """Apply a transformation function to agents/RenewablesAndPolicy.yaml."""
    yaml_path = os.path.join(config_dir, "agents", "RenewablesAndPolicy.yaml")
    with open(yaml_path) as f:
        text = f.read()
    text = transform_fn(text)
    with open(yaml_path, "w") as f:
        f.write(text)


def set_co2_price(config_dir, price):
    """Replace timeseries/co2_price.csv with a constant CO2 price."""
    co2_path = os.path.join(config_dir, "timeseries", "co2_price.csv")
    write_constant_co2(co2_path, price)
    print(f"  Set CO2 = {price:.1f} EUR/t in {os.path.basename(config_dir)}/timeseries/co2_price.csv")


# ─────────────────────────────────────────────────────────────────────────────
# Create the 5 missing scenario configs
# ─────────────────────────────────────────────────────────────────────────────
scenarios = [
    {
        "dst": f"{PROJECT}/no_support_high_co2_config",
        "src": G2019,
        "run_id": "Germany2019_NoSupport_HighCO2",
        "policy_fn": transform_no_support,
        "co2": CO2_HIGH,
        "output": "no_support_high_co2",
    },
    {
        "dst": f"{PROJECT}/mpvar_reduced_low_co2_config",
        "src": G2019,
        "run_id": "Germany2019_MPVARReduced_LowCO2",
        "policy_fn": transform_mpvar_reduced,
        "co2": CO2_LOW,
        "output": "mpvar_reduced_low_co2",
    },
    {
        "dst": f"{PROJECT}/mpvar_reduced_high_co2_config",
        "src": G2019,
        "run_id": "Germany2019_MPVARReduced_HighCO2",
        "policy_fn": transform_mpvar_reduced,
        "co2": CO2_HIGH,
        "output": "mpvar_reduced_high_co2",
    },
    {
        "dst": f"{PROJECT}/fit_only_low_co2_config",
        "src": FIT_BASE,
        "run_id": "Germany2019_FITOnly_LowCO2",
        "policy_fn": None,   # fit_scenario_config already correct
        "co2": CO2_LOW,
        "output": "fit_only_low_co2",
    },
    {
        "dst": f"{PROJECT}/fit_only_high_co2_config",
        "src": FIT_BASE,
        "run_id": "Germany2019_FITOnly_HighCO2",
        "policy_fn": None,
        "co2": CO2_HIGH,
        "output": "fit_only_high_co2",
    },
]

print("=" * 60)
print("Creating 5 new scenario config directories")
print("=" * 60)

for s in scenarios:
    print(f"\n[{s['output']}]")
    copy_config(s["src"], s["dst"], s["run_id"])
    if s["policy_fn"] is not None:
        apply_policy_transform(s["dst"], s["policy_fn"])
        print(f"  Applied policy transform: {s['policy_fn'].__name__}")
    set_co2_price(s["dst"], s["co2"])

print("\n" + "=" * 60)
print("All 5 config directories created.")
print("=" * 60)
print("\nTo run simulations:")
print("  source amiris-env/bin/activate")
for s in scenarios:
    dst = s["dst"].replace(PROJECT + "/", "")
    out = s["output"]
    print(f"  amiris run --scenario ./{dst}/scenario.yaml --output {out}")
