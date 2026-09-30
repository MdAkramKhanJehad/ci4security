"""RQ3 library-type contrasts with current diagnostics.

Each contrast compares a developer-only reporting condition with an inclusive
condition containing developer alerts plus one grouped library type. Every
eligible developer and selected-library alert is retained; the legacy library
grouping and pairwise contrast are preserved without legacy downsampling.
"""

from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from causal_analysis.shared.data_loading import load_reporting_policy_data
from causal_analysis.shared.rq3_analysis import (
    COVARIATES,
    ESTIMATOR_LABELS,
    OUTCOME,
    TREATMENT,
    _package_version,
    _sha256,
    apk_cluster_diagnostics,
    bootstrap_estimates,
    dowhy_estimate_suite,
    estimate_suite,
    propensity_diagnostics,
    run_refuters,
    save_overlap_plot,
    summarize_estimates,
)


BASELINE_GROUP = "App_Source_Code"
LIBRARY_GROUPS = ("Android", "Small_Libraries", "Utilities", "miscellaneous")
SMALL_LIBRARY_LOCATIONS = ("SocialMedia", "Analytics", "Cloud", "Advertising")


def load_library_type_source(path: Path):
    """Load one copy of every source alert and reproduce legacy grouping."""

    expanded, source_summary = load_reporting_policy_data(path)
    source = expanded[expanded[TREATMENT] == 1].copy().reset_index(drop=True)
    source["lib_grouped"] = source["code_location"].replace(
        list(SMALL_LIBRARY_LOCATIONS), "Small_Libraries"
    )
    source.loc[source["lib_grouped"] == "developer_written", "lib_grouped"] = (
        BASELINE_GROUP
    )
    source.loc[source["lib_grouped"] == "others", "lib_grouped"] = "miscellaneous"

    observed = set(source["lib_grouped"].dropna().astype(str))
    expected = {BASELINE_GROUP, *LIBRARY_GROUPS}
    unexpected = sorted(observed - expected)
    if unexpected:
        raise ValueError(f"Unexpected grouped library types in {path}: {unexpected}")
    missing = sorted(expected - observed)
    if missing:
        raise ValueError(f"Missing grouped library types in {path}: {missing}")
    return source, source_summary


def make_library_contrast(
    source: pd.DataFrame,
    library_type: str,
):
    """Construct one all-row, policy-expanded library contrast."""

    if library_type not in LIBRARY_GROUPS:
        raise ValueError(f"Unsupported library type: {library_type!r}")

    baseline = source[source["lib_grouped"] == BASELINE_GROUP].copy()
    library = source[source["lib_grouped"] == library_type].copy()
    if baseline.empty:
        raise ValueError("No developer-written alerts are available")
    if library.empty:
        raise ValueError(f"No alerts are available for {library_type}")

    all_rows = pd.concat([baseline, library], ignore_index=True)
    all_rows["contrast_row_id"] = np.arange(len(all_rows), dtype=int)

    inclusive = all_rows.copy()
    inclusive[TREATMENT] = 1
    inclusive["reporting_scope"] = f"developer_plus_{library_type}"
    developer_only = all_rows[all_rows["lib_grouped"] == BASELINE_GROUP].copy()
    developer_only[TREATMENT] = 0
    developer_only["reporting_scope"] = "developer_only"
    analysis = pd.concat([inclusive, developer_only], ignore_index=True)
    analysis["reported_alert_is_third_party"] = analysis["is_third_party"]
    analysis["library_contrast"] = library_type

    summary = {
        "library_type": library_type,
        "available_developer_alerts": int(len(baseline)),
        "available_library_alerts": int(len(library)),
        "included_developer_alerts": int(len(baseline)),
        "included_library_alerts": int(len(library)),
        "control_rows": int((analysis[TREATMENT] == 0).sum()),
        "inclusive_rows": int((analysis[TREATMENT] == 1).sum()),
        "analyzed_rows": int(len(analysis)),
        "unique_apks": int(analysis["apk_id"].nunique()),
        "unique_library_alerts": int(library["source_alert_id"].nunique()),
    }
    return analysis, summary


