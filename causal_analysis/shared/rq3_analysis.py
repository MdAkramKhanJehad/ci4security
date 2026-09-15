"""Shared RQ3 estimation, diagnostics, clustered uncertainty, and refutation code."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import platform
import warnings
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from dowhy import CausalModel
from dowhy.causal_estimators.generalized_linear_model_estimator import (
    GeneralizedLinearModelEstimator,
)
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import NearestNeighbors

from causal_analysis.shared.data_loading import load_reporting_policy_data


TREATMENT = "reporting_policy"
OUTCOME = "verdict"
COVARIATES = ["app_popularity_encoded", "apk_size_scaled"]
ESTIMATOR_LABELS = {
    "psm": "Propensity-score matching",
    "logistic_regression": "Logistic-regression adjustment",
    "doubly_robust": "Doubly robust (AIPW)",
}


def _sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_version(name: str):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def _fit_propensity(data: pd.DataFrame):
    treatment = data[TREATMENT].astype(int).to_numpy()
    if np.unique(treatment).size != 2:
        raise ValueError("Both reporting-policy conditions are required")
    model = LogisticRegression(max_iter=1000, random_state=0)
    model.fit(data[COVARIATES].astype(float), treatment)
    scores = model.predict_proba(data[COVARIATES].astype(float))[:, 1]
    return model, scores


def _fit_outcome_model(data: pd.DataFrame):
    design = sm.add_constant(
        data[[TREATMENT, *COVARIATES]].astype(float), has_constant="add"
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = sm.GLM(
            data[OUTCOME].astype(float),
            design,
            family=sm.families.Binomial(),
        ).fit(maxiter=100, disp=0)
    treated_design = design.copy()
    treated_design[TREATMENT] = 1.0
    control_design = design.copy()
    control_design[TREATMENT] = 0.0
    treated_predictions = np.asarray(model.predict(treated_design), dtype=float)
    control_predictions = np.asarray(model.predict(control_design), dtype=float)
    return model, treated_predictions, control_predictions


def _psm_ate(data: pd.DataFrame, propensity_scores: np.ndarray):
    treatment = data[TREATMENT].astype(int).to_numpy()
    outcome = data[OUTCOME].astype(float).to_numpy()
    treated_indices = np.flatnonzero(treatment == 1)
    control_indices = np.flatnonzero(treatment == 0)

    control_neighbors = NearestNeighbors(n_neighbors=1, algorithm="ball_tree").fit(
        propensity_scores[control_indices].reshape(-1, 1)
    )
    control_match_positions = control_neighbors.kneighbors(
        propensity_scores[treated_indices].reshape(-1, 1), return_distance=False
    ).ravel()
    matched_control_indices = control_indices[control_match_positions]
    att = np.mean(outcome[treated_indices] - outcome[matched_control_indices])

    treated_neighbors = NearestNeighbors(n_neighbors=1, algorithm="ball_tree").fit(
        propensity_scores[treated_indices].reshape(-1, 1)
    )
    treated_match_positions = treated_neighbors.kneighbors(
        propensity_scores[control_indices].reshape(-1, 1), return_distance=False
    ).ravel()
    matched_treated_indices = treated_indices[treated_match_positions]
    atc = np.mean(outcome[matched_treated_indices] - outcome[control_indices])

    n_treated = len(treated_indices)
    n_control = len(control_indices)
    ate = (att * n_treated + atc * n_control) / (n_treated + n_control)
    return float(ate)


def estimate_suite(data: pd.DataFrame):
    """Compute the three ATEs on the risk-difference scale."""

    _, propensity_scores = _fit_propensity(data)
    _, treated_predictions, control_predictions = _fit_outcome_model(data)
    treatment = data[TREATMENT].astype(int).to_numpy()
    outcome = data[OUTCOME].astype(float).to_numpy()
    clipped_scores = np.clip(propensity_scores, 0.01, 0.99)

    psm = _psm_ate(data, propensity_scores)
    logistic = float(np.mean(treated_predictions - control_predictions))
    aipw_scores = (
        treated_predictions
        - control_predictions
        + treatment * (outcome - treated_predictions) / clipped_scores
        - (1 - treatment) * (outcome - control_predictions) / (1 - clipped_scores)
    )
    doubly_robust = float(np.mean(aipw_scores))
    return {
        "psm": psm,
        "logistic_regression": logistic,
        "doubly_robust": doubly_robust,
    }


def dowhy_estimate_suite(data: pd.DataFrame):
    """Run the corresponding DoWhy 0.14 estimators and return their objects."""

    model = CausalModel(
        data=data.copy(),
        treatment=TREATMENT,
        outcome=OUTCOME,
        common_causes=COVARIATES,
    )
    estimand = model.identify_effect(proceed_when_unidentifiable=True)
    specifications = {
        "psm": (
            "backdoor.propensity_score_matching",
            {},
        ),
        "logistic_regression": (
            "backdoor.generalized_linear_model",
            {"glm_family": sm.families.Binomial()},
        ),
        "doubly_robust": (
            "backdoor.doubly_robust",
            {
                "propensity_score_column": "propensity_score_dr",
                "regression_estimator": GeneralizedLinearModelEstimator,
                "glm_family": sm.families.Binomial(),
                "min_ps_score": 0.01,
                "max_ps_score": 0.99,
            },
        ),
    }
    estimates = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for name, (method_name, method_params) in specifications.items():
            estimates[name] = model.estimate_effect(
                estimand,
                method_name=method_name,
                target_units="ate",
                method_params=method_params,
            )
    return model, estimand, estimates


def _weighted_mean(values: np.ndarray, weights: np.ndarray):
    return float(np.average(values, weights=weights))


def _weighted_variance(values: np.ndarray, weights: np.ndarray):
    mean = _weighted_mean(values, weights)
    return float(np.average((values - mean) ** 2, weights=weights))


def _standardized_mean_difference(values, treatment, weights=None):
    values = np.asarray(values, dtype=float)
    treatment = np.asarray(treatment, dtype=int)
    if weights is None:
        weights = np.ones(len(values), dtype=float)
    else:
        weights = np.asarray(weights, dtype=float)
    treated = treatment == 1
    control = treatment == 0
    mean_treated = _weighted_mean(values[treated], weights[treated])
    mean_control = _weighted_mean(values[control], weights[control])
    variance_treated = _weighted_variance(values[treated], weights[treated])
    variance_control = _weighted_variance(values[control], weights[control])
    denominator = math.sqrt((variance_treated + variance_control) / 2)
    if denominator == 0:
        return 0.0
    return (mean_treated - mean_control) / denominator


def propensity_diagnostics(data: pd.DataFrame):
    """Return row scores, group overlap, PSM balance, and matching diagnostics."""

    _, scores = _fit_propensity(data)
    treatment = data[TREATMENT].astype(int).to_numpy()
    treated_indices = np.flatnonzero(treatment == 1)
    control_indices = np.flatnonzero(treatment == 0)
    treated_scores = scores[treated_indices]
    control_scores = scores[control_indices]
    support_lower = max(float(treated_scores.min()), float(control_scores.min()))
    support_upper = min(float(treated_scores.max()), float(control_scores.max()))
    in_support = (scores >= support_lower) & (scores <= support_upper)

    control_neighbors = NearestNeighbors(n_neighbors=1, algorithm="ball_tree").fit(
        control_scores.reshape(-1, 1)
    )
    att_distances, att_positions = control_neighbors.kneighbors(
        treated_scores.reshape(-1, 1)
    )
    treated_neighbors = NearestNeighbors(n_neighbors=1, algorithm="ball_tree").fit(
        treated_scores.reshape(-1, 1)
    )
    atc_distances, atc_positions = treated_neighbors.kneighbors(
        control_scores.reshape(-1, 1)
    )
    matched_control_indices = control_indices[att_positions.ravel()]
    matched_treated_indices = treated_indices[atc_positions.ravel()]

    n_rows = len(data)
    matching_weights = np.zeros(n_rows, dtype=float)
    matching_weights[treated_indices] += 1 / n_rows
    matching_weights[control_indices] += 1 / n_rows
    np.add.at(matching_weights, matched_control_indices, 1 / n_rows)
    np.add.at(matching_weights, matched_treated_indices, 1 / n_rows)
    clipped_scores = np.clip(scores, 0.01, 0.99)
    aipw_weights = treatment / clipped_scores + (1 - treatment) / (1 - clipped_scores)

    balance_rows = []
    for covariate in COVARIATES:
        values = data[covariate].astype(float).to_numpy()
        before = _standardized_mean_difference(values, treatment)
        after_psm = _standardized_mean_difference(values, treatment, matching_weights)
        after_aipw = _standardized_mean_difference(values, treatment, aipw_weights)
        balance_rows.append(
            {
                "covariate": covariate,
                "smd_before": before,
                "abs_smd_before": abs(before),
                "smd_after_psm": after_psm,
                "abs_smd_after_psm": abs(after_psm),
                "balanced_after_psm_at_0_1": abs(after_psm) < 0.1,
                "smd_after_aipw_weighting": after_aipw,
                "abs_smd_after_aipw_weighting": abs(after_aipw),
                "balanced_after_aipw_weighting_at_0_1": abs(after_aipw) < 0.1,
            }
        )
    balance = pd.DataFrame(balance_rows)

    overlap_rows = []
    for policy, label in ((0, "developer_only"), (1, "developer_plus_third_party")):
        group_scores = scores[treatment == policy]
        group_support = in_support[treatment == policy]
        quantiles = np.quantile(group_scores, [0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1])
        overlap_rows.append(
            {
                "reporting_policy": policy,
                "reporting_scope": label,
                "n_rows": len(group_scores),
                "ps_min": quantiles[0],
                "ps_q01": quantiles[1],
                "ps_q05": quantiles[2],
                "ps_q25": quantiles[3],
                "ps_median": quantiles[4],
                "ps_q75": quantiles[5],
                "ps_q95": quantiles[6],
                "ps_q99": quantiles[7],
                "ps_max": quantiles[8],
                "common_support_lower": support_lower,
                "common_support_upper": support_upper,
                "n_outside_common_support": int((~group_support).sum()),
                "percent_outside_common_support": float((~group_support).mean() * 100),
                "n_extreme_ps_below_0_1_or_above_0_9": int(
                    ((group_scores < 0.1) | (group_scores > 0.9)).sum()
                ),
            }
        )
    overlap = pd.DataFrame(overlap_rows)

    clipped = np.clip(scores, 1e-8, 1 - 1e-8)
    logits = np.log(clipped / (1 - clipped))
    caliper = 0.2 * float(np.std(logits, ddof=1))
    att_logit_distances = np.abs(logits[treated_indices] - logits[matched_control_indices])
    atc_logit_distances = np.abs(logits[matched_treated_indices] - logits[control_indices])
    treated_weights = matching_weights[treatment == 1]
    control_weights = matching_weights[treatment == 0]
    matching = pd.DataFrame(
        [
            {
                "n_treated_rows": len(treated_indices),
                "n_control_rows": len(control_indices),
                "common_support_lower": support_lower,
                "common_support_upper": support_upper,
                "n_rows_outside_common_support": int((~in_support).sum()),
                "percent_rows_outside_common_support": float((~in_support).mean() * 100),
                "matching_with_replacement": True,
                "unmatched_rows": 0,
                "unique_controls_used_for_att": int(np.unique(matched_control_indices).size),
                "unique_treated_used_for_atc": int(np.unique(matched_treated_indices).size),
                "mean_att_propensity_distance": float(att_distances.mean()),
                "max_att_propensity_distance": float(att_distances.max()),
                "mean_atc_propensity_distance": float(atc_distances.mean()),
                "max_atc_propensity_distance": float(atc_distances.max()),
                "diagnostic_logit_caliper_0_2_sd": caliper,
                "att_pairs_above_diagnostic_caliper": int((att_logit_distances > caliper).sum()),
                "atc_pairs_above_diagnostic_caliper": int((atc_logit_distances > caliper).sum()),
                "treated_effective_sample_size": float(
                    treated_weights.sum() ** 2 / np.square(treated_weights).sum()
                ),
                "control_effective_sample_size": float(
                    control_weights.sum() ** 2 / np.square(control_weights).sum()
                ),
                "aipw_treated_effective_sample_size": float(
                    aipw_weights[treated_indices].sum() ** 2
                    / np.square(aipw_weights[treated_indices]).sum()
                ),
                "aipw_control_effective_sample_size": float(
                    aipw_weights[control_indices].sum() ** 2
                    / np.square(aipw_weights[control_indices]).sum()
                ),
                "n_propensity_scores_clipped_at_0_01_or_0_99": int(
                    ((scores < 0.01) | (scores > 0.99)).sum()
                ),
            }
        ]
    )

    scores_frame = data[
        [
            "source_alert_id",
            "apk_id",
            TREATMENT,
            "reporting_scope",
            OUTCOME,
            *COVARIATES,
        ]
    ].copy()
    scores_frame["propensity_score"] = scores
    scores_frame["in_common_support"] = in_support
    scores_frame["psm_ate_weight"] = matching_weights
    scores_frame["aipw_ate_weight"] = aipw_weights
    return scores_frame, overlap, balance, matching


def save_overlap_plot(scores: pd.DataFrame, output_path: Path, tool_name: str):
    fig, axis = plt.subplots(figsize=(7.2, 4.4))
    bins = np.linspace(0, 1, 31)
    for policy, label, color in (
        (0, "Developer only", "#2563eb"),
        (1, "Developer + third-party", "#d97706"),
    ):
        values = scores.loc[scores[TREATMENT] == policy, "propensity_score"]
        axis.hist(values, bins=bins, density=True, alpha=0.5, label=label, color=color)
    axis.set(xlabel="Estimated propensity score", ylabel="Density", title=f"{tool_name}: propensity-score overlap")
    axis.set_xlim(0, 1)
    axis.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output_path, format="svg")
    plt.close(fig)


def _row_bootstrap_sample(data: pd.DataFrame, rng: np.random.Generator):
    sampled_positions = []
    groups = data.groupby(["app_popularity_encoded", TREATMENT], sort=False).indices
    for positions in groups.values():
        positions = np.asarray(positions, dtype=int)
        sampled_positions.append(rng.choice(positions, size=len(positions), replace=True))
    return data.iloc[np.concatenate(sampled_positions)].reset_index(drop=True)


def _cluster_sampling_plan(data: pd.DataFrame):
    cluster_rows = {
        apk_id: np.asarray(positions, dtype=int)
        for apk_id, positions in data.groupby("apk_id", sort=False).indices.items()
    }
    cluster_table = apk_cluster_diagnostics(data)
    strata = {
        stratum: group["apk_id"].to_numpy()
        for stratum, group in cluster_table.groupby("bootstrap_stratum", sort=False)
    }
    return cluster_rows, strata


def apk_cluster_diagnostics(data: pd.DataFrame):
    """Describe popularity strata used to resample whole APK clusters."""

    records = []
    for apk_id, group in data.groupby("apk_id", sort=False):
        values = sorted(group["app_popularity_encoded"].astype(int).unique())
        stratum = (
            f"popularity_{values[0]}"
            if len(values) == 1
            else "mixed_" + "_".join(str(value) for value in values)
        )
        records.append(
            {
                "apk_id": apk_id,
                "popularity_values": "|".join(str(value) for value in values),
                "n_popularity_values": len(values),
                "bootstrap_stratum": stratum,
                "n_policy_expanded_rows": len(group),
            }
        )
    return pd.DataFrame(records)


def _cluster_bootstrap_sample(data, rng, cluster_rows, strata):
    sampled_positions = []
    for apk_ids in strata.values():
        sampled_apks = rng.choice(apk_ids, size=len(apk_ids), replace=True)
        sampled_positions.extend(cluster_rows[apk_id] for apk_id in sampled_apks)
    return data.iloc[np.concatenate(sampled_positions)].reset_index(drop=True)


def bootstrap_estimates(data: pd.DataFrame, simulations: int, seed: int):
    """Compare row and popularity-stratified APK-cluster bootstrap estimates."""

    rng = np.random.default_rng(seed)
    cluster_rows, strata = _cluster_sampling_plan(data)
    rows = []
    for replicate in range(simulations):
        samples = {
            "row": _row_bootstrap_sample(data, rng),
            "apk_cluster": _cluster_bootstrap_sample(data, rng, cluster_rows, strata),
        }
        for resampling_unit, sample in samples.items():
            try:
                estimates = estimate_suite(sample)
                for estimator, value in estimates.items():
                    rows.append(
                        {
                            "replicate": replicate,
                            "resampling_unit": resampling_unit,
                            "estimator": estimator,
                            "estimate": value,
                            "status": "success",
                            "error": None,
                        }
                    )
            except Exception as error:
                for estimator in ESTIMATOR_LABELS:
                    rows.append(
                        {
                            "replicate": replicate,
                            "resampling_unit": resampling_unit,
                            "estimator": estimator,
                            "estimate": math.nan,
                            "status": "failed",
                            "error": f"{type(error).__name__}: {error}",
                        }
                    )
    return pd.DataFrame(rows)


def summarize_estimates(point_estimates: dict, bootstrap: pd.DataFrame):
    rows = []
    for estimator, label in ESTIMATOR_LABELS.items():
        record = {
            "estimator": estimator,
            "estimator_label": label,
            "effect_scale": "risk_difference",
            "target_units": "ate",
            "estimate": float(point_estimates[estimator]),
        }
        for unit in ("row", "apk_cluster"):
            subset = bootstrap[
                (bootstrap["estimator"] == estimator)
                & (bootstrap["resampling_unit"] == unit)
                & (bootstrap["status"] == "success")
            ]["estimate"].dropna()
            prefix = "row" if unit == "row" else "cluster"
            if len(subset) == 0:
                record.update(
                    {
                        f"{prefix}_bootstrap_successes": 0,
                        f"{prefix}_bootstrap_se": math.nan,
                        f"{prefix}_ci_low": math.nan,
                        f"{prefix}_ci_high": math.nan,
                        f"{prefix}_ci_width": math.nan,
                        f"{prefix}_ci_excludes_zero": False,
                    }
                )
            else:
                low, high = np.quantile(subset, [0.025, 0.975])
                record.update(
                    {
                        f"{prefix}_bootstrap_successes": len(subset),
                        f"{prefix}_bootstrap_se": float(subset.std(ddof=1)),
                        f"{prefix}_ci_low": float(low),
                        f"{prefix}_ci_high": float(high),
                        f"{prefix}_ci_width": float(high - low),
                        f"{prefix}_ci_excludes_zero": bool(low > 0 or high < 0),
                    }
                )
        rows.append(record)
    return pd.DataFrame(rows)


def _scalar(value):
    if value is None:
        return math.nan
    array = np.asarray(value, dtype=float)
    if array.size == 0:
        return math.nan
    return float(array.mean())


def run_refuters(model, estimand, estimates, simulations: int, seed: int):
    """Run the four legacy refuters plus unobserved-common-cause sensitivity."""

    refuter_specs = [
        ("random_common_cause", {"random_state": seed}),
        (
            "placebo_treatment_refuter",
            {
                "placebo_type": "permute",
                "num_simulations": simulations,
                "random_state": seed,
            },
        ),
        (
            "data_subset_refuter",
            {
                "subset_fraction": 0.8,
                "num_simulations": simulations,
                "random_state": seed,
            },
        ),
        (
            "dummy_outcome_refuter",
            {"num_simulations": simulations, "random_state": seed},
        ),
        (
            "add_unobserved_common_cause",
            {
                "simulation_method": "direct-simulation",
                "confounders_effect_on_treatment": "binary_flip",
                "confounders_effect_on_outcome": "binary_flip",
                "effect_strength_on_treatment": 0.05,
                "effect_strength_on_outcome": 0.05,
                "plotmethod": None,
            },
        ),
    ]
    rows = []
    for estimator_index, (estimator, estimate) in enumerate(estimates.items()):
        original_effect = float(estimate.value)
        for refuter_index, (method, parameters) in enumerate(refuter_specs):
            call_seed = seed + estimator_index * 100 + refuter_index
            np.random.seed(call_seed)
            call_parameters = parameters.copy()
            if method == "data_subset_refuter":
                # DoWhy 0.14 forwards an integer unchanged to every pandas
                # sample call, which repeats one subset. A stateful generator
                # yields distinct but reproducible subsets when n_jobs=1.
                call_parameters["random_state"] = np.random.RandomState(call_seed)
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    result = model.refute_estimate(
                        estimand,
                        estimate,
                        method_name=method,
                        **call_parameters,
                    )
                result_items = result if isinstance(result, list) else [result]
                for result_index, item in enumerate(result_items):
                    refutation_result = getattr(item, "refutation_result", None) or {}
                    new_effect = _scalar(getattr(item, "new_effect", None))
                    rows.append(
                        {
                            "estimator": estimator,
                            "refuter": method,
                            "result_index": result_index,
                            "original_effect": original_effect,
                            "refuter_reference_effect": _scalar(
                                getattr(item, "estimated_effect", original_effect)
                            ),
                            "new_effect": new_effect,
                            "absolute_change_from_original": abs(new_effect - original_effect),
                            "relative_change_from_original": (
                                abs(new_effect - original_effect) / abs(original_effect)
                                if original_effect != 0
                                else math.nan
                            ),
                            "sign_changed_from_original": bool(
                                np.isfinite(new_effect)
                                and original_effect != 0
                                and np.sign(new_effect) != np.sign(original_effect)
                            ),
                            "p_value": _scalar(refutation_result.get("p_value")),
                            "refuter_reports_significant_change": refutation_result.get(
                                "is_statistically_significant"
                            ),
                            "status": "success",
                            "error": None,
                        }
                    )
            except Exception as error:
                rows.append(
                    {
                        "estimator": estimator,
                        "refuter": method,
                        "result_index": 0,
                        "original_effect": original_effect,
                        "refuter_reference_effect": math.nan,
                        "new_effect": math.nan,
                        "absolute_change_from_original": math.nan,
                        "relative_change_from_original": math.nan,
                        "sign_changed_from_original": False,
                        "p_value": math.nan,
                        "refuter_reports_significant_change": None,
                        "status": "failed",
                        "error": f"{type(error).__name__}: {error}",
                    }
                )
    return pd.DataFrame(rows)


def _format_number(value, digits=4):
    if value is None or not np.isfinite(float(value)):
        return "NA"
    return f"{float(value):.{digits}f}"


def _markdown_report(
    tool_name,
    source_path,
    graph_path,
    summary,
    overlap,
    balance,
    matching,
    estimator_results,
    refuters,
    cluster_diagnostics,
    bootstrap_simulations,
    refuter_simulations,
):
    overlap_rows = []
    for row in overlap.itertuples(index=False):
        overlap_rows.append(
            f"| {row.reporting_scope} | {row.n_rows:,} | "
            f"{row.ps_min:.4f}–{row.ps_max:.4f} | "
            f"{row.n_outside_common_support:,} ({row.percent_outside_common_support:.2f}%) |"
        )
    balance_rows = []
    for row in balance.itertuples(index=False):
        balance_rows.append(
            f"| `{row.covariate}` | {row.smd_before:.4f} | "
            f"{row.smd_after_psm:.4f} | "
            f"{row.smd_after_aipw_weighting:.4f} |"
        )
    estimator_rows = []
    for row in estimator_results.itertuples(index=False):
        estimator_rows.append(
            f"| {row.estimator_label} | {row.estimate:.4f} | "
            f"[{row.row_ci_low:.4f}, {row.row_ci_high:.4f}] | "
            f"[{row.cluster_ci_low:.4f}, {row.cluster_ci_high:.4f}] | "
            f"{row.row_ci_width:.4f} | {row.cluster_ci_width:.4f} |"
        )
    refuter_rows = []
    for row in refuters.itertuples(index=False):
        significant_value = row.refuter_reports_significant_change
        significant_change = (
            "NA"
            if pd.isna(significant_value)
            else str(bool(significant_value))
        )
        refuter_rows.append(
            f"| {ESTIMATOR_LABELS.get(row.estimator, row.estimator)} | `{row.refuter}` | "
            f"{_format_number(row.new_effect)} | {_format_number(row.p_value)} | "
            f"{significant_change} | {str(row.status)} |"
        )
    match = matching.iloc[0]
    conflicting_clusters = int((cluster_diagnostics["n_popularity_values"] > 1).sum())
    cluster_note = (
        "Every APK has one popularity stratum."
        if conflicting_clusters == 0
        else f"{conflicting_clusters} APK has conflicting popularity values in the input. "
        "It is retained as one complete cluster in a disclosed composite stratum; "
        "see `apk_cluster_diagnostics.csv`."
    )
    return f"""# {tool_name}: RQ3 results

