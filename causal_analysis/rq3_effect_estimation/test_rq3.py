import unittest
from pathlib import Path

import numpy as np

from causal_analysis.shared.data_loading import load_reporting_policy_data
from causal_analysis.shared.rq3_analysis import (
    _cluster_bootstrap_sample,
    _cluster_sampling_plan,
    dowhy_estimate_suite,
    estimate_suite,
    propensity_diagnostics,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CODEQL_DATA = (
    REPOSITORY_ROOT
    / "causal_analysis/data/codeql/alerts_with_lib_category_and_apk_size_codeql.csv"
)


class RQ3AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data, _ = load_reporting_policy_data(CODEQL_DATA)
        cls.estimator_data = data
        apk_ids = data["apk_id"].drop_duplicates().iloc[:30]
        cls.data = data[data["apk_id"].isin(apk_ids)].reset_index(drop=True)

    def test_independent_estimators_reproduce_dowhy(self):
        independent = estimate_suite(self.estimator_data)
        _, _, estimates = dowhy_estimate_suite(self.estimator_data)
        for estimator, value in independent.items():
            self.assertAlmostEqual(value, float(estimates[estimator].value), places=8)

    def test_balance_output_covers_both_adjustments(self):
        _, _, balance, matching = propensity_diagnostics(self.data)
        self.assertEqual(
            set(balance["covariate"]),
            {"app_popularity_encoded", "apk_size_scaled"},
        )
        self.assertIn("smd_after_psm", balance)
        self.assertIn("smd_after_aipw_weighting", balance)
        self.assertIn("n_rows_outside_common_support", matching)

    def test_cluster_bootstrap_keeps_complete_policy_expanded_alerts(self):
        cluster_rows, strata = _cluster_sampling_plan(self.data)
        sampled = _cluster_bootstrap_sample(
            self.data,
            np.random.default_rng(19),
            cluster_rows,
            strata,
        )
        memberships = sampled.groupby("source_alert_id")["reporting_policy"].apply(set)
        original = self.data.set_index("source_alert_id")["is_third_party"].to_dict()
        for alert_id, policies in memberships.items():
            expected = {1} if original[alert_id] else {0, 1}
            self.assertEqual(policies, expected)


if __name__ == "__main__":
    unittest.main()