def _with_library(frame: pd.DataFrame, library_type: str):
    result = frame.copy()
    result.insert(0, "library_type", library_type)
    return result


def _direction_agreement(row: pd.Series):
    values = [row["psm"], row["logistic_regression"], row["doubly_robust"]]
    return bool(all(value > 0 for value in values) or all(value < 0 for value in values))


def _markdown_report(tool_name: str, estimator_results: pd.DataFrame, summaries: pd.DataFrame):
    pivot = estimator_results.pivot(
        index="library_type", columns="estimator", values="estimate"
    ).reindex(LIBRARY_GROUPS)
    pivot["same_direction"] = pivot.apply(_direction_agreement, axis=1)
    result_rows = []
    for library_type, row in pivot.iterrows():
        result_rows.append(
            f"| {library_type} | {row.psm:.4f} | {row.logistic_regression:.4f} | "
            f"{row.doubly_robust:.4f} | {'Yes' if row.same_direction else 'No / mixed'} |"
        )

    inclusion_rows = []
    for row in summaries.itertuples(index=False):
        inclusion_rows.append(
            f"| {row.library_type} | {row.included_developer_alerts:,} | "
            f"{row.included_library_alerts:,} | {row.control_rows:,} | "
            f"{row.inclusive_rows:,} |"
        )

    return f"""# {tool_name}: RQ3 library-type results

## Analysis definition

Each row compares developer-only reporting with reporting developer alerts plus
one grouped library type. The construction preserves the legacy grouping and
pairwise policy contrast while retaining every eligible source row. It
estimates alert-row ATE risk differences with PSM, standardized logistic
regression, and doubly robust AIPW.

| Library type | PSM ATE | Logistic ATE | Doubly robust AIPW ATE | Same direction? |
|---|---:|---:|---:|---|
{chr(10).join(result_rows)}

## Row inclusion

| Library type | Included developer alerts | Included library alerts | Control rows | Inclusive rows |
|---|---:|---:|---:|---|
{chr(10).join(inclusion_rows)}

For every contrast, the inclusive policy contains the developer alerts and the
selected library alerts, while the control policy repeats the developer alerts.
No eligible source alert is sampled out, and no source alert is duplicated by
resampling.

## Diagnostics and robustness outputs

The aggregate CSV files in this directory contain propensity overlap, balance,
matching diagnostics, row and APK-cluster bootstrap intervals, all bootstrap
replicates, software validation, and five refuters for every estimator and
library contrast. The four SVG files show propensity overlap separately for
each contrast.

These are all-row alert-set reporting contrasts. They do not estimate the
effect of modifying the SAST engine to analyze a different set of code.
"""