## Analysis definition

- Dataset: `{source_path}`
- Treatment: `reporting_policy` (`0` = developer-only; `1` = developer plus third-party)
- Outcome: binary `verdict`; all reported effects are ATE risk differences
- Adjustment variables: `app_popularity_encoded`, `apk_size_scaled`
- Alert-level rows: {summary.analyzed_alert_rows:,}
- Unique APKs: {summary.apks:,}
- Bootstrap simulations per uncertainty method: {bootstrap_simulations}
- Refuter simulations where applicable: {refuter_simulations}
- Causal graph: `{graph_path}`

Developer-written alerts are shared across both policy conditions, and
third-party alerts occur only in the inclusive condition, matching the legacy
binary-treatment construction.

## 1. Overlap and post-matching balance

The propensity model predicts reporting policy from app popularity and APK
size. Common support is the intersection of the observed propensity-score
ranges in the two policy conditions.

| Policy condition | Rows | Propensity range | Outside common support |
|---|---:|---:|---:|
{chr(10).join(overlap_rows)}

Nearest-neighbor PSM uses replacement, as in DoWhy's legacy-compatible ATE
implementation. It leaves no row formally unmatched. As a match-quality
diagnostic, {int(match.att_pairs_above_diagnostic_caliper)} treated-to-control
pairs and {int(match.atc_pairs_above_diagnostic_caliper)} control-to-treated
pairs exceed a 0.2-SD logit-propensity caliper. These pairs are reported rather
than silently discarded.

