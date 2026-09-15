"""Load the four alert datasets using one documented reporting-policy transform."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


POPULARITY_ORDER = [
    "<100",
    "100-500",
    "500-1k",
    "1k-5k",
    "5k-10k",
    "10k-50k",
    "50k-100k",
    "100k-500k",
    "500k-1M",
    "1M-5M",
    ">5M",
]

REQUIRED_COLUMNS = {
    "verdict",
    "app_package_name",
    "version_code",
    "apk_size",
    "apk_category",
    "code_location",
}


@dataclass(frozen=True)
class DatasetSummary:
    raw_alerts: int
    analyzed_alert_rows: int
    developer_alerts: int
    third_party_alerts: int
    apks: int


def _normalise_verdict(value: object):
    normalised = str(value).strip().lower()
    if normalised in {"true", "1"}:
        return 1
    if normalised in {"false", "0"}:
        return 0
    raise ValueError(f"Unsupported verdict value: {value!r}")


def _robust_scale(series: pd.Series):
    median = float(series.median())
    q1, q3 = series.quantile([0.25, 0.75])
    iqr = float(q3 - q1)
    if iqr == 0:
        return series.astype(float) - median
    return (series.astype(float) - median) / iqr


def load_reporting_policy_data(path: Path):
    """Return the alert-level policy table used by the existing binary analyses.

    ``reporting_policy=1`` reports developer-written and third-party alerts.
    ``reporting_policy=0`` reports developer-written alerts only. Consequently,
    every developer-written alert appears in both policy arms and each
    third-party alert appears only in the inclusive arm. This function preserves
    that intentional operationalisation exactly; it does not reinterpret the
    treatment as alert provenance.
    """

    source = pd.read_csv(path)
    missing = REQUIRED_COLUMNS.difference(source.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")

    source = source.copy()
    source = source[~source["code_location"].astype(str).str.contains("obfuscated", case=False, na=False)].copy()
    source["verdict"] = source["verdict"].map(_normalise_verdict)
    source["apk_size"] = pd.to_numeric(source["apk_size"], errors="raise")
    source["app_popularity"] = source["apk_category"].astype(str).str.strip()
    unknown = sorted(set(source["app_popularity"]) - set(POPULARITY_ORDER))
    if unknown:
        raise ValueError(f"Unknown popularity buckets in {path}: {unknown}")

    source["app_popularity_encoded"] = pd.Categorical(
        source["app_popularity"], categories=POPULARITY_ORDER, ordered=True
    ).codes.astype(int)
    source["apk_size_scaled"] = _robust_scale(source["apk_size"])
    source["is_third_party"] = (source["code_location"] != "developer_written").astype(int)
    rule_column = "rule_id" if "rule_id" in source.columns else "ruleId"
    if rule_column not in source.columns:
        raise ValueError(f"{path} has neither rule_id nor ruleId")
    source["rule_id"] = source[rule_column].astype(str).str.strip()
    source["source_alert_id"] = np.arange(len(source), dtype=int)
    source["apk_id"] = source["app_package_name"].astype(str) + "::" + source["version_code"].astype(str)

    inclusive = source.copy()
    inclusive["reporting_policy"] = 1
    inclusive["reporting_scope"] = "developer_plus_third_party"
    developer_only = source[source["code_location"] == "developer_written"].copy()
    developer_only["reporting_policy"] = 0
    developer_only["reporting_scope"] = "developer_only"
    analysis = pd.concat([inclusive, developer_only], ignore_index=True)
    analysis["reported_alert_is_third_party"] = analysis["is_third_party"]

    if analysis[["reporting_policy", "verdict", "app_popularity_encoded", "apk_size_scaled"]].isna().any().any():
        raise ValueError(f"Missing values remain in the four graph variables for {path}")

    summary = DatasetSummary(
        raw_alerts=len(source),
        analyzed_alert_rows=len(analysis),
        developer_alerts=int((source["code_location"] == "developer_written").sum()),
        third_party_alerts=int((source["code_location"] != "developer_written").sum()),
        apks=int(source["apk_id"].nunique()),
    )
    return analysis, summary


GRAPH_COLUMNS = [
    "app_popularity_encoded",
    "apk_size_scaled",
    "reporting_policy",
    "reported_alert_is_third_party",
    "verdict",
]