def run_rq3_library_type_analysis(
    tool_name: str,
    source_path: Path,
    output_dir: Path,
    bootstrap_simulations: int = 1000,
    refuter_simulations: int = 200,
    seed: int = 20260915,
):
    """Run and persist all four all-row library-type contrasts."""

    output_dir.mkdir(parents=True, exist_ok=True)
    source, source_summary = load_library_type_source(source_path)
    collected: dict[str, list[pd.DataFrame]] = {
        "overlap": [],
        "balance": [],
        "matching": [],
        "estimator_results": [],
        "bootstrap": [],
        "refuters": [],
        "software_validation": [],
        "cluster_diagnostics": [],
        "propensity_scores": [],
    }
    summary_rows = []

    for library_index, library_type in enumerate(LIBRARY_GROUPS):
        contrast_seed = seed + library_index
        data, contrast_summary = make_library_contrast(source, library_type)
        summary_rows.append(contrast_summary)

        scores, overlap, balance, matching = propensity_diagnostics(data)
        save_overlap_plot(
            scores,
            output_dir / f"propensity_overlap_{library_type.lower()}.svg",
            f"{tool_name}: {library_type}",
        )
        model, estimand, dowhy_estimates = dowhy_estimate_suite(data)
        point_estimates = {
            name: float(estimate.value) for name, estimate in dowhy_estimates.items()
        }
        independent = estimate_suite(data)
        validation_rows = []
        for estimator in ESTIMATOR_LABELS:
            difference = independent[estimator] - point_estimates[estimator]
            validation_rows.append(
                {
                    "estimator": estimator,
                    "dowhy_estimate": point_estimates[estimator],
                    "independent_implementation_estimate": independent[estimator],
                    "difference": difference,
                    "agrees_within_1e_8": abs(difference) < 1e-8,
                }
            )
        software_validation = pd.DataFrame(validation_rows)
        if not software_validation["agrees_within_1e_8"].all():
            raise RuntimeError(
                f"Independent estimators do not reproduce DoWhy for {library_type}"
            )

        bootstrap = bootstrap_estimates(data, bootstrap_simulations, contrast_seed)
        estimator_results = summarize_estimates(point_estimates, bootstrap)
        cluster_diagnostics = apk_cluster_diagnostics(data)
        refuters = run_refuters(
            model,
            estimand,
            dowhy_estimates,
            simulations=refuter_simulations,
            seed=contrast_seed,
        )

        for key, frame in (
            ("propensity_scores", scores),
            ("overlap", overlap),
            ("balance", balance),
            ("matching", matching),
            ("estimator_results", estimator_results),
            ("bootstrap", bootstrap),
            ("refuters", refuters),
            ("software_validation", software_validation),
            ("cluster_diagnostics", cluster_diagnostics),
        ):
            collected[key].append(_with_library(frame, library_type))

    combined = {
        key: pd.concat(frames, ignore_index=True) for key, frames in collected.items()
    }
    summaries = pd.DataFrame(summary_rows)
    filenames = {
        "propensity_scores": "propensity_scores.csv",
        "overlap": "overlap_summary.csv",
        "balance": "balance.csv",
        "matching": "matching_diagnostics.csv",
        "estimator_results": "estimator_results.csv",
        "bootstrap": "bootstrap_estimates.csv",
        "refuters": "refuter_results.csv",
        "software_validation": "software_validation.csv",
        "cluster_diagnostics": "apk_cluster_diagnostics.csv",
    }
    for key, filename in filenames.items():
        combined[key].to_csv(output_dir / filename, index=False)
    summaries.to_csv(output_dir / "contrast_summary.csv", index=False)

    metadata = {
        "tool": tool_name,
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "source_csv": str(source_path),
        "source_sha256": _sha256(source_path),
        "library_groups": list(LIBRARY_GROUPS),
        "small_library_locations": list(SMALL_LIBRARY_LOCATIONS),
        "baseline_group": BASELINE_GROUP,
        "row_inclusion": (
            "retain every eligible developer alert and every alert in the "
            "selected library group; perform no category downsampling"
        ),
        "bootstrap_simulations_per_contrast": bootstrap_simulations,
        "refuter_simulations_where_applicable": refuter_simulations,
        "contrast_seed_base": seed,
        "treatment": TREATMENT,
        "outcome": OUTCOME,
        "adjustment_variables": COVARIATES,
        "target_units": "ate",
        "effect_scale": "risk_difference",
        "source_dataset_summary": source_summary.__dict__,
        "python": platform.python_version(),
        "packages": {
            name: _package_version(name)
            for name in (
                "dowhy",
                "numpy",
                "pandas",
                "scikit-learn",
                "scipy",
                "statsmodels",
            )
        },
    }
    (output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    report = _markdown_report(tool_name, combined["estimator_results"], summaries)
    (output_dir / "RQ3_LIBRARY_TYPES_RESULTS.md").write_text(report, encoding="utf-8")
    return {
        **combined,
        "contrast_summary": summaries,
        "output_dir": output_dir,
    }