| Covariate | SMD before | SMD after PSM | SMD after AIPW weighting |
|---|---:|---:|---:|
{chr(10).join(balance_rows)}

Absolute SMD below 0.1 is used as a descriptive balance threshold. See
`balance.csv` for the absolute values and threshold flags. The AIPW column
diagnoses the inverse-propensity-weighted component of the doubly robust
estimator; it is not a separate effect estimate.

## 2. Effect estimates and uncertainty

All estimators target the same alert-row ATE on the risk-difference scale. The
logistic estimate is obtained by standardizing binomial-model predictions under
both policies. The doubly robust estimate uses the same binomial outcome model
and a logistic propensity model in an augmented inverse-probability-weighted
estimator.

| Estimator | ATE | Row-bootstrap 95% CI | APK-cluster-bootstrap 95% CI | Row width | Cluster width |
|---|---:|---:|---:|---:|---:|
{chr(10).join(estimator_rows)}

The row bootstrap resamples individual alert rows within popularity-policy
strata. The clustered bootstrap resamples complete APKs within popularity
strata and retains every selected APK's rows across both policy conditions.
{cluster_note}

## 3. Refutation and sensitivity checks

The four legacy checks are retained: random common cause, placebo treatment,
data subset, and dummy outcome. The `add_unobserved_common_cause` check is added
using direct simulation with 0.05 binary-flip strength on both treatment and
outcome. Its result is a sensitivity scenario, not proof that unmeasured
confounding is absent.

