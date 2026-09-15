# RQ1: causal-graph formulation and association assessment

RQ1 asks:

> How can evidence from SAST literature and empirical constraints be used to
> formulate and assess causal graphs for SAST design assumptions?

The restart-executable notebook processes CodeQL, CogniCrypt, CryptoGuard, and
Semgrep separately. It uses the same systematic graph structure for every tool
and produces four tool-specific graph images.

## Workflow

1. Load the canonical alert dataset for one SAST tool.
2. Construct `reporting_policy` exactly as in the legacy binary experiment:
   `0` is developer-only and `1` is developer plus third-party.
3. Run two-sided Spearman association tests for the numeric/binary graph
   variables and a chi-square/Cramer's V test for rule ID and verdict.
4. Apply Benjamini-Hochberg correction within each tool.
5. Apply the common domain-specified DAG structure.
6. Save one domain-specified SVG graph for that tool and report the association
   results separately in CSV and Markdown tables.

Correlation supplies empirical association evidence. Direction is supplied by
domain knowledge and is not inferred from the sign or significance of a
correlation.

## Graph structure

`reporting_policy` is the treatment, `reported_alert_is_third_party` represents
alert provenance in the policy-expanded table, and `verdict` is the outcome.
App popularity and APK size are the specified confounder nodes and point to both
alert provenance and verdict. The same eight directed edges are used for all
four tools; only the tool name differs.

## Run the notebook

From the repository root:

```bash
source venv/bin/activate
jupyter notebook causal_analysis/rq1_graph_assessment/rq1_analysis.ipynb
```

Choose **Restart Kernel and Run All Cells**. The notebook regenerates all
association tables, summaries, metadata, and the four graphs.

## Outputs

- `graphs/codeql_causal_graph.svg`
- `graphs/cognicrypt_causal_graph.svg`
- `graphs/cryptoguard_causal_graph.svg`
- `graphs/semgrep_causal_graph.svg`
- `results/<tool>/association_checks.csv`
- `results/<tool>/reporting_policy_summary.csv`
- `results/<tool>/dataset_summary.json`
- `results/<tool>/causal_graph.md`
- `results/<tool>/run_metadata.json`
- `results/all_tools_association_checks.csv`

See `RQ1_RESULTS.md` for the results narrative and `NAVIGATION.md` for the code
and output map.
