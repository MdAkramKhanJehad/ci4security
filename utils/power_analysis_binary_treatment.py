#!/usr/bin/env python3

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize


REPO_ROOT = Path(__file__).resolve().parents[1]

CODEQL_INPUT = REPO_ROOT / "causal_analysis_codeql" / "alerts_with_lib_category_and_apk_size_codeql.csv"
SEMGREP_INPUT = REPO_ROOT / "causal_analysis_semgrep" / "alerts_with_lib_category_and_apk_size_semgrep.csv"
CRYPTOGUARD_INPUT = REPO_ROOT / "causal_analysis_cryptoguard" / "alerts_with_lib_category_and_apk_size_cryptoguard.csv"
COGNICRYPT_INPUT = REPO_ROOT / "causal_analysis_cognicrypt" / "alerts_with_lib_category_and_apk_size_cognicrypt.csv"

ACTIVE_INPUTS = {
    "CodeQL": CODEQL_INPUT,
    "Semgrep": SEMGREP_INPUT,
    "CryptoGuard": CRYPTOGUARD_INPUT,
    "CogniCrypt": COGNICRYPT_INPUT,
}

# To run one tool only, comment out the others above, for example:
# ACTIVE_INPUTS = {"Semgrep": SEMGREP_INPUT}


def normalize_verdict(value):
    normalized = str(value).strip().lower()
    if normalized in {"1", "true"}:
        return 1
    if normalized in {"0", "false"}:
        return 0
    raise ValueError(f"Unsupported verdict value: {value!r}")


def load_and_preprocess(path):
    df = pd.read_csv(path)
    df = df[~df["code_location"].str.contains("obfuscated", case=False, na=False)].copy()
    df["verdict"] = df["verdict"].apply(normalize_verdict)
    df["is_third_party"] = (~df["code_location"].isin(["developer_written"])).astype(int)
    return df


def compute_power(df, alpha=0.05, target_power=0.8):
    dev = df[df["is_third_party"] == 0]
    third_party = df[df["is_third_party"] == 1]

    if dev.empty or third_party.empty:
        raise ValueError("Both developer-written and third-party groups are required.")

    p_dev = dev["verdict"].mean()
    p_third = third_party["verdict"].mean()
    n_dev = len(dev)
    n_third = len(third_party)
    ratio = n_third / n_dev
    effect_size = proportion_effectsize(p_third, p_dev)

    power_analysis = NormalIndPower()
    observed_power = power_analysis.power(
        effect_size=effect_size,
        nobs1=n_dev,
        alpha=alpha,
        ratio=ratio,
        alternative="two-sided",
    )

    required_n_dev = np.nan
    required_n_third = np.nan
    if effect_size != 0:
        required_n_dev = power_analysis.solve_power(
            effect_size=effect_size,
            power=target_power,
            alpha=alpha,
            ratio=ratio,
            alternative="two-sided",
        )
        required_n_third = required_n_dev * ratio

    return {
        "n_dev": n_dev,
        "n_third_party": n_third,
        "p_dev": p_dev,
        "p_third_party": p_third,
        "difference": p_third - p_dev,
        "cohens_h": effect_size,
        "observed_power": observed_power,
        "required_n_dev_80_power": required_n_dev,
        "required_n_third_party_80_power": required_n_third,
    }


def plot_group_rates(tool_name, df):
    rates = (
        df.groupby("code_location")["verdict"]
        .agg(["count", "mean"])
        .sort_values("mean", ascending=False)
    )

    plt.figure(figsize=(10, 5))
    plt.bar(rates.index, rates["mean"])
    plt.xticks(rotation=35, ha="right")
    plt.ylabel("True-positive rate")
    plt.title(f"{tool_name}: verdict rate by code_location")
    plt.tight_layout()
    plt.show()


def plot_bootstrap_difference(tool_name, df, n_boot=2000):
    rng = np.random.default_rng(42)
    diffs = []

    for _ in range(n_boot):
        sample = df.iloc[rng.integers(0, len(df), len(df))]
        p_dev = sample.loc[sample["is_third_party"] == 0, "verdict"].mean()
        p_third = sample.loc[sample["is_third_party"] == 1, "verdict"].mean()
        if not np.isnan(p_dev) and not np.isnan(p_third):
            diffs.append(p_third - p_dev)

    diffs = np.array(diffs)
    observed = (
        df.loc[df["is_third_party"] == 1, "verdict"].mean()
        - df.loc[df["is_third_party"] == 0, "verdict"].mean()
    )

    ci_lower, ci_upper = np.percentile(diffs, [2.5, 97.5])

    plt.figure(figsize=(8, 5))
    plt.hist(diffs, bins=30, density=True, alpha=0.75)
    plt.axvline(observed, color="red", linestyle="--", linewidth=2, label="Observed difference")
    plt.axvline(ci_lower, color="gray", linestyle=":", linewidth=1, label="95% CI")
    plt.axvline(ci_upper, color="gray", linestyle=":", linewidth=1)
    plt.xlabel("TP-rate difference: third-party minus developer-written")
    plt.ylabel("Density")
    plt.title(f"{tool_name}: bootstrap TP-rate difference")
    plt.legend()
    plt.tight_layout()
    plt.show()


def plot_power_curve(tool_name, df, alpha=0.05):
    stats = compute_power(df, alpha=alpha)
    effect_size = stats["cohens_h"]
    ratio = stats["n_third_party"] / stats["n_dev"]

    if effect_size == 0:
        print(f"{tool_name}: effect size is zero; skipping power curve.")
        return

    power_analysis = NormalIndPower()
    n_grid = np.arange(20, max(620, stats["n_dev"] + 100), 20)
    powers = [
        power_analysis.power(
            effect_size=effect_size,
            nobs1=n,
            alpha=alpha,
            ratio=ratio,
            alternative="two-sided",
        )
        for n in n_grid
    ]

    plt.figure(figsize=(8, 5))
    plt.plot(n_grid, powers, marker="o")
    plt.axhline(0.8, color="gray", linestyle="--", label="80% power")
    plt.axvline(stats["n_dev"], color="red", linestyle=":", label=f"current n_dev = {stats['n_dev']}")
    plt.xlabel("Developer-written alerts; third-party ratio fixed")
    plt.ylabel("Power")
    plt.title(f"{tool_name}: power curve for TP-rate difference")
    plt.legend()
    plt.tight_layout()
    plt.show()


def analyze_tool(tool_name, path):
    print(f"\\n{'=' * 80}\\n{tool_name}\\n{path}\\n{'=' * 80}")
    df = load_and_preprocess(path)

    print("\\nis_third_party counts:")
    print(df["is_third_party"].value_counts())
    print("\\ncode_location counts:")
    print(df["code_location"].value_counts())

    stats = compute_power(df)
    print("\\nPower analysis for verdict proportion difference")
    for key, value in stats.items():
        print(f"{key}: {value}")

    plot_group_rates(tool_name, df)
    plot_bootstrap_difference(tool_name, df)
    plot_power_curve(tool_name, df)


def main():
    for tool_name, path in ACTIVE_INPUTS.items():
        analyze_tool(tool_name, path)


if __name__ == "__main__":
    main()
