"""Exploratory association checks for the RQ1 candidate-edge universe."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats


NUMERIC_EDGE_PAIRS = [
    ("app_popularity_encoded", "apk_size_scaled"),
    ("app_popularity_encoded", "reporting_policy"),
    ("app_popularity_encoded", "verdict"),
    ("apk_size_scaled", "reporting_policy"),
    ("apk_size_scaled", "verdict"),
    ("reporting_policy", "verdict"),
    ("reporting_policy", "reported_alert_is_third_party"),
    ("app_popularity_encoded", "reported_alert_is_third_party"),
    ("apk_size_scaled", "reported_alert_is_third_party"),
    ("reported_alert_is_third_party", "verdict"),
]


def _benjamini_hochberg(p_values: list[float]):
    count = len(p_values)
    order = np.argsort(p_values)
    adjusted = np.empty(count, dtype=float)
    running = 1.0
    for rank_from_end, index in enumerate(order[::-1], start=1):
        rank = count - rank_from_end + 1
        running = min(running, p_values[index] * count / rank)
        adjusted[index] = running
    return adjusted.clip(0, 1).tolist()


def _cramers_v(table: pd.DataFrame, chi2: float):
    n = table.to_numpy().sum()
    if n == 0:
        return math.nan
    rows, cols = table.shape
    denominator = min(rows - 1, cols - 1)
    return math.sqrt((chi2 / n) / denominator) if denominator > 0 else math.nan


def run_association_checks(data: pd.DataFrame, alpha: float = 0.06):
    """Run two-sided, unadjusted checks and control FDR within each tool.

    These tests are deliberately symmetric: their results must not be used to
    orient an edge. They only describe whether a marginal association is visible
    in the policy-expanded alert table.
    """

    rows: list[dict[str, object]] = []
    for left, right in NUMERIC_EDGE_PAIRS:
        statistic, p_value = stats.spearmanr(data[left], data[right])
        rows.append(
            {
                "variable_1": left,
                "variable_2": right,
                "test": "spearman_two_sided",
                "statistic": float(statistic),
                "effect_size": float(statistic),
                "p_value": float(p_value),
                "n_rows": len(data),
            }
        )

    table = pd.crosstab(data["rule_id"], data["verdict"])
    chi2, p_value, degrees_of_freedom, _ = stats.chi2_contingency(table)
    rows.append(
        {
            "variable_1": "rule_id",
            "variable_2": "verdict",
            "test": "chi_square",
            "statistic": float(chi2),
            "effect_size": _cramers_v(table, float(chi2)),
            "p_value": float(p_value),
            "degrees_of_freedom": int(degrees_of_freedom),
            "n_rows": len(data),
        }
    )

    result = pd.DataFrame(rows)
    result["q_value_bh"] = _benjamini_hochberg(result["p_value"].tolist())
    result["associated_at_alpha"] = result["q_value_bh"] < alpha
    result["interpretation"] = np.where(
        result["associated_at_alpha"],
        "marginal association detected; direction remains domain-determined",
        "no marginal association detected; this does not prove independence",
    )
    return result
