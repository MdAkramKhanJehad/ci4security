"""Small invariant tests for the RQ1 transform and causal-graph specification."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import networkx as nx
import pandas as pd

from causal_analysis.shared.data_loading import load_reporting_policy_data
from causal_analysis.shared.graph_construction import (
    CAUSAL_EDGES,
    CAUSAL_NODES,
    build_causal_graph,
    graph_source,
)


class ReportingPolicyTransformTests(unittest.TestCase):
    def test_developer_alert_is_shared_and_third_party_is_inclusive_only(self):
        frame = pd.DataFrame(
            [
                {"ruleId": "r1", "verdict": True, "app_package_name": "a", "version_code": 1, "apk_size": 10, "apk_category": "<100", "code_location": "developer_written"},
                {"ruleId": "r2", "verdict": False, "app_package_name": "a", "version_code": 1, "apk_size": 10, "apk_category": "<100", "code_location": "Utilities"},
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "alerts.csv"
            frame.to_csv(path, index=False)
            transformed, summary = load_reporting_policy_data(path)
        self.assertEqual(summary.raw_alerts, 2)
        self.assertEqual(summary.analyzed_alert_rows, 3)
        self.assertEqual(set(transformed.loc[transformed.source_alert_id == 0, "reporting_policy"]), {0, 1})
        self.assertEqual(set(transformed.loc[transformed.source_alert_id == 1, "reporting_policy"]), {1})
        self.assertEqual(set(transformed.loc[transformed.source_alert_id == 1, "reported_alert_is_third_party"]), {1})


class CausalGraphTests(unittest.TestCase):
    def test_graph_is_acyclic_and_contains_the_fixed_domain_edges(self):
        graph = build_causal_graph()
        self.assertTrue(nx.is_directed_acyclic_graph(graph))
        self.assertEqual(set(graph.nodes), set(CAUSAL_NODES))
        self.assertEqual(set(graph.edges), set(CAUSAL_EDGES))
        self.assertIn(("reporting_policy", "reported_alert_is_third_party"), graph.edges)
        for confounder in ("app_popularity_encoded", "apk_size_scaled"):
            self.assertIn((confounder, "reported_alert_is_third_party"), graph.edges)
            self.assertIn((confounder, "verdict"), graph.edges)

    def test_graph_has_no_association_values(self):
        source = graph_source("Example")
        for association_text in ("rho=", "q=", "associated when", "Edge labels"):
            self.assertNotIn(association_text, source)


if __name__ == "__main__":
    unittest.main()