| Estimator | Refuter | New effect | p-value | Significant refuter change | Execution status |
|---|---|---:|---:|---:|---|
{chr(10).join(refuter_rows)}

Complete refuter diagnostics, including relative changes, sign changes, and
errors, are stored in `refuter_results.csv`.
`success` means that the refuter executed; it does not mean that the estimate
passed the refuter. The significant-change column records DoWhy's test result
where that refuter supplies one.

## Interpretation boundary

- PSM, regression, and doubly robust estimation use the same treatment,
  outcome, adjustment variables, target population, and risk-difference scale.
- Developer-alert duplication and multiple alerts per APK make row-independent
  intervals optimistic when within-APK dependence is material.
- The APK-cluster bootstrap addresses uncertainty from that dependence but does
  not change the alert-level estimand or repair structural treatment overlap.
- Refuters test sensitivity to specific perturbations; passing them does not
  establish that the causal assumptions are true.
- The report preserves the legacy reporting-policy operationalization. Results
  should be interpreted as the effect of changing the reported alert set, not
  as an intervention on the SAST engine's method-level analysis behavior.
"""


def run_rq3_analysis(
    tool_name: str,
    source_path: Path,
    graph_path: Path,
    output_dir: Path,
    bootstrap_simulations: int = 1000,
    refuter_simulations: int = 200,
    seed: int = 20260915,
):
    """Run and persist the complete RQ3 workflow for one SAST tool."""

    output_dir.mkdir(parents=True, exist_ok=True)
    data, summary = load_reporting_policy_data(source_path)
    scores, overlap, balance, matching = propensity_diagnostics(data)
    save_overlap_plot(scores, output_dir / "propensity_overlap.svg", tool_name)

    model, estimand, dowhy_estimates = dowhy_estimate_suite(data)
    point_estimates = {
        name: float(estimate.value) for name, estimate in dowhy_estimates.items()
    }
    independent_estimates = estimate_suite(data)
    validation_rows = []
    for estimator in ESTIMATOR_LABELS:
        difference = independent_estimates[estimator] - point_estimates[estimator]
        validation_rows.append(
            {
                "estimator": estimator,
                "dowhy_estimate": point_estimates[estimator],
                "independent_implementation_estimate": independent_estimates[estimator],
                "difference": difference,
                "agrees_within_1e_8": abs(difference) < 1e-8,
            }
        )
    software_validation = pd.DataFrame(validation_rows)
    if not software_validation["agrees_within_1e_8"].all():
        raise RuntimeError("Independent estimator implementations do not reproduce DoWhy")

    bootstrap = bootstrap_estimates(data, bootstrap_simulations, seed)
    estimator_results = summarize_estimates(point_estimates, bootstrap)
    cluster_diagnostics = apk_cluster_diagnostics(data)
    refuters = run_refuters(
        model,
        estimand,
        dowhy_estimates,
        simulations=refuter_simulations,
        seed=seed,
    )

    scores.to_csv(output_dir / "propensity_scores.csv", index=False)
    overlap.to_csv(output_dir / "overlap_summary.csv", index=False)
    balance.to_csv(output_dir / "balance.csv", index=False)
    matching.to_csv(output_dir / "matching_diagnostics.csv", index=False)
    estimator_results.to_csv(output_dir / "estimator_results.csv", index=False)
    bootstrap.to_csv(output_dir / "bootstrap_estimates.csv", index=False)
    refuters.to_csv(output_dir / "refuter_results.csv", index=False)
    software_validation.to_csv(output_dir / "software_validation.csv", index=False)
    cluster_diagnostics.to_csv(
        output_dir / "apk_cluster_diagnostics.csv", index=False
    )

    metadata = {
        "tool": tool_name,
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "source_csv": str(source_path),
        "source_sha256": _sha256(source_path),
        "graph": str(graph_path),
        "treatment": TREATMENT,
        "outcome": OUTCOME,
        "adjustment_variables": COVARIATES,
        "target_units": "ate",
        "effect_scale": "risk_difference",
        "bootstrap_simulations": bootstrap_simulations,
        "refuter_simulations": refuter_simulations,
        "random_seed": seed,
        "unobserved_common_cause_scenario": {
            "simulation_method": "direct-simulation",
            "treatment_binary_flip_strength": 0.05,
            "outcome_binary_flip_strength": 0.05,
        },
        "apk_clusters_with_conflicting_popularity": int(
            (cluster_diagnostics["n_popularity_values"] > 1).sum()
        ),
        "conflicting_cluster_bootstrap_policy": (
            "retain complete APK in a composite popularity stratum"
        ),
        "python": platform.python_version(),
        "packages": {
            name: _package_version(name)
            for name in ("dowhy", "numpy", "pandas", "scikit-learn", "statsmodels")
        },
    }
    (output_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "dataset_summary.json").write_text(
        json.dumps(summary.__dict__, indent=2) + "\n", encoding="utf-8"
    )
    report = _markdown_report(
        tool_name,
        source_path,
        graph_path,
        summary,
        overlap,
        balance,
        matching,
        estimator_results,
        refuters,
        cluster_diagnostics,
        bootstrap_simulations,
        refuter_simulations,
    )
    (output_dir / "RQ3_RESULTS.md").write_text(report, encoding="utf-8")
    return {
        "data": data,
        "overlap": overlap,
        "balance": balance,
        "matching": matching,
        "estimator_results": estimator_results,
        "refuters": refuters,
        "software_validation": software_validation,
        "cluster_diagnostics": cluster_diagnostics,
        "output_dir": output_dir,
    }
